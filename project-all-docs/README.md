# project-all-docs

총괄 설계 문서. **사람만 읽는다.** 세션에는 통째로 넣지 않고, 슬라이스당 `context-card/` 1장만 프롬프트에 붙인다.

원칙상 레포 밖(Notion 등)에 두는 폴더다. 이 템플릿에서는 편의상 형제 폴더로 두었으며, 세션은 반드시 `project/`에서 연다. 동기화가 필요할 때만 최상위(real-root)에서 새 세션을 연다.

| 파일 | 용도 |
|---|---|
| `context-card/` | 슬라이스당 1장. `_template.md` 복사해서 작성 |
| `api.md` | 전체 API 명세 — 엔드포인트, 요청/응답 |
| `erd.md` | 전체 ERD — 테이블, 관계, 제약 |
| `feature-graph.md` | 피쳐 의존 그래프 — 슬라이스 목록, 상하류, 병렬 가능 묶음 |
| `checklist.md` | 슬라이스 완료 체크리스트 |
| `loop-config.md` | 루프 엔지니어링 설정 — 목표 지표 / 불변 게이트 / 최대 반복 횟수 |
| `approvals.md` | 계약·공용 레이어 변경 승인 기록 |

여기서 나온 **엔티티·DTO·enum은 `project/*/src/common/`에 코드로 내려놓는다.** 그건 세션이 읽는다.
