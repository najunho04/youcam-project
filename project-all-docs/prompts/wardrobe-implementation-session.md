아래 슬라이스를 구현해줘.

- backend/test/contract/wardrobe/ 의 테스트를 통과시키되, 그 파일은 수정 금지.
- 공용 레이어(`common/`, `shared/`, `backend/test/conftest.py`)는 읽기 전용. 변경 필요하면 멈추고 보고.
- 세부 단위 테스트는 TDD로 먼저 작성. 위치: backend/test/unit/wardrobe/, front/test/unit/wardrobe/
- 레퍼런스 구조: backend/src/feature/auth/, front/src/feature/auth/ — 폴더 구조·파일 이름·역할을 그대로 따를 것.
  - 다른 슬라이스(auth 포함)의 코드를 import 하지 말 것. 같은 로직이 필요하면 이 슬라이스 안에 따로 둘 것. 공용으로 옮겨야 한다고 판단되면 멈추고 보고.
  - `_reference-slice/` 폴더는 건드리지 말 것.
- 조립 지점에는 이 슬라이스 줄만 추가: backend/src/main.py `FEATURE_ROUTERS`, front/src/app/App.tsx 슬라이스 라우트 구역 (`ROUTES.wardrobe`, RequireAuth 로 감쌈).
- 임베딩은 `get_embedding_model()` 로만 접근할 것.
- 완료 기준: `SLICE=wardrobe make test-slice` 통과 (계약 + 단위), `make lint` 통과. 커밋은 하지 말고 결과를 보고할 것.

[컨텍스트 카드]

# 슬라이스: wardrobe

## 목적
좋아하는 착용 사진·옷 사진을 1~4장 올려 취향 분석에 반영한다. 건너뛸 수 있다. (컷 라인 1순위)

## 경로
- 백: backend/src/feature/wardrobe/
- 프론트: front/src/feature/wardrobe/
- 계약 테스트: backend/test/contract/wardrobe/ · 단위 테스트: backend/test/unit/wardrobe/, front/test/unit/wardrobe/

## 데이터
- 읽기: wardrobe_photos (사용자별 개수)
- 쓰기: wardrobe_photos
- 스키마 발췌:
  - wardrobe_photos.id bigserial PK
  - wardrobe_photos.user_id bigint NOT NULL FK → users.id ON DELETE CASCADE
  - wardrobe_photos.image_key varchar(255) NOT NULL — `wardrobe/{userId}/{uuid}.{jpg|png}`
  - wardrobe_photos.embedding vector(512) NOT NULL
  - 사용자당 최대 4장 (`common.entity.WARDROBE_PHOTO_LIMIT`)

## 계약
- POST /api/wardrobe-photos (인증 필요, multipart/form-data)
  - Request: 필드 `images` 1~4개 — 각각 jpg/png, 10MB 이하
  - Response 200 `WardrobePhotosResponse { photos: WardrobePhotoDto[] }`, `WardrobePhotoDto { id: number, imageUrl: string }`
    - photos 범위: 이번 업로드 후 사용자의 전체 사진 (기존 + 이번), id 오름차순
  - Error:
    - INVALID_IMAGE(400) — 하나라도 이미지가 아니면 전체 거부
    - WARDROBE_LIMIT_EXCEEDED(409) — 기존 개수 + 이번 개수 > 4
    - VALIDATION_ERROR(422) — images 0개 또는 5개 이상
    - UNAUTHORIZED(401)
- 처리: `read_upload_image` 검증 → `get_storage().upload(new_object_key("wardrobe", ...))` → `get_embedding_model().embed_images([...])` → 행 저장
- 임베딩 전 전처리: 없음 (검증된 원본 이미지를 그대로 임베딩)

## 상하류
- 상류: 스와이프 완료 후 이동해 옴
- 하류: 업로드 또는 "건너뛰기" 후 추천 화면(`ROUTES.recommendation`). 저장된 embedding 은 recommendation 이 가중치 1.5 로 읽는다

## 공유 상태 - 호출 없이 얽히는 관계
- 무효화 필요 캐시: 없음 (추천은 요청마다 계산)

## 횡단 관심사
- 권한: 본인만 (`CurrentUser`)
- 트랜잭션 경계: 요청 1개. 일부 실패 시 전체 롤백
- 에러 처리: 공통 규약 따름

## 불변조건
- 사용자당 wardrobe_photos 는 4장을 넘지 않는다
- 저장된 embedding 은 512차원
- 거부된 요청은 행을 하나도 남기지 않는다

## 충돌 주의
- wardrobe_photos 쓰는 다른 피쳐: 없음

## 허용 의존
- `common/`, `shared/`만
- 조립: main.py 한 줄, App.tsx 에 `ROUTES.wardrobe` (RequireAuth)

## UI 결과
- 안내 문구 + 사진 선택(최대 4장, 미리보기) + "업로드" + "건너뛰기"
- 필요 상태: 업로드 중 로딩 / 에러(형식·개수 초과) / 0장 선택 시 업로드 버튼 비활성

## 테스트 환경
- 공용 fixture: backend/test/conftest.py — storage, embedding_model(fake), sample_image_bytes, create_user, auth_headers
