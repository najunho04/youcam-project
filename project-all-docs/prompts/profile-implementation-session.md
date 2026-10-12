아래 슬라이스를 구현해줘.

- backend/test/contract/profile/ 의 테스트를 통과시키되, 그 파일은 수정 금지.
- 공용 레이어(`common/`, `shared/`, `backend/test/conftest.py`)는 읽기 전용. 변경 필요하면 멈추고 보고.
- 세부 단위 테스트는 TDD로 먼저 작성. 위치: backend/test/unit/profile/, front/test/unit/profile/
- 레퍼런스 구조: backend/src/feature/auth/, front/src/feature/auth/ — 폴더 구조·파일 이름·역할을 그대로 따를 것.
  - 다른 슬라이스(auth 포함)의 코드를 import 하지 말 것. UserDto 구성처럼 auth 와 같은 로직이 필요하면 이 슬라이스 안에 따로 둘 것. 공용으로 옮겨야 한다고 판단되면 멈추고 보고.
  - `_reference-slice/` 폴더는 건드리지 말 것.
- 조립 지점에는 이 슬라이스 줄만 추가: backend/src/main.py `FEATURE_ROUTERS`, front/src/app/App.tsx 슬라이스 라우트 구역 (`ROUTES.profile`, RequireAuth 로 감쌈).
- users 의 age_group, gender 외 컬럼은 쓰지 말 것.
- 완료 기준: `SLICE=profile make test-slice` 통과 (계약 + 단위), `make lint` 통과. 커밋은 하지 말고 결과를 보고할 것.

[컨텍스트 카드]

# 슬라이스: profile

## 목적
사용자의 나이대와 성별을 저장한다. 스와이프 이미지 풀 필터에 쓰인다.

## 경로
- 백: backend/src/feature/profile/
- 프론트: front/src/feature/profile/
- 계약 테스트: backend/test/contract/profile/ · 단위 테스트: backend/test/unit/profile/, front/test/unit/profile/

## 데이터
- 읽기: users
- 쓰기: users (age_group, gender 만)
- 스키마 발췌:
  - users.age_group varchar — AgeGroup enum, NULL 허용 (입력 전)
  - users.gender varchar — Gender enum, NULL 허용

## 계약
- PUT /api/users/me/profile (인증 필요)
  - Request `ProfileUpdateRequest { ageGroup: AgeGroup, gender: Gender }` — 둘 다 필수
  - Response 200 `UserDto { id, nickname, ageGroup, gender, personalColor: PersonalColorDto|null }`
    - personalColor 는 users.season, selfie_key, body_image_key 가 **모두** 있을 때만 채움: `{ season, palette: SEASON_PALETTES[season], selfieUrl: get_url(selfie_key), bodyImageUrl: get_url(body_image_key) }` (get_url = `get_storage().get_url`)
  - Error: UNAUTHORIZED(401), VALIDATION_ERROR(422) — enum 밖 값·누락
- enum: AgeGroup = LATE_TEENS | TWENTIES | THIRTIES | FORTIES_PLUS, Gender = FEMALE | MALE

## 상하류
- 상류: 가입 직후 화면 흐름 (auth → 이 화면)
- 하류: 저장 후 퍼스널컬러 화면(`ROUTES.personalColor`)으로 이동. 저장된 값은 swipe 가 카드 필터로 읽는다

## 공유 상태 - 호출 없이 얽히는 관계
- 무효화 필요 캐시: 없음
- 기타: 값 변경 시 이미 저장된 swipes 는 그대로 둔다

## 횡단 관심사
- 권한: 본인만 (`shared.security.CurrentUser`)
- 트랜잭션 경계: 요청 1개
- 에러 처리: 공통 규약 따름

## 불변조건
- 다른 사용자의 프로필은 바꿀 수 없다 (경로에 사용자 id 없음, 토큰 기준)
- users 의 다른 컬럼(nickname, season, selfie_key, body_image_key 등)은 바뀌지 않는다
- 같은 값으로 여러 번 호출해도 결과가 같다

## 충돌 주의
- users 쓰는 다른 피쳐: auth(nickname, password_hash), personal_color(season, selfie_key, body_image_key)

## 허용 의존
- `common/`, `shared/`만
- 조립: main.py `FEATURE_ROUTERS` 한 줄, App.tsx 에 `ROUTES.profile` (RequireAuth 로 감쌈)

## UI 결과
- 나이대 4개 선택지(10대 후반 / 20대 / 30대 / 40대 이상), 성별 2개(여성 / 남성), "다음" 버튼 (둘 다 선택해야 활성)
- 이미 값이 있으면 선택된 상태로 표시 (기존 값은 GET /api/users/me 의 ageGroup·gender)
- 필요 상태: 저장 중 로딩 / 에러 메시지

## 테스트 환경
- 공용 fixture: backend/test/conftest.py (client, create_user, auth_headers)
