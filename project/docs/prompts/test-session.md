# 테스트 세션 프롬프트

깨끗한 세션(`project/`에서 연다). **구현 코드 접근 없이** 컨텍스트 카드만 보고 계약 테스트를 작성한다.

동결 = git 커밋. 사람이 승인하면 직접 커밋한다 (`--no-verify`, 사람만). 커밋된 슬라이스의 계약 테스트는 hook(`.claude/hooks/protect-frozen-contract.py`)이 수정·추가를 차단한다.

```bash
git add backend/test/contract/{slice} && git commit --no-verify -m "contract: {slice} 동결"
```

```
아래 명세를 보고 계약 테스트를 작성해줘. 3~7개.

- 구현 코드는 열지 말 것. 명세만 보고 작성.
- 정상 케이스 + 불변조건 위반 + 권한 위반을 다룰 것.
- 응답 DTO의 필드와 타입을 검증할 것.
- 명세에 없어서 판단이 안 서는 부분은 지어내지 말고 질문으로 남겨줘.
- 저장 위치: backend/test/contract/{슬라이스명}/ (pytest, 공용 fixture 는 backend/test/conftest.py)
- 이 슬라이스 폴더 밖에는 쓰지 말 것. 작성 후 커밋하지 말고 멈춰서 승인을 기다릴 것.
- 구현이 없으므로 테스트는 실패하는 것이 정상. 수집 오류(import 에러 등)만 없게 할 것.

[컨텍스트 카드]
```
