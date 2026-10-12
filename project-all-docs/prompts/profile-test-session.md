아래 명세를 보고 계약 테스트를 작성해줘. 3~7개.

- 구현 코드는 열지 말 것. 명세만 보고 작성. (`backend/src/common/`, `backend/src/shared/`, `backend/test/conftest.py` 는 읽어도 됨. `feature/` 는 열지 말 것)
- 정상 케이스 + 불변조건 위반 + 권한 위반을 다룰 것.
- 응답 DTO의 필드와 타입을 검증할 것.
- 명세에 없어서 판단이 안 서는 부분은 지어내지 말고 질문으로 남겨줘.
- 저장 위치: backend/test/contract/profile/ (pytest, 공용 fixture 는 backend/test/conftest.py)
- 이 슬라이스 폴더 밖에는 쓰지 말 것. 작성 후 커밋하지 말고 멈춰서 승인을 기다릴 것.
- 구현이 없으므로 테스트는 실패하는 것이 정상. `SLICE=profile make test-slice` 로 수집 오류(import 에러 등)만 없는지 확인할 것.
- 백엔드 API 계약만 대상. 카드의 프론트·UI 항목은 테스트하지 말 것.
- 사전 상태(다른 컬럼 값, 다른 사용자)는 `create_user(**columns)` fixture 로 만들고, 결과는 응답 또는 `database_session` 으로 확인할 것. 다른 슬라이스 API(signup 등)를 호출해서 상태를 만들지 말 것.

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
