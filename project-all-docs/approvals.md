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
| 2026-10-15 | swipe · recommendation | backend/src/common(entity·enums·error·dto) · front/src/common/type · conftest(create_pin) · contract(swipe·recommendation·profile) | 스와이프 카드를 상품 → Pinterest 코디 사진(pins)으로 변경, 추천에 핀평균·상품평균 빼기 적용 (사용자 승인, 실험 결과 근거) | swipe, recommendation, profile(계약 테스트 1건) | swipe·recommendation 재작업 완료 |
| 2026-10-26 | personal_color · product_ingest · recommendation | backend/src/common(entity users·products, dto PersonalColorDto·ProductDto·RecommendationResponse, enums SeasonSubtype·ProductSource) · shared(youcam 얼굴 색 5개, color 판정 함수·팔레트) · front/src/common/type · conftest · contract(personal_color·product_ingest·recommendation·auth·profile·fitting) | 퍼스널컬러를 YouCam 응답 전부로 12유형 판정 + 근거 노출, 상품을 네이버 → eBay 로 교체 (사용자 승인, 해커톤 심사 기준 대응) | personal_color, product_ingest, recommendation, auth, profile, fitting(ProductDto) | 공용 레이어 완료(10-26, 공용 테스트 통과). 슬라이스 6개 재작업 예정 — 기존 테스트 41건 실패 중 |
