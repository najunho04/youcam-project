아래 명세를 보고 계약 테스트를 작성해줘. 3~7개.

- 구현 코드는 열지 말 것. 명세만 보고 작성. (`backend/src/common/`, `backend/src/shared/`, `backend/test/conftest.py` 는 읽어도 됨. `feature/` 는 열지 말 것)
- 정상 케이스 + 불변조건 위반 + 권한 위반을 다룰 것.
- 응답 DTO의 필드와 타입을 검증할 것.
- 명세에 없어서 판단이 안 서는 부분은 지어내지 말고 질문으로 남겨줘.
- 저장 위치: backend/test/contract/personal_color/ (pytest, 공용 fixture 는 backend/test/conftest.py)
- 이 슬라이스 폴더 밖에는 쓰지 말 것. 작성 후 커밋하지 말고 멈춰서 승인을 기다릴 것.
- 구현이 없으므로 테스트는 실패하는 것이 정상. `SLICE=personal_color make test-slice` 로 수집 오류(import 에러 등)만 없는지 확인할 것.
- 백엔드 API 계약만 대상. 카드의 프론트·UI 항목은 테스트하지 말 것.
- 사전 상태는 fixture(`create_user(**columns)` 등)나 `database_session` 으로 직접 만들 것. 다른 슬라이스 API를 호출해서 상태를 만들지 말 것.
- YouCam 은 `youcam_client` fixture(Mock)의 `face_detected`, `skin_color_hex` 를 바꿔서 제어할 것. 저장소 상태는 `storage.objects` 로 확인할 것. 이미지는 `sample_image_bytes` 로 만들 것.
- 시즌 판정은 카드의 예시 hex 만 사용할 것 (경계값 근처 hex 를 새로 만들지 말 것).
- fittings 사전 행은 `create_product` + `database_session` 으로 `common.entity` 모델을 직접 넣을 것.

[컨텍스트 카드]

# 슬라이스: personal_color

## 목적
얼굴 사진과 상반신 사진 2장을 받는다. 얼굴 사진으로 YouCam 피부톤 분석을 해서 퍼스널컬러 시즌을 진단하고, 상반신 사진은 가상 피팅 원본으로 저장한다.

## 경로
- 백: backend/src/feature/personal_color/
- 프론트: front/src/feature/personal_color/
- 계약 테스트: backend/test/contract/personal_color/ · 단위 테스트: backend/test/unit/personal_color/, front/test/unit/personal_color/

## 데이터
- 읽기: users
- 쓰기: users (season, selfie_key, body_image_key 만), fittings (해당 사용자 행 삭제)
- 스키마 발췌:
  - users.season varchar — Season enum, NULL 허용
  - users.selfie_key varchar(255) — 얼굴 사진. S3 키 `selfies/{userId}/{uuid}.{jpg|png}`, NULL 허용
  - users.body_image_key varchar(255) — 상반신 사진. S3 키 `body-images/{userId}/{uuid}.{jpg|png}`, NULL 허용
  - fittings.user_id bigint FK → users.id

## 계약
- POST /api/personal-color (인증 필요, multipart/form-data)
  - Request: 필드 `selfie`(얼굴 사진) + `bodyImage`(상반신 사진) — 둘 다 필수, 각각 jpg/png 10MB 이하
  - Response 200 `PersonalColorDto { season: Season, palette: string[] (hex), selfieUrl: string, bodyImageUrl: string }`
  - Error:
    - INVALID_IMAGE(400) — 둘 중 하나라도 이미지 아님 / 형식 / 용량 (`shared.image.read_upload_image` 가 던짐)
    - VALIDATION_ERROR(422) — 필드 누락
    - FACE_NOT_DETECTED(422) — 얼굴 사진에서 YouCam 얼굴 인식 실패 (`youcam.analyze_skin_tone` 이 던짐)
    - EXTERNAL_API_FAILED(502) — YouCam·저장소 실패
    - UNAUTHORIZED(401)
- 처리 순서:
  1. 두 파일 모두 `read_upload_image(file)` 검증
  2. `get_storage().upload(new_object_key("selfies", ...))`, `upload(new_object_key("body-images", ...))`
  3. `get_youcam_client().analyze_skin_tone(get_storage().get_url(selfie_key))` → `SkinToneResult.skin_color_hex` (상반신 사진은 분석하지 않음)
  4. 피부색 hex → Season 판정 (Lab 2축, `shared.color.hex_to_lab` 사용):
     - 웜/쿨: b* ≥ 18 → 웜, b* < 18 → 쿨
     - 밝기: L* ≥ 70 → 밝음(봄·여름), L* < 70 → 어두움(가을·겨울)
     - 웜+밝음 = SPRING_WARM / 쿨+밝음 = SUMMER_COOL / 웜+어두움 = AUTUMN_WARM / 쿨+어두움 = WINTER_COOL
     - 기준값 18·70 은 슬라이스 상수로 둔다
     - 예시 (L*, b*): `#F2D3B1`(86.3, 20.8) → SPRING_WARM / `#F5D5C8`(87.6, 10.5) → SUMMER_COOL / `#B07B4F`(56.0, 32.1) → AUTUMN_WARM / `#8E6A63`(48.2, 9.5) → WINTER_COOL
  5. users.season, selfie_key, body_image_key 저장. 이전 키가 있으면 저장소에서 삭제. 해당 사용자의 fittings 행 전부 삭제
- palette = `shared.color.SEASON_PALETTES[season]`

## 상하류
- 상류: profile 저장 후 이동해 옴
- 하류: 결과 확인 후 스와이프 화면(`ROUTES.swipe`)으로 이동. season 은 recommendation 이, body_image_key 는 fitting 이 원본 사진으로 읽는다

## 공유 상태 - 호출 없이 얽히는 관계
- 무효화 필요 캐시: fittings 테이블의 해당 사용자 행 (사진이 바뀌면 피팅 결과 무효)
- 기타: 없음

## 횡단 관심사
- 권한: 본인만 (`CurrentUser`)
- 트랜잭션 경계: 요청 1개. 분석 실패 시 users·fittings 는 바뀌지 않아야 한다. 이번 요청에서 업로드한 새 파일은 저장소에서 삭제한다
- 에러 처리: 공통 규약 따름
- YouCam 은 `get_youcam_client()` 로만 호출 (테스트·개발은 mock)

## 불변조건
- 분석에 실패하면 기존 season·selfie_key·body_image_key 가 유지되고, 저장소에 새 파일이 남지 않는다 (기존 파일도 지워지지 않는다)
- 성공하면 해당 사용자의 기존 fittings 가 남아 있지 않다
- 응답의 palette 는 season 의 SEASON_PALETTES 와 같다

## 충돌 주의
- users 쓰는 다른 피쳐: auth, profile (다른 컬럼)
- fittings 쓰는 다른 피쳐: fitting (생성·갱신)

## 허용 의존
- `common/`, `shared/`만
- 조립: main.py 한 줄, App.tsx 에 `ROUTES.personalColor` (RequireAuth)

## UI 결과
- 사진 2칸, 칸마다 가이드 + 파일 선택/촬영(`<input type="file" accept="image/*" capture="user">`) + 미리보기
  - 얼굴 사진: 정면, 자연광, 화장 최소화, 얼굴이 화면을 가득 채우게
  - 상반신 사진: 정면으로 서서, 가슴 위 상반신과 어깨가 보이게, 혼자 나오게
- 두 장 모두 선택해야 "분석하기" 버튼 활성
- 결과: 시즌 이름(한글 표기: 봄 웜톤 / 여름 쿨톤 / 가을 웜톤 / 겨울 쿨톤) + 팔레트 색 칩 + 얼굴 사진 + "다음" 버튼
- 필요 상태: 분석 중 로딩(수 초 소요) / FACE_NOT_DETECTED 시 얼굴 사진 재촬영 안내 + 가이드 다시 표시 / 기타 에러
- 상반신 사진이 피팅 조건에 맞는지는 여기서 검사하지 않는다 (피팅 실패 시 fitting 화면에서 FAILED 로 드러남)

## 테스트 환경
- 공용 fixture: backend/test/conftest.py — youcam_client(Mock: `face_detected`, `skin_color_hex` 속성으로 동작 변경), storage(Memory: `objects` dict), sample_image_bytes, create_user, auth_headers
