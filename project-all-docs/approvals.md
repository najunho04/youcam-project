# 계약·공용 변경 승인 기록

세션이 "공용 레이어 변경 필요"를 보고했을 때의 처리 절차:

1. 사람이 판단
2. 공용 타입 수정 후 사용자가 직접 `HARNESS_APPROVED=1 git commit`
3. **같은 타입 쓰는 다른 슬라이스 확인**
4. 끝난 슬라이스면 재작업 여부 결정
5. 컨텍스트 카드 갱신 후 세션 재개

| 날짜 | 슬라이스 | 변경 대상 | 사유 | 영향 슬라이스 | 재작업 |
|---|---|---|---|---|---|
| 2026-10-11 | foundation | backend/src/common, shared · front/src/common, shared · Makefile · CLAUDE.md · pre-commit·settings.json 보호 경로 추가 | 초기 구축 (사용자 승인) | 전체 | - |
