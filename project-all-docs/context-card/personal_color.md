# 슬라이스: personal_color

## 목적
얼굴 사진과 상반신 사진 2장을 받는다. 얼굴 사진으로 YouCam 얼굴 색 분석을 해서 응답의 얼굴 색 5개(피부·입술·눈·눈썹·머리)를 **전부** 써서 퍼스널컬러 12유형(시즌 + 세부 유형)을 판정하고, 판정 근거를 함께 돌려준다. 상반신 사진은 가상 피팅 원본으로 저장한다.

## 경로
- 백: backend/src/feature/personal_color/
- 프론트: front/src/feature/personal_color/
- 계약 테스트: backend/test/contract/personal_color/ · 단위 테스트: backend/test/unit/personal_color/, front/test/unit/personal_color/

## 데이터
- 읽기: users
- 쓰기: users (season, season_subtype, face_colors, selfie_key, body_image_key 만), fittings (해당 사용자 행 삭제)
- 스키마 발췌:
  - users.season varchar — Season enum, NULL 허용
  - users.season_subtype varchar — SeasonSubtype enum, NULL 허용 (season 과 함께 쓰고 함께 NULL)
  - users.face_colors jsonb — `{ skin, lip, eye, eyebrow, hair, eyeColorName, hairColorName }`, NULL 허용
  - users.selfie_key varchar(255) — 얼굴 사진. S3 키 `selfies/{userId}/{uuid}.{jpg|png}`, NULL 허용
  - users.body_image_key varchar(255) — 상반신 사진. S3 키 `body-images/{userId}/{uuid}.{jpg|png}`, NULL 허용
  - fittings.user_id bigint FK → users.id

## 계약
- POST /api/personal-color (인증 필요, multipart/form-data)
  - Request: 필드 `selfie`(얼굴 사진) + `bodyImage`(상반신 사진) — 둘 다 필수, 각각 jpg/png 10MB 이하
  - Response 200 `PersonalColorDto`
    ```
    { season: Season, subtype: SeasonSubtype,
      palette: string[] (hex 8개), avoidPalette: string[] (hex 6개),
      analysis: { faceColors: { skin, lip, eye, eyebrow, hair: hex, eyeColorName: string|null, hairColorName: string|null },
                  warmth: number, depth: number, clarity: number, skinLightness: number, contrast: number },
      selfieUrl: string, bodyImageUrl: string }
    ```
  - Error:
    - INVALID_IMAGE(400) — 둘 중 하나라도 이미지 아님 / 형식 / 용량 (`shared.image.read_upload_image` 가 던짐)
    - VALIDATION_ERROR(422) — 필드 누락
    - FACE_NOT_DETECTED(422) — 얼굴 사진에서 YouCam 얼굴 인식 실패 (`youcam.analyze_face_colors` 가 던짐)
    - EXTERNAL_API_FAILED(502) — YouCam·저장소 실패, YouCam 응답에 hex 5개 중 하나라도 없음
    - UNAUTHORIZED(401)
- 처리 순서:
  1. 두 파일 모두 `read_upload_image(file)` 검증
  2. `get_storage().upload(new_object_key("selfies", ...))`, `upload(new_object_key("body-images", ...))`
  3. `get_youcam_client().analyze_face_colors(get_storage().get_url(selfie_key))` → `FaceColors` (상반신 사진은 분석하지 않음)
  4. `shared.color.judge_personal_color(face_colors)` → `PersonalColorJudgment { season, subtype, analysis }`
  5. users.season, season_subtype, face_colors, selfie_key, body_image_key 저장. 이전 키가 있으면 저장소에서 삭제. 해당 사용자의 fittings 행 전부 삭제
- palette = `shared.color.SUBTYPE_PALETTES[(season, subtype)]`, avoidPalette = `shared.color.AVOID_PALETTES[season]`

## 판정 규칙 (`shared.color.judge_personal_color` — auth 도 같은 함수를 쓰므로 공용)
- 모든 색은 `shared.color.hex_to_lab` 으로 CIE Lab. 색상각 h = atan2(b\*, a\*) (도), 채도 C = √(a\*² + b\*²)
- 대비 contrast = L\*(피부) − min(L\*(머리), L\*(눈썹), L\*(눈))
- 3개 축 (0 이 경계, 기준값은 `shared.color` 상수 — 기획 조정 대상):
  - warmth = 0.7 × (h(피부) − 58) / 10 + 0.3 × (h(입술) − 25) / 20
  - depth = 0.5 × (72 − L\*(피부)) / 8 + 0.5 × (contrast − 50) / 15
  - clarity = 0.6 × (C(피부) − 20) / 5 + 0.4 × (C(입술) − 45) / 12
- 시즌: warmth ≥ 0 이면 웜, depth ≥ 0 이면 딥
  - 웜+라이트 = SPRING_WARM / 쿨+라이트 = SUMMER_COOL / 웜+딥 = AUTUMN_WARM / 쿨+딥 = WINTER_COOL
- 세부 유형: 시즌별 후보 3개의 점수 중 최댓값. 같으면 아래 나열 순서가 앞인 것
  - 점수: TRUE = |warmth|, LIGHT = −depth, DEEP = depth, BRIGHT = clarity, SOFT = −clarity
  - SPRING_WARM: TRUE, LIGHT, BRIGHT / SUMMER_COOL: TRUE, LIGHT, SOFT / AUTUMN_WARM: TRUE, DEEP, SOFT / WINTER_COOL: TRUE, DEEP, BRIGHT
- analysis 의 숫자 5개(warmth, depth, clarity, skinLightness, contrast)는 소수 둘째 자리 반올림. 판정은 반올림 전 값으로 한다
- 예시 (skin / lip / eye / eyebrow / hair → 결과):
  - `#F6DCC2 / #E8907A / #8A6A4A / #A08060 / #B08A60` → SPRING_WARM · LIGHT (warmth +1.26, depth −1.34, clarity −0.54)
  - `#F2D3B1 / #E07A5F / #6B4A2B / #7A5A3A / #8B6A45` → SPRING_WARM · TRUE (+1.39, −0.83, +0.33)
  - `#D8C0B8 / #B88890 / #5A5048 / #6A605A / #5A524C` → SUMMER_COOL · SOFT (−1.17, −0.64, −2.03)
  - `#B07B4F / #B5553A / #3B2414 / #3A2618 / #2E1C10` → AUTUMN_WARM · DEEP (+0.68, +0.79, +2.06)
  - `#E3C0A6 / #C8646E / #3A2A22 / #3B2E28 / #231C19` → AUTUMN_WARM · TRUE (+0.32, +0.13, −0.11)
  - `#C9A79A / #A8354F / #1E1714 / #1A1514 / #141212` → WINTER_COOL · TRUE (−0.92, +0.57, −0.38)

## 상하류
- 상류: profile 저장 후 이동해 옴
- 하류: 결과 확인 후 스와이프 화면(`ROUTES.swipe`)으로 이동. season·season_subtype 은 recommendation 이, body_image_key 는 fitting 이 원본 사진으로 읽는다. auth 의 `GET /api/users/me` 는 같은 `PersonalColorDto` 를 users 컬럼으로 다시 만든다

## 공유 상태 - 호출 없이 얽히는 관계
- 무효화 필요 캐시: fittings 테이블의 해당 사용자 행 (사진이 바뀌면 피팅 결과 무효)
- 기타: 없음

## 횡단 관심사
- 권한: 본인만 (`CurrentUser`)
- 트랜잭션 경계: 요청 1개. 분석 실패 시 users·fittings 는 바뀌지 않아야 한다. 이번 요청에서 업로드한 새 파일은 저장소에서 삭제한다
- 에러 처리: 공통 규약 따름
- YouCam 은 `get_youcam_client()` 로만 호출 (테스트·개발은 mock)

## 불변조건
- 분석에 실패하면 기존 season·season_subtype·face_colors·selfie_key·body_image_key 가 유지되고, 저장소에 새 파일이 남지 않는다 (기존 파일도 지워지지 않는다)
- 성공하면 해당 사용자의 기존 fittings 가 남아 있지 않다
- subtype 은 항상 season 의 후보 3개 중 하나다
- 응답의 palette·avoidPalette 는 `SUBTYPE_PALETTES[(season, subtype)]`·`AVOID_PALETTES[season]` 와 같다
- 응답의 analysis.faceColors 는 YouCam 응답 값 그대로다 (hex 는 대문자 `#RRGGBB` 로 맞춘다)

## 충돌 주의
- users 쓰는 다른 피쳐: auth, profile (다른 컬럼)
- fittings 쓰는 다른 피쳐: fitting (생성·갱신)

## 허용 의존
- `common/`, `shared/`만
- 조립: main.py 한 줄, App.tsx 에 `ROUTES.personalColor` (RequireAuth)

## UI 결과
- 사진 2칸, 칸마다 가이드 + 파일 선택/촬영(안내 촬영 다이얼로그) + 미리보기
  - 얼굴 사진: 정면, 자연광, 화장 최소화, 얼굴이 화면을 가득 채우게, 머리카락이 보이게
  - 상반신 사진: 정면으로 서서, 가슴 위 상반신과 어깨가 보이게, 혼자 나오게
- 두 장 모두 선택해야 "분석하기" 버튼 활성
- 결과 상단: 시즌 + 세부 유형 이름 (영어 예: "Deep Autumn", 한국어 예: "가을 웜톤 · 딥") + 어울리는 팔레트 칩 8개 + 피해야 할 팔레트 칩 6개 + 얼굴 사진 + "다음" 버튼
- 결과 하단 **판정 근거**:
  1. YouCam 이 찾은 얼굴 색 5개 칩 (피부·입술·눈·눈썹·머리) + 눈·머리 색 이름 (있을 때만)
  2. 3개 축 막대: 웜 ↔ 쿨(warmth), 라이트 ↔ 딥(depth), 소프트 ↔ 브라이트(clarity). 0 이 가운데, 값의 부호 쪽으로 채움
  3. 보조 수치: 피부 명도(skinLightness), 대비(contrast)
  4. 판정 문장: 시즌은 웜/쿨 + 명도로, 세부 유형은 가장 두드러진 축으로 정했다는 설명 (예: "노란 기가 도는 피부와 코랄 입술로 웜, 피부와 머리색 대비가 커서 딥 → 가을 웜톤. 그중 깊이가 가장 두드러져 딥")
- 필요 상태: 분석 중 로딩(수 초 소요) / FACE_NOT_DETECTED 시 얼굴 사진 재촬영 안내 + 가이드 다시 표시 / 기타 에러
- 상반신 사진이 피팅 조건에 맞는지는 여기서 검사하지 않는다 (피팅 실패 시 fitting 화면에서 FAILED 로 드러남)

## 테스트 환경
- 공용 fixture: backend/test/conftest.py — youcam_client(Mock: `face_detected`, `face_colors` 속성으로 동작 변경), storage(Memory: `objects` dict), sample_image_bytes, create_user(season·season_subtype·face_colors 지정 가능), auth_headers
