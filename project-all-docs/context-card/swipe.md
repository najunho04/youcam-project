# 슬라이스: swipe

## 목적
나이대·성별에 맞는 상의 이미지를 스타일별로 섞어 보여주고, 좋아요/싫어요를 모아 저장한다.

## 경로
- 백: backend/src/feature/swipe/
- 프론트: front/src/feature/swipe/
- 계약 테스트: backend/test/contract/swipe/ · 단위 테스트: backend/test/unit/swipe/, front/test/unit/swipe/

## 데이터
- 읽기: users(age_group, gender), products, swipes
- 쓰기: swipes
- 스키마 발췌:
  - swipes.user_id bigint PK, FK → users.id ON DELETE CASCADE
  - swipes.product_id bigint PK, FK → products.id ON DELETE CASCADE
  - swipes.liked boolean NOT NULL
  - swipes.created_at timestamptz
  - products.id, image_url text, gender, age_group, style, category (읽기만)

## 계약
- GET /api/swipe/cards?count=20 (인증 필요)
  - Query `count`: 기본 20, 허용 범위 {미정}
  - Response 200 `SwipeCardsResponse { cards: SwipeCardDto[] }`, `SwipeCardDto { productId: number, imageUrl: string, style: Style }`
  - 선택 규칙:
    - products.gender = users.gender AND products.age_group = users.age_group AND category = TOP
    - 사용자가 이미 스와이프한 상품 제외
    - Style 5종에서 균등하게 섞음 (count 를 스타일 수로 나눠 배분, 순서도 섞음)
    - 후보가 count 보다 적을 때: {미정 — 있는 만큼 반환 / 에러}
  - Error: PROFILE_REQUIRED(409) — users.age_group 또는 gender 가 NULL / UNAUTHORIZED(401)
- POST /api/swipe/answers (인증 필요)
  - Request `SwipeAnswersRequest { answers: { productId: number, liked: boolean }[] }` — 1개 이상
  - Response 200 `SwipeAnswersResponse { likedCount: number, totalCount: number }` — 이 사용자의 **저장된 전체** swipes 기준
  - Error: PRODUCT_NOT_FOUND(404) — 없는 productId 포함 시 전체 거부 / VALIDATION_ERROR(422) — answers 비어 있음 / UNAUTHORIZED(401)
  - 같은 상품 재제출: upsert (liked 덮어씀)

## 상하류
- 상류: 퍼스널컬러 결과 화면에서 이동해 옴. 카드 풀은 product_ingest 가 채운 products
- 하류: 제출 후 옷장 사진 화면(`ROUTES.wardrobe`). swipes 는 recommendation 이 취향 벡터 계산에 읽는다

## 공유 상태 - 호출 없이 얽히는 관계
- 무효화 필요 캐시: 없음
- 기타: 답변은 스와이프를 다 끝낸 뒤 한 번에 제출 (중간 이탈 시 저장 안 됨)

## 횡단 관심사
- 권한: 본인만 (`CurrentUser`)
- 트랜잭션 경계: answers 제출 1회 = 트랜잭션 1개 (부분 저장 없음)
- 에러 처리: 공통 규약 따름

## 불변조건
- (user_id, product_id) 당 swipes 행은 최대 1개
- cards 에 이미 스와이프한 상품이 나오지 않는다
- cards 의 상품은 모두 사용자 성별·나이대와 일치한다

## 충돌 주의
- swipes 쓰는 다른 피쳐: 없음 (recommendation 은 읽기만)

## 허용 의존
- `common/`, `shared/`만
- 조립: main.py 한 줄, App.tsx 에 `ROUTES.swipe` (RequireAuth)

## UI 결과
- 카드 한 장씩 표시, 좋아요/싫어요 버튼 (스와이프 제스처: {미정 — 버튼만 / 제스처 포함}), 진행률 "n / 전체"
- 마지막 카드 후 자동 제출 → 다음 화면
- 필요 상태: 카드 로딩 / 카드 0장(빈 상태 문구) / PROFILE_REQUIRED 시 프로필 화면으로 안내 / 제출 에러 시 재시도

## 테스트 환경
- 공용 fixture: backend/test/conftest.py — create_product(gender, age_group, style 등 지정 가능), create_user(age_group=..., gender=...), auth_headers
