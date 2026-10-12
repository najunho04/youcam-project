아래 명세를 보고 계약 테스트를 작성해줘. 3~7개.

- 구현 코드는 열지 말 것. 명세만 보고 작성. (`backend/src/common/`, `backend/src/shared/`, `backend/test/conftest.py` 는 읽어도 됨. `feature/` 는 열지 말 것)
- 정상 케이스 + 불변조건 위반 + 권한 위반을 다룰 것.
- 응답 DTO의 필드와 타입을 검증할 것.
- 명세에 없어서 판단이 안 서는 부분은 지어내지 말고 질문으로 남겨줘.
- 저장 위치: backend/test/contract/wardrobe/ (pytest, 공용 fixture 는 backend/test/conftest.py)
- 이 슬라이스 폴더 밖에는 쓰지 말 것. 작성 후 커밋하지 말고 멈춰서 승인을 기다릴 것.
- 구현이 없으므로 테스트는 실패하는 것이 정상. `SLICE=wardrobe make test-slice` 로 수집 오류(import 에러 등)만 없는지 확인할 것.
- 백엔드 API 계약만 대상. 카드의 프론트·UI 항목은 테스트하지 말 것.
- 사전 상태는 fixture(`create_user(**columns)` 등)나 `database_session` 으로 직접 만들 것. 다른 슬라이스 API를 호출해서 상태를 만들지 말 것.
- 이미지는 `sample_image_bytes` 로 만들 것. 저장소 상태는 `storage.objects`, 행·embedding 차원은 `database_session` 으로 확인할 것.
- 기존 사진이 있는 상태는 `database_session` 으로 `common.entity` 모델을 직접 넣어 만들 것.

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
