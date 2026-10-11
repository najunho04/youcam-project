# 슬라이스: fitting

## 목적
추천 상품을 사용자 상반신 사진에 입혀보는 가상 피팅을 비동기로 실행하고, 원본과 결과를 비교해 보여준다. 구매 링크 포함.

## 경로
- 백: backend/src/feature/fitting/
- 프론트: front/src/feature/fitting/
- 계약 테스트: backend/test/contract/fitting/ · 단위 테스트: backend/test/unit/fitting/, front/test/unit/fitting/

## 데이터
- 읽기: users(body_image_key), products(image_url, purchase_url), fittings
- 쓰기: fittings
- 스키마 발췌:
  - fittings.id bigserial PK
  - fittings.user_id bigint NOT NULL FK → users.id
  - fittings.product_id bigint NOT NULL FK → products.id
  - fittings.status varchar — FittingStatus (PENDING | DONE | FAILED)
  - fittings.result_key varchar(255) NULL — DONE 일 때만. `fittings/{userId}/{fittingId}.jpg`
  - UNIQUE (user_id, product_id)

## 계약
- POST /api/fittings (인증 필요)
  - Request `FittingCreateRequest { productId: number }`
  - Response **202** `FittingDto { id: number, productId: number, status: FittingStatus, originalImageUrl: string, resultImageUrl: string|null }`
    - originalImageUrl = get_storage().get_url(users.body_image_key), resultImageUrl = DONE 일 때 get_url(result_key), 아니면 null
  - 동작:
    - (user, product) 행이 DONE → 그대로 반환 (YouCam 호출 없음, 캐시)
    - 행이 PENDING → 그대로 반환 (중복 호출 없음)
    - 행이 없음 또는 FAILED → PENDING 으로 생성/갱신 후 백그라운드 작업 시작 (FastAPI BackgroundTasks)
  - Error: PRODUCT_NOT_FOUND(404) / PERSONAL_COLOR_REQUIRED(409) — body_image_key 없음 / UNAUTHORIZED(401)
- GET /api/fittings/{fittingId} (인증 필요)
  - Response 200 `FittingDto`
  - Error: FITTING_NOT_FOUND(404) — 없음 또는 **다른 사용자의 피팅** / UNAUTHORIZED(401)
- 백그라운드 작업 (`shared.database.session_scope()` 사용):
  1. `youcam.start_cloth_fitting(user_image_url=get_url(body_image_key), garment_image_url=product.image_url)`
  2. `youcam.wait_cloth_fitting(task_id)` → SUCCESS 면 `shared.image.download_image(result_image_url)` → `get_storage().upload(f"fittings/{userId}/{fittingId}.jpg")` → status DONE, result_key 저장
  3. ERROR 또는 예외 → status FAILED

## 상하류
- 상류: 추천 카드의 "입어보기" → `ROUTES.fitting(productId)` 로 이동해 옴
- 하류: "구매하러 가기" → 상품 purchaseUrl (새 탭), "다른 상품 입어보기" → `ROUTES.recommendation`
  - 화면에 상품 정보(이름·가격·purchaseUrl) 표시가 필요하지만 FittingDto 에 없음: {미정 — 보고 참고}

## 공유 상태 - 호출 없이 얽히는 관계
- 무효화 필요 캐시: 없음
- 기타: personal_color 가 사진을 다시 올리면 이 사용자의 fittings 행을 전부 삭제한다 (진행 중인 백그라운드 작업이 끝났을 때 행이 없으면 아무것도 하지 않는다)

## 횡단 관심사
- 권한: 본인 피팅만 조회
- 트랜잭션 경계: POST 요청 1개 + 백그라운드 작업 1개 (별도 세션)
- 크레딧: YouCam 호출은 사용자가 입어보기를 누를 때만, 같은 (사용자, 상품)은 DONE 결과 재사용
- 에러 처리: 공통 규약 따름

## 불변조건
- (user_id, product_id) 당 fittings 행은 최대 1개
- DONE 이면 result_key 가 있고, 그 외에는 resultImageUrl 이 null
- DONE 인 피팅을 다시 요청해도 YouCam 을 호출하지 않는다

## 충돌 주의
- fittings 쓰는 다른 피쳐: personal_color (사진 변경 시 삭제)

## 허용 의존
- `common/`, `shared/`만
- 조립: main.py 한 줄, App.tsx 에 `ROUTES.fittingPattern` (RequireAuth)

## UI 결과
- 진입 시 POST → PENDING 이면 GET 을 2초 간격 폴링 {폴링 최대 시간 미정}
- DONE: 원본 / 결과 비교 보기, "구매하러 가기", "다른 상품 입어보기"
- 필요 상태: 생성 중 로딩("입혀보는 중") / FAILED 시 상품 이미지만 보여주고 "다시 시도"(POST 재호출) / 에러

## 테스트 환경
- 공용 fixture: backend/test/conftest.py — youcam_client(Mock: `cloth_fitting_succeeds` 로 성공/실패 전환, 결과 URL = 상품 이미지 URL), storage, create_user(body_image_key=...), create_product, auth_headers
  - TestClient 에서는 BackgroundTasks 가 응답 직후 동기로 실행된다
  - Mock 결과 URL(상품 image_url)은 실제로 다운로드되지 않으므로 download_image 대체가 필요하다
