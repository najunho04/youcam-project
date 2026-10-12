아래 명세를 보고 계약 테스트를 작성해줘. 3~7개.

- 구현 코드는 열지 말 것. 명세만 보고 작성. (`backend/src/common/`, `backend/src/shared/`, `backend/test/conftest.py` 는 읽어도 됨. `feature/` 는 열지 말 것)
- 정상 케이스 + 불변조건 위반 + 권한 위반을 다룰 것.
- 응답 DTO의 필드와 타입을 검증할 것.
- 명세에 없어서 판단이 안 서는 부분은 지어내지 말고 질문으로 남겨줘.
- 저장 위치: backend/test/contract/swipe/ (pytest, 공용 fixture 는 backend/test/conftest.py)
- 이 슬라이스 폴더 밖에는 쓰지 말 것. 작성 후 커밋하지 말고 멈춰서 승인을 기다릴 것.
- 구현이 없으므로 테스트는 실패하는 것이 정상. `SLICE=swipe make test-slice` 로 수집 오류(import 에러 등)만 없는지 확인할 것.
- 백엔드 API 계약만 대상. 카드의 프론트·UI 항목은 테스트하지 말 것.
- 사전 상태는 fixture(`create_user(**columns)`, `create_product(**columns)`)나 `database_session` 으로 직접 만들 것. 다른 슬라이스 API(profile 등)를 호출해서 상태를 만들지 말 것.
- 카드 선택은 무작위다. 특정 상품·순서·나머지를 받는 스타일을 단정하지 말고, 명세가 보장하는 성질(개수, 성별·나이대 일치, 중복 없음, 이미 스와이프한 상품 제외, 스타일별 상한)만 검증할 것. 여러 번 호출해야 드러나는 성질이 아니면 한 번 호출로 충분하다.

[컨텍스트 카드]

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
  - Query `count`: 기본 20, 허용 범위 1~50 (밖이면 VALIDATION_ERROR(422))
  - Response 200 `SwipeCardsResponse { cards: SwipeCardDto[] }`, `SwipeCardDto { productId: number, imageUrl: string, style: Style }`
  - 선택 규칙:
    - products.gender = users.gender AND products.age_group = users.age_group AND category = TOP
    - 사용자가 이미 스와이프한 상품 제외
    - Style 5종에서 균등하게 섞음 (count 를 스타일 수로 나눠 배분, 순서도 섞음)
      - 스타일별 몫 = count // 5. 나머지 count % 5 장은 무작위로 고른 서로 다른 스타일에 1장씩 더한다 (예: count=7 → 2개 스타일 2장, 3개 스타일 1장)
      - 스타일 안에서 어떤 상품을 고를지는 무작위
    - 후보가 부족할 때: 다른 스타일로 채우지 않는다. 스타일별로 몫과 후보 수 중 작은 만큼만 담는다. 그래서 cards 는 count 보다 적을 수 있고, 후보가 없으면 빈 배열 200
  - Error: PROFILE_REQUIRED(409) — users.age_group 또는 gender 가 NULL / UNAUTHORIZED(401)
- POST /api/swipe/answers (인증 필요)
  - Request `SwipeAnswersRequest { answers: { productId: number, liked: boolean }[] }` — 1개 이상
  - Response 200 `SwipeAnswersResponse { likedCount: number, totalCount: number }` — 이 사용자의 **저장된 전체** swipes 기준
  - Error: PRODUCT_NOT_FOUND(404) — 없는 productId 포함 시 전체 거부 / VALIDATION_ERROR(422) — answers 비어 있음 / UNAUTHORIZED(401)
  - 같은 상품 재제출: upsert (liked 덮어씀). 한 요청 안에 같은 productId 가 여러 번 있으면 마지막 값을 쓴다

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
- cards 안에 같은 상품이 두 번 나오지 않는다
- 한 스타일의 카드 수는 그 스타일 몫(count // 5, 나머지를 받은 스타일은 +1)을 넘지 않는다

## 충돌 주의
- swipes 쓰는 다른 피쳐: 없음 (recommendation 은 읽기만)

## 허용 의존
- `common/`, `shared/`만
- 조립: main.py 한 줄, App.tsx 에 `ROUTES.swipe` (RequireAuth)

## UI 결과
- 카드 한 장씩 표시, 좋아요/싫어요 버튼 + 좌우 드래그 (pointer events, 라이브러리 없이)
  - 오른쪽 = 좋아요, 왼쪽 = 싫어요. 드래그 중 카드가 손가락을 따라 이동·살짝 회전
  - 가로 이동이 카드 너비의 30% 이상이면 그 방향으로 확정, 아니면 원위치로 복귀
  - 버튼과 드래그는 같은 답변 처리 함수를 쓴다, 진행률 "n / 전체"
- 마지막 카드 후 자동 제출 → 다음 화면
- 필요 상태: 카드 로딩 / 카드 0장(빈 상태 문구) / PROFILE_REQUIRED 시 프로필 화면으로 안내 / 제출 에러 시 재시도

## 테스트 환경
- 공용 fixture: backend/test/conftest.py — create_product(gender, age_group, style 등 지정 가능), create_user(age_group=..., gender=...), auth_headers
