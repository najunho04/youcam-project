아래 명세를 보고 계약 테스트를 작성해줘. 3~7개.

- 구현 코드는 열지 말 것. 명세만 보고 작성. (`backend/src/common/`, `backend/src/shared/`, `backend/test/conftest.py` 는 읽어도 됨. `feature/` 는 열지 말 것)
- 정상 케이스 + 불변조건 위반 + 권한 위반을 다룰 것.
- 응답 DTO의 필드와 타입을 검증할 것.
- 명세에 없어서 판단이 안 서는 부분은 지어내지 말고 질문으로 남겨줘.
- 저장 위치: backend/test/contract/recommendation/ (pytest, 공용 fixture 는 backend/test/conftest.py)
- 이 슬라이스 폴더 밖에는 쓰지 말 것. 작성 후 커밋하지 말고 멈춰서 승인을 기다릴 것.
- 구현이 없으므로 테스트는 실패하는 것이 정상. `SLICE=recommendation make test-slice` 로 수집 오류(import 에러 등)만 없는지 확인할 것.
- 백엔드 API 계약만 대상. 카드의 프론트·UI 항목은 테스트하지 말 것.
- 사전 상태는 fixture(`create_user(**columns)`, `create_product(**columns)`)와 `database_session`(swipes·wardrobe_photos 직접 삽입)으로 만들 것. 다른 슬라이스 API를 호출해서 상태를 만들지 말 것.
- 점수 기대값이 명확하도록 입력을 통제할 것: embedding 은 직접 만든 L2 정규화 512차원 벡터(예: 한두 축만 값이 있는 벡터), color_lab 은 `shared.color.palette_lab(season)` 의 색이나 ΔE 를 계산하기 쉬운 값. 기대 점수는 카드의 식으로 테스트 안에서 계산하고 부동소수 비교는 `pytest.approx` 로 할 것.
- tasteScore 는 후보 전체에 의존한다. 기대값을 계산할 때 그 사용자의 후보 전부(스와이프한 상품 제외)를 포함할 것.
- 응답 시간(1초) 같은 성능 항목은 테스트하지 말 것.

[컨텍스트 카드]

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
    - `styleTags: string[]` — 사용자 취향 요약 태그 1~3개 (아래 계산 규칙)
    - `season: Season`, `palette: string[]` (= SEASON_PALETTES[season])
    - `isFallback: boolean` — 좋아요 3개 미만이면 true
    - `items: RecommendationItem[]` — 최대 5개, score 내림차순
  - `RecommendationItem { product: ProductDto, score: number, tasteScore: number, colorScore: number, reasonTags: string[] }`
  - `ProductDto { id, title, price, mallName, purchaseUrl, imageUrl, style }`
  - Error: PROFILE_REQUIRED(409) — age_group/gender NULL / PERSONAL_COLOR_REQUIRED(409) — season NULL / UNAUTHORIZED(401)
- 계산:
  - 후보: products 중 gender·age_group 일치, category = TOP, **사용자가 스와이프한 상품 제외**
  - 취향 벡터 `u = normalize(mean(L) + 1.5 × mean(C) − 0.5 × mean(D))` — L: 좋아요 상품 embedding, C: wardrobe_photos embedding, D: 싫어요 상품 embedding. 비어 있는 항은 0 벡터
  - tasteScore = 후보 안에서 Z-score 정규화 후 표준정규 CDF:
    - c_i = cos(u, product_i.embedding), μ·σ = 전체 후보 c_i 의 평균·모표준편차(ddof=0)
    - tasteScore_i = Φ((c_i − μ) / σ), Φ(z) = 0.5 × (1 + erf(z / √2))
    - σ = 0 (후보 1개, 모두 같은 값) 이거나 u 가 0 벡터면 모든 후보 0.5
  - colorScore = max(0, 1 − ΔE / 50) — ΔE 는 상품 color_lab 과 팔레트(`shared.color.palette_lab(season)`) 중 가장 가까운 색의 거리(`shared.color.delta_e`)
  - score = 0.7 × tasteScore + 0.3 × colorScore
  - 정렬: score 내림차순, 같으면 product.id 오름차순
  - 폴백(좋아요 < 3): tasteScore 를 계산하지 않는다. tasteScore = 0, score = colorScore, isFallback = true. 후보·정렬 규칙은 같다
  - 한글명 (태그 공통)
    - Style: MINIMAL 미니멀 / CASUAL 캐주얼 / STREET 스트릿 / FORMAL 포멀 / LOVELY 러블리
    - Season: SPRING_WARM 봄 웜톤 / SUMMER_COOL 여름 쿨톤 / AUTUMN_WARM 가을 웜톤 / WINTER_COOL 겨울 쿨톤
  - styleTags (규칙 기반):
    - 선호 스타일 = 좋아요한 상품들의 style 을 빈도순으로 최대 2개 (빈도가 같으면 Style enum 정의 순서)
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
- 상단: 취향 요약(styleTags) + 시즌 + 팔레트 칩. isFallback 이면 "취향 데이터가 적어 퍼스널컬러에 어울리는 상품을 보여드려요" 안내
- 카드 5개: 이미지, 상품명, 가격(원), 쇼핑몰, reasonTags, "입어보기", "구매하러 가기"
- 필요 상태: 로딩 / items 0개 빈 상태 / PROFILE_REQUIRED·PERSONAL_COLOR_REQUIRED 시 해당 화면으로 안내 / 에러

## 테스트 환경
- 공용 fixture: backend/test/conftest.py — create_product(embedding, color_lab, style 등 지정 가능), create_user(season=..., age_group=..., gender=...), embedding_model(fake), auth_headers. swipes·wardrobe_photos 는 database_session 으로 직접 삽입
