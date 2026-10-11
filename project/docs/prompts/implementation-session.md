# 구현 세션 프롬프트

피쳐별 세션(`project/`에서 연다). 의존 없는 슬라이스끼리 병렬 (1인 기준 동시 2~3개 상한). 슬라이스당 브랜치 1개.

**시작 전 확인: 이 슬라이스의 계약 테스트가 커밋(동결)되어 있어야 한다.** 커밋 전이면 hook 이 보호하지 못한다.

```bash
git status --short backend/test/contract   # 출력이 없어야 한다
```

종료 후 확인: `git diff --stat` 에 `test/contract/` 가 없어야 한다 (Bash 우회 수정은 hook 이 못 잡는다).

```
아래 슬라이스를 구현해줘.

- backend/test/contract/ 의 테스트를 통과시키되, 그 파일은 수정 금지.
- 공용 레이어는 읽기 전용. 변경 필요하면 멈추고 보고.
- 세부 단위 테스트는 TDD로 먼저 작성.
- 레퍼런스 구조: backend/src/feature/_reference-slice/, front/src/feature/_reference-slice/

[컨텍스트 카드]
```
