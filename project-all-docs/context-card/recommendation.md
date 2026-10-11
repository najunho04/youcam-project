# 슬라이스: recommendation

## 목적
스와이프·옷장 사진으로 만든 취향 벡터와 퍼스널컬러 점수로 상품을 랭킹해 상위 5개와 추천 이유를 보여준다. 구매 링크 포함.

## 경로
- 백: backend/src/feature/recommendation/
- 프론트: front/src/feature/recommendation/
- 계약 테스트: backend/test/contract/recommendation/ · 단위 테스트: backend/test/unit/recommendation/, front/test/unit/recommendation/

## 데이터
- 읽기: users(age_group, gender, season), swipes, wardrobe_photos(embedding), products
- 쓰기: 없음 (요청마다 계산, 저장하지 않음)
- 스키마 발췌:
  - products: id, title, price, mall_name, purchase_url, image_url, gender, age_group, style, category, color_lab real[3], embedding vector(512)
  - swipes: user_id, product_id, liked
  - wardrobe_photos: user_id, embedding vector(512)

## 계약
- GET /api/recommendations (인증 필요)
  - Response 200 `RecommendationResponse`
    - `styleTags: string[]` — 사용자 취향 요약 태그 2~3개 {생성 방법 미정}
    - `season: Season`, `palette: string[]` (= SEASON_PALETTES[season])
    - `isFallback: boolean` — 좋아요 3개 미만이면 true
    - `items: RecommendationItem[]` — 최대 5개, score 내림차순
  - `RecommendationItem { product: ProductDto, score: number, tasteScore: number, colorScore: number, reasonTags: string[] }`
  - `ProductDto { id, title, price, mallName, purchaseUrl, imageUrl, style }`
  - Error: PROFILE_REQUIRED(409) — age_group/gender NULL / PERSONAL_COLOR_REQUIRED(409) — season NULL / UNAUTHORIZED(401)
- 계산:
  - 후보: products 중 gender·age_group 일치, category = TOP, **사용자가 스와이프한 상품 제외**
  - 취향 벡터 `u = normalize(mean(L) + 1.5 × mean(C) − 0.5 × mean(D))` — L: 좋아요 상품 embedding, C: wardrobe_photos embedding, D: 싫어요 상품 embedding. 비어 있는 항은 0 벡터
  - tasteScore = cos(u, product.embedding) 의 0~1 변환 {변환식 미정}
  - colorScore = 상품 color_lab 과 팔레트(`shared.color.palette_lab(season)`) 중 가장 가까운 색의 ΔE(`shared.color.delta_e`) → 0~1 {변환식 미정}
  - score = 0.7 × tasteScore + 0.3 × colorScore
  - reasonTags: {생성 방법 미정}
  - 폴백(좋아요 < 3): {미정 — "인기 상품" 기준이 데이터에 없음}

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
- items 에 스와이프한 상품이 없다
- items 는 score 내림차순, 최대 5개
- tasteScore, colorScore, score 는 0~1
- 같은 입력이면 같은 결과 (무작위 없음)

## 충돌 주의
- 쓰는 테이블 없음

## 허용 의존
- `common/`, `shared/`만 (임베딩 모델이 필요하면 `shared.embedding.get_embedding_model()`)
- 조립: main.py 한 줄, App.tsx 에 `ROUTES.recommendation` (RequireAuth)

## UI 결과
- 상단: 취향 요약(styleTags) + 시즌 + 팔레트 칩. isFallback 이면 "취향 데이터가 적어 인기 상품을 보여드려요" 류 안내
- 카드 5개: 이미지, 상품명, 가격(원), 쇼핑몰, reasonTags, "입어보기", "구매하러 가기"
- 필요 상태: 로딩 / items 0개 빈 상태 / PROFILE_REQUIRED·PERSONAL_COLOR_REQUIRED 시 해당 화면으로 안내 / 에러

## 테스트 환경
- 공용 fixture: backend/test/conftest.py — create_product(embedding, color_lab, style 등 지정 가능), create_user(season=..., age_group=..., gender=...), embedding_model(fake), auth_headers. swipes·wardrobe_photos 는 database_session 으로 직접 삽입
