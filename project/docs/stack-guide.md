# 스택 커스텀 가이드

하네스는 언어 무관이다. 스택에 맞춰 손대는 건 **`Makefile` 명령 5개**와 **import 금지 린트 룰 1개**뿐이다.

## 1. `Makefile` — 명령 5개

타겟 이름은 바꾸지 않는다 (`CLAUDE.md`가 참조). `TODO`를 실제 명령으로 교체한다.

| 타겟 | 역할 | Spring + React 예 |
|---|---|---|
| `dev` | 개발 서버 | `./gradlew bootRun & (cd front && npm run dev)` |
| `test` | 단위 + 계약 전체 | `./gradlew test && (cd front && npm test)` |
| `test-slice` | 자기 슬라이스만 (`SLICE=` 필수) | `./gradlew test --tests "*feature.$(SLICE)*"` |
| `test-e2e` | E2E | `npx playwright test` |
| `lint` | import 금지 검사 | `./gradlew archTest && (cd front && npx eslint .)` |

`test-slice` 스택별:

| 스택 | 예 |
|---|---|
| Jest / Vitest | `npx vitest run feature/$(SLICE) test/unit/$(SLICE)` |
| Gradle | `./gradlew test --tests "*feature.$(SLICE)*"` |
| pytest | `pytest backend/test/unit/$(SLICE)` |
| Go | `go test ./backend/feature/$(SLICE)/...` |

## 2. 린트 룰 — "다른 `feature/` 폴더 import 금지" 1개

| 스택 | 파일 | 규칙 |
|---|---|---|
| TypeScript / JS | `front/.eslintrc` | `no-restricted-imports` — `feature/*` 안에서 다른 `feature/*` 경로 금지 |
| Java / Kotlin | `backend/src/test/.../ArchTest.java` | ArchUnit `noClasses().that().resideInAPackage("..feature.(*)..").should().dependOnClassesThat().resideInAPackage("..feature..")` + 같은 슬라이스 예외 |
| Python | `.importlinter` | `[importlinter:contract:slices]` `type = independence` `modules = feature.*` |
| Go | 패키지 구조 | `feature/{slice}/internal/` — 컴파일러가 차단 |
| Rust | 크레이트 분리 | 슬라이스별 크레이트. `Cargo.toml`에 없으면 컴파일 불가 |

만든 룰을 실행하는 명령을 `Makefile`의 `lint:` 타겟 밑에 쓴다. 예: `./gradlew archTest`, `npx eslint .`, `lint-imports`.

## 계약 테스트

`test/contract/`는 백엔드 테스트 프레임워크(JUnit, pytest, vitest…)로 HTTP 호출 → 응답 DTO 필드·타입을 검증한다. 프론트와 언어가 다르면 이 테스트가 타입 공유를 대신하므로 응답 스키마 검증(JSON Schema, zod, Pydantic 등)을 넣는 게 좋다.

## 손대지 않는 것

- `CLAUDE.md`, `.claude/settings.json`, `.githooks/pre-commit`, `.claudeignore` — 경로 기반. 언어 무관
- 디렉토리 구조, 컨텍스트 카드, 프롬프트, 체크리스트 — 언어 무관
- `.githooks/pre-commit`의 경로 목록은 디렉토리 구조를 바꿨을 때만 갱신
