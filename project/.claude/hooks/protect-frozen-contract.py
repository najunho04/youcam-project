#!/usr/bin/env python3
"""PreToolUse hook: 동결된 계약 테스트 수정 차단.

동결 = git 에 커밋됨. 규칙:
- {backend,front}/test/contract/{slice}/ 안에 git 이 추적하는 파일이 하나라도 있으면 그 슬라이스는 동결 → 수정·추가 차단
- 아직 커밋 전인 슬라이스 폴더는 테스트 세션이 작성할 수 있다
차단 시 exit 2 (stderr 가 세션에 전달된다).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

CONTRACT_ROOTS = ("backend/test/contract", "front/test/contract")


def main() -> int:
    payload = json.load(sys.stdin)
    tool_input = payload.get("tool_input") or {}
    raw_path = tool_input.get("file_path") or tool_input.get("notebook_path")
    if not raw_path:
        return 0

    project_directory = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".").resolve()
    target = Path(raw_path)
    if not target.is_absolute():
        target = Path(payload.get("cwd") or project_directory) / target
    target = target.resolve()

    try:
        relative = target.relative_to(project_directory).as_posix()
    except ValueError:
        return 0

    for root in CONTRACT_ROOTS:
        if relative != root and not relative.startswith(root + "/"):
            continue
        remainder = relative[len(root):].lstrip("/")
        parts = remainder.split("/") if remainder else []
        # contract/ 바로 아래 파일이면 contract/ 자체, 아니면 contract/{slice}/ 를 동결 단위로 본다
        frozen_unit = root if len(parts) <= 1 else f"{root}/{parts[0]}"
        tracked = subprocess.run(
            ["git", "ls-files", "--", frozen_unit if frozen_unit != root else relative],
            cwd=project_directory, capture_output=True, text=True,
        ).stdout.strip()
        if tracked:
            print(
                f"[harness] 동결된 계약 테스트입니다 ({frozen_unit}). 수정·추가할 수 없습니다.\n"
                "구현 코드를 고쳐 테스트를 통과시키거나, 명세 불일치라면 멈추고 사용자에게 보고하세요.",
                file=sys.stderr,
            )
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
