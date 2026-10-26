아래 슬라이스를 재작업해줘.

- 이번 작업은 **재작업**이다. 슬라이스 코드는 이미 있고, 공용 레이어와 계약 테스트가 새 카드 기준으로 바뀌었다 (커밋 84416b5, 958ef9e). 기존 코드를 아래 카드에 맞게 고칠 것.
- backend/test/contract/recommendation/ 의 테스트를 통과시키되, 그 파일은 수정 금지.
- 공용 레이어(`common/`, `shared/`, `backend/test/conftest.py`, front `common/`·`shared/`)는 읽기 전용. 변경이 필요하면 멈추고 보고.
- `shared.color.SEASON_PALETTES` 는 개편 전 임시 별칭이다. 새 코드에서 쓰지 말 것 (`SUBTYPE_PALETTES`·`AVOID_PALETTES` 사용).
- 기존 단위 테스트(backend/test/unit/recommendation/, front/test/unit/recommendation/)가 깨져 있다. 새 카드 기준으로 TDD 로 고칠 것 (테스트를 먼저 고치고 구현). 다른 슬라이스의 단위 테스트는 건드리지 말 것.
- 다른 슬라이스의 코드를 import 하지 말 것. 공용으로 옮겨야 한다고 판단되면 멈추고 보고.
- 조립 지점(backend/src/main.py `FEATURE_ROUTERS`, front/src/app/App.tsx)은 이미 연결돼 있다. 바꾸지 말 것.
- 색 점수는 `shared.color.palette_lab(season, subtype)`, `avoid_palette_lab(season)`, `delta_e` 를 쓸 것. 감점 기준 15 와 배율 0.5 는 슬라이스 상수로 둔다.
- 후보 조회에 `source = EBAY` 조건을 추가할 것 (한국어 UI 네이버 상품은 최후순위라 지금은 EBAY 고정).
- reasonTags·styleTags 문구 규칙은 바뀌지 않았다 (4계절 한글명 그대로).
- 프론트: 가격은 `shared.i18n.formatMoney(price, currency, language)` 로 표시 (기존 formatPrice 는 원화 전용). 상단에 세부 유형 표시.
- 완료 기준: `SLICE=recommendation make test-slice` 통과 (계약 + 단위), `make lint` 통과, 프론트 `npx tsc -b` 오류 없음. 커밋은 하지 말고 결과를 보고할 것.

[컨텍스트 카드]

# 슬라이스: recommendation

## 목적
스와이프·옷장 사진으로 만든 취향 벡터와 퍼스널컬러(12유형) 점수로 상품을 랭킹해 상위 6개와 추천 이유를 보여준다. 구매 링크(eBay) 포함.

## 경로
- 백: backend/src/feature/recommendation/
- 프론트: front/src/feature/recommendation/
- 계약 테스트: backend/test/contract/recommendation/ · 단위 테스트: backend/test/unit/recommendation/, front/test/unit/recommendation/

## 데이터
- 읽기: users(age_group, gender, season, season_subtype), swipes, pins(style, embedding), wardrobe_photos(embedding), products, embedding_centroids
- 쓰기: 없음 (요청마다 계산, 저장하지 않음)
- 스키마 발췌:
  - products: id, source, title, price, currency, mall_name, purchase_url, image_url, gender, age_group, style, category, color_lab real[3], embedding vector(512)
  - swipes: user_id, pin_id, liked
  - pins: id, style, embedding vector(512)
  - embedding_centroids: domain(PIN | PRODUCT) PK, embedding vector(512) — 적재 시 계산한 핀평균 P·상품평균 Q
  - wardrobe_photos: user_id, embedding vector(512)

## 계약
- GET /api/recommendations (인증 필요)
  - Response 200 `RecommendationResponse`
    - `styleTags: string[]` — 사용자 취향 요약 태그 1~3개 (아래 계산 규칙)
    - `season: Season`, `subtype: SeasonSubtype`, `palette: string[]` (= `SUBTYPE_PALETTES[(season, subtype)]`)
    - `isFallback: boolean` — 좋아요 3개 미만이면 true
    - `items: RecommendationItem[]` — 최대 6개, score 내림차순
  - `RecommendationItem { product: ProductDto, score: number, tasteScore: number, colorScore: number, reasonTags: string[] }`
  - `ProductDto { id, title, price, currency, mallName, purchaseUrl, imageUrl, style }`
  - Error: PROFILE_REQUIRED(409) — age_group/gender NULL / PERSONAL_COLOR_REQUIRED(409) — season 또는 season_subtype NULL / UNAUTHORIZED(401)
- 계산:
  - 후보: products 중 source = EBAY, gender·age_group 일치, category = TOP (스와이프는 핀에 하므로 상품을 제외하지 않음)
  - 취향 벡터 `u = normalize(mean(L − P) + 1.5 × mean(C) − 0.5 × mean(D − P))` — L: 좋아요 핀 embedding, C: wardrobe_photos embedding(평균 빼지 않음), D: 싫어요 핀 embedding, P: 핀평균. 비어 있는 항은 0 벡터, 평균이 없으면 0 벡터
  - tasteScore = 후보 안에서 Z-score 정규화 후 표준정규 CDF:
    - c_i = cos(u, product_i.embedding − Q) — Q: 상품평균, μ·σ = 전체 후보 c_i 의 평균·모표준편차(ddof=0)
    - tasteScore_i = Φ((c_i − μ) / σ), Φ(z) = 0.5 × (1 + erf(z / √2))
    - σ = 0 (후보 1개, 모두 같은 값) 이거나 u 가 0 벡터면 모든 후보 0.5
  - colorScore = max(0, 1 − ΔE / 50) × 감점 — ΔE 는 상품 color_lab 과 어울리는 팔레트(`shared.color.palette_lab(season, subtype)`) 중 가장 가까운 색의 거리(`shared.color.delta_e`)
    - 감점: 피해야 할 팔레트(`shared.color.avoid_palette_lab(season)`) 중 가장 가까운 색과의 ΔE < 15 이면 × 0.5, 아니면 × 1
  - score = 0.7 × tasteScore + 0.3 × colorScore
  - 정렬: score 내림차순, 같으면 product.id 오름차순
  - 폴백(좋아요 < 3): tasteScore 를 계산하지 않는다. tasteScore = 0, score = colorScore, isFallback = true. 후보·정렬 규칙은 같다
  - 한글명 (태그 공통)
    - Style: MINIMAL 미니멀 / CASUAL 캐주얼 / STREET 스트릿 / FORMAL 포멀 / LOVELY 러블리
    - Season: SPRING_WARM 봄 웜톤 / SUMMER_COOL 여름 쿨톤 / AUTUMN_WARM 가을 웜톤 / WINTER_COOL 겨울 쿨톤
  - styleTags (규칙 기반):
    - 선호 스타일 = 좋아요한 핀들의 style 을 빈도순으로 최대 2개 (빈도가 같으면 Style enum 정의 순서)
    - styleTags = [선호 스타일 한글명…, 시즌 한글명] — 마지막은 항상 시즌명. 좋아요가 없으면 [시즌명] 1개
  - reasonTags (규칙 기반, 상품마다 최대 2개, 이 순서):
    1. 상품 style 이 선호 스타일에 있으면 `"선호하는 {스타일}"` (예: "선호하는 미니멀")
    2. colorScore ≥ 0.7 이면 `"{시즌} 컬러"` (예: "가을 웜톤 컬러")
    3. 1·2 가 모두 없으면 `"{스타일} 스타일"` (예: "캐주얼 스타일")

## 상하류
- 상류: 옷장 사진 화면(업로드 또는 건너뛰기) 후 이동해 옴
- 하류: 카드의 "입어보기" → `ROUTES.fitting(productId)`, "구매하러 가기" → product.purchaseUrl (새 탭)

## 공유 상태 - 호출 없이 얽히는 관계
- 무효화 필요 캐시: 없음
- 기타: 결과를 저장하지 않으므로 다시 들어오면 다시 계산 (같은 데이터면 같은 결과)

## 횡단 관심사
- 권한: 본인만 (`CurrentUser`)
- 트랜잭션 경계: 읽기 전용
- 성능: 응답 1초 이내 (후보 수천 개 기준, 벡터 인덱스 없이 계산)
- 에러 처리: 공통 규약 따름

## 불변조건
- items 는 score 내림차순, 최대 6개
- tasteScore, colorScore, score 는 0~1
- 같은 입력이면 같은 결과 (무작위 없음)

## 충돌 주의
- 쓰는 테이블 없음

## 허용 의존
- `common/`, `shared/`만 (임베딩 모델이 필요하면 `shared.embedding.get_embedding_model()`)
- 조립: main.py 한 줄, App.tsx 에 `ROUTES.recommendation` (RequireAuth)

## UI 결과
- 상단: 취향 요약(styleTags) + 시즌·세부 유형 + 팔레트 칩. isFallback 이면 "취향 데이터가 적어 퍼스널컬러에 어울리는 상품을 보여드려요" 안내
- 카드 최대 6개 (같은 크기 그리드): 이미지, 상품명, 가격(currency 기준, USD 는 `$19.99`), 판매처, reasonTags, "입어보기", "구매하러 가기"
- 필요 상태: 로딩 / items 0개 빈 상태 / PROFILE_REQUIRED·PERSONAL_COLOR_REQUIRED 시 해당 화면으로 안내 / 에러

## 테스트 환경
- 공용 fixture: backend/test/conftest.py — create_product(embedding, color_lab, style, source·currency 등 지정 가능), create_pin(embedding, style 등), create_user(season=..., season_subtype=..., age_group=..., gender=...), embedding_model(fake), auth_headers. swipes·wardrobe_photos·embedding_centroids 는 database_session 으로 직접 삽입
