# 구현 세션 프롬프트

피쳐별 세션. 의존 없는 슬라이스끼리 병렬 (1인 기준 동시 2~3개 상한). 슬라이스당 브랜치 1개.

```
아래 슬라이스를 구현해줘.

- backend/test/contract/ 의 테스트를 통과시키되, 그 파일은 수정 금지.
- 공용 레이어는 읽기 전용. 변경 필요하면 멈추고 보고.
- 세부 단위 테스트는 TDD로 먼저 작성.
- 레퍼런스 구조: backend/src/feature/_reference-slice/, front/src/feature/_reference-slice/

[컨텍스트 카드]
```
