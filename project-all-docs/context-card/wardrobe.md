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
    - photos 범위: {미정 — 이번에 올린 것만 / 사용자 전체}
  - Error:
    - INVALID_IMAGE(400) — 하나라도 이미지가 아니면 전체 거부
    - WARDROBE_LIMIT_EXCEEDED(409) — 기존 개수 + 이번 개수 > 4
    - VALIDATION_ERROR(422) — images 0개 또는 5개 이상
    - UNAUTHORIZED(401)
- 처리: `read_upload_image` 검증 → `get_storage().upload(new_object_key("wardrobe", ...))` → `get_embedding_model().embed_images([...])` → 행 저장
- 임베딩 전 전처리(배경 제거·상의 크롭): {미정}

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
