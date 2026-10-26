아래 슬라이스를 재작업해줘.

- 이번 작업은 **재작업**이다. 슬라이스 코드는 이미 있고, 공용 레이어와 계약 테스트가 새 카드 기준으로 바뀌었다 (커밋 84416b5, 958ef9e). 기존 코드를 아래 카드에 맞게 고칠 것.
- backend/test/contract/auth/ 의 테스트를 통과시키되, 그 파일은 수정 금지.
- 공용 레이어(`common/`, `shared/`, `backend/test/conftest.py`, front `common/`·`shared/`)는 읽기 전용. 변경이 필요하면 멈추고 보고.
- `shared.color.SEASON_PALETTES` 는 개편 전 임시 별칭이다. 새 코드에서 쓰지 말 것 (`SUBTYPE_PALETTES`·`AVOID_PALETTES` 사용).
- 기존 단위 테스트(backend/test/unit/auth/, front/test/unit/auth/)가 깨져 있다. 새 카드 기준으로 TDD 로 고칠 것 (테스트를 먼저 고치고 구현). 다른 슬라이스의 단위 테스트는 건드리지 말 것.
- 다른 슬라이스의 코드를 import 하지 말 것. 공용으로 옮겨야 한다고 판단되면 멈추고 보고.
- 조립 지점(backend/src/main.py `FEATURE_ROUTERS`, front/src/app/App.tsx)은 이미 연결돼 있다. 바꾸지 말 것.
- 바뀌는 것은 `/api/users/me` 의 `personalColor` 형태뿐이다. 판정 근거는 `shared.color.judge_personal_color(FaceColorsDto.model_validate(users.face_colors)).analysis` 로 다시 만든다. season·subtype 은 저장값을 쓴다.
- 가입·로그인 동작은 바꾸지 말 것. 프론트 변경은 단위 테스트의 PersonalColorDto 목업 갱신 정도다.
- 완료 기준: `SLICE=auth make test-slice` 통과 (계약 + 단위), `make lint` 통과, 프론트 `npx tsc -b` 오류 없음. 커밋은 하지 말고 결과를 보고할 것.

[컨텍스트 카드]

# 슬라이스: auth

## 목적
닉네임 + 비밀번호로 가입·로그인하고, 로그인한 사용자 정보를 조회한다. 랜딩 화면 포함. **레퍼런스 슬라이스** (단독 구현).

## 경로
- 백: backend/src/feature/auth/
- 프론트: front/src/feature/auth/
- 계약 테스트: backend/test/contract/auth/ · 단위 테스트: backend/test/unit/auth/, front/test/unit/auth/

## 데이터
- 읽기: users
- 쓰기: users (nickname, password_hash 만)
- 스키마 발췌:
  - users.id bigserial PK
  - users.nickname varchar(20) NOT NULL UNIQUE
  - users.password_hash varchar(255) NOT NULL (bcrypt)
  - users.age_group, gender, season, selfie_key, body_image_key — NULL 허용. 이 슬라이스는 읽기만 (UserDto 구성용)

## 계약
- POST /api/auth/signup
  - Request `AuthRequest { nickname: string(2~20), password: string(4~72) }`
  - Response 200 `AuthResponse { accessToken: string, user: UserDto }` — 가입 직후 user 의 ageGroup·gender·personalColor 는 null
  - Error: NICKNAME_TAKEN(409) — 같은 닉네임 존재 / VALIDATION_ERROR(422) — 길이 위반
- POST /api/auth/login
  - Request `AuthRequest`
  - Response 200 `AuthResponse`
  - Error: INVALID_CREDENTIALS(401) — 닉네임 없음 또는 비밀번호 불일치 (둘을 구분하지 않음) / VALIDATION_ERROR(422) — 길이 위반 (signup 과 동일)
- GET /api/users/me (인증 필요)
  - Response 200 `UserDto`
  - Error: UNAUTHORIZED(401) — 토큰 없음/만료/위조, 또는 토큰은 유효하나 해당 사용자가 DB 에 없음
- DTO
  - `UserDto { id: number, nickname: string, ageGroup: AgeGroup|null, gender: Gender|null, personalColor: PersonalColorDto|null }`
  - `PersonalColorDto` (personal_color 카드와 같은 형태: season, subtype, palette, avoidPalette, analysis, selfieUrl, bodyImageUrl) — users.season, season_subtype, face_colors, selfie_key, body_image_key 가 **모두** 있을 때만 채움. season·subtype 은 저장값, analysis 는 `shared.color.judge_personal_color(users.face_colors).analysis` 로 다시 만든다 (같은 입력이면 같은 결과). palette 는 `shared.color.SUBTYPE_PALETTES[(season, subtype)]`, avoidPalette 는 `AVOID_PALETTES[season]`, selfieUrl 은 `get_storage().get_url(selfie_key)`, bodyImageUrl 은 `get_storage().get_url(body_image_key)`
- 에러 응답 형태: `{ "error": { "code": ErrorCode, "message": string } }` (shared/exception 이 처리. 슬라이스는 `AppError(ErrorCode.X)` 만 던짐)

## 상하류
- 상류: 없음 (첫 화면)
- 하류: 가입·로그인 성공 시 accessToken 을 `shared/auth` 의 `tokenStorage.set()` 으로 저장 → 다음 화면으로 이동
  - 다음 화면: 가입 → 프로필 화면(`ROUTES.profile`), 로그인 → 메인 화면(`ROUTES.landing`, `/`)
  - 메인 "이어하기" → profile / personal_color / recommendation 화면 (UI 결과의 이동 규칙)

## 공유 상태 - 호출 없이 얽히는 관계
- 무효화 필요 캐시: 없음
- 발행 이벤트: 없음
- 구독 이벤트: 없음
- 기타: accessToken 은 localStorage (`shared/auth` 의 tokenStorage). `GET /api/users/me` 는 다른 슬라이스 화면에서도 진행 상태 확인용으로 호출될 수 있음

## 횡단 관심사
- 권한: signup·login 은 인증 불필요. users/me 는 `shared.security.CurrentUser` 의존성 사용
- 비밀번호: `shared.security.hash_password / verify_password`, 토큰: `create_access_token(user_id)` (JWT, 7일)
- 트랜잭션 경계: 요청 1개 = 트랜잭션 1개 (`shared.database.get_database_session`)
- 에러 처리: 공통 규약 따름

## 불변조건
- 닉네임은 유일하다 (DB UNIQUE 위반도 NICKNAME_TAKEN 으로 변환)
- 닉네임은 trim 하지 않고 대소문자를 구분한다 ("Abc" 와 "abc" 는 다른 닉네임)
- 비밀번호 원문은 저장·로그·응답 어디에도 남지 않는다
- 응답에 password_hash 가 포함되지 않는다

## 충돌 주의
- users 쓰는 다른 피쳐: profile(age_group, gender), personal_color(season, selfie_key, body_image_key) — 이 슬라이스는 그 컬럼을 쓰지 않는다

## 허용 의존
- `common/`, `shared/`만
- 조립: backend/src/main.py `FEATURE_ROUTERS` 에 한 줄, front/src/app/App.tsx 슬라이스 라우트에 `/`, `/signup`, `/login` (경로 상수는 `shared/navigation` 의 ROUTES)

## UI 결과
- 메인(`/`) — 토큰 유무(`tokenStorage.get()`)로 두 가지 화면
  - 비로그인: 서비스 소개 한 줄 + "시작하기"(→ `ROUTES.signup`) + "로그인" 링크(→ `ROUTES.login`)
  - 로그인: 서비스 소개 한 줄 + "{nickname} 님, 반가워요" + "이어하기" + "로그아웃"
    - 진입 시 `GET /api/users/me` 호출 (nickname 표시용)
    - "이어하기" 이동 규칙: ageGroup 또는 gender 가 null → `ROUTES.profile` / personalColor 가 null → `ROUTES.personalColor` / 둘 다 있음 → `ROUTES.recommendation`
    - "로그아웃": `tokenStorage.clear()` 후 비로그인 화면으로 전환 (서버 호출 없음)
    - users/me 가 401 이면 토큰이 지워지므로(`shared/api`) 비로그인 화면으로 전환
- 가입(`/signup`)·로그인(`/login`): 닉네임·비밀번호 입력, 제출 버튼
- 필요 상태
  - 가입·로그인: 제출 중 로딩(버튼 비활성) / 에러 — NICKNAME_TAKEN·INVALID_CREDENTIALS 메시지를 폼 아래 표시
  - 메인(로그인): users/me 로딩 중에는 "이어하기" 비활성 / 네트워크 에러 시 ErrorMessage + 다시 시도
- UI 컴포넌트는 `shared/ui` (PageLayout, Button, Loading, ErrorMessage), API 호출은 `shared/api` 의 apiRequest

## 테스트 환경
- 공용 fixture: backend/test/conftest.py (client, create_user, auth_headers 등). DB 는 테스트마다 비워진다
