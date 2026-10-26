# 로드맵

제출 마감 **2026-11-02**. 오늘(10-11) 기준 약 3주. 마지막 주는 버퍼 + 데모 준비로 비워둔다.

| 단계 | 기간 | 할 일 | 완료 기준 |
|---|---|---|---|
| 0. foundation | 10/12 ~ 10/14 | 스캐폴딩(uv·Vite), docker-compose(db·backend·web), `common/` 모델·DTO·enum, `shared/`(DB·JWT·S3·YouCam·임베딩·에러), 린트 룰, 컨텍스트 카드 8장 | `make dev`로 빈 앱 기동, `make lint` 통과 |
| 1. 레퍼런스 + 데이터 | 10/15 ~ 10/17 | **auth** 단독 구현 → 레퍼런스 지정 / **product_ingest**로 상품 수천 개 적재 | 가입·로그인 E2E 통과, products 행 + 임베딩 존재 |
| 2. 입력 슬라이스 | 10/18 ~ 10/21 | **profile** · **personal_color** · **wardrobe** 병렬 | 사진 2장 → 시즌 결과 화면까지 |
| 3. 취향 | 10/22 ~ 10/23 | **swipe** | 20장 스와이프 → 답변 저장 |
| 4. 추천 | 10/24 ~ 10/26 | **recommendation** (+ 추천 이유 태그, 좋아요<3 폴백) | 추천 5개 1초 이내 |
| 5. 피팅 | 10/27 ~ 10/28 | **fitting** (비동기 + 폴링 + 캐시) | 입어보기 → 결과 → 구매 링크 |
| 6. 배포·데모 | 10/29 ~ 11/02 | EC2 배포, 전체 흐름 E2E, 데모 영상, 버퍼 | 배포 URL에서 3분 내 첫 추천 |

## 제출 전 개편 (10/26 ~ 11/02)

단계 0~6은 완료. 해커톤 심사 기준 점검 결과로 퍼스널컬러와 상품 데이터를 고친다. 제출 마감 **11/02 11:45 EST = 11/03 01:45 KST**.

| 순서 | 기간 | 할 일 | 완료 기준 |
|---|---|---|---|
| A. 준비 | 10/26 | eBay 개발자 계정 · Production 키 활성화 신청 (계정 삭제 알림 구독 또는 면제). 문서·카드 갱신 | 키 발급, 카드 승인 |
| B. 공용 변경 | 10/26 ~ 10/27 | `shared.youcam` 얼굴 색 5개 전부 반환, `shared.color` 판정 함수·12유형 팔레트·피해야 할 팔레트, `common` DTO·enum·entity(users·products) 변경, conftest 갱신 | 승인 커밋 (`approvals.md` 기록) |
| C. personal_color | 10/27 ~ 10/28 | 12유형 판정 + 결과 화면 하단 판정 근거. auth·profile 의 `personalColor` 동기화 | 계약 테스트 통과, 근거 화면 확인 |
| D. product_ingest | 10/28 ~ 10/29 | eBay 수집, 배경 제거 + K-means 대표색, 상품 평균 갱신 | 상품 1,000개 이상 적재 |
| E. recommendation · fitting | 10/29 ~ 10/30 | 12유형 팔레트 + 피해야 할 색 감점, USD 가격 표시 | 추천 6개, 피팅 1회 성공 |
| F. 제출 준비 | 10/31 ~ 11/02 | 배포, 영어 README, 데모 영상(1~3분), 스크린샷, 심사위원용 테스트 계정, 레포 공개·LICENSE | Devpost 제출 완료 |
| Z. 최후순위 | 여유 있을 때 | 한국어 UI에서 네이버 쇼핑 상품 노출 (`products.source = NAVER`, 추천 후보를 화면 언어로 거름) | - |

## DB 재생성 절차 (스키마 변경 시, Alembic 없음)

핀은 레포에 적재 스크립트가 없어 **DB에만 있다**. 통째로 지우지 말고 아래 순서로 한다. 로컬 Docker DB는 10/26 완료 (백업: `project/backend/var/db-backup-20261026/`). **Neon(운영)은 새 코드 배포할 때 같은 절차로 한다.**

1. 전체 백업: `pg_dump -Fc` + 살릴 테이블 데이터만 `pg_dump --data-only --table=…` (users, pins, swipes, wardrobe_photos) + `embedding_centroids` 의 PIN 행
2. `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`
3. 새 코드로 `initialize_database()` (앱 기동 또는 직접 호출) → 새 스키마로 테이블 생성
4. users → pins → swipes → wardrobe_photos 순서로 데이터 복원, PIN 평균 복원
5. 새 판정 근거가 없는 사용자는 `season` 을 NULL 로 (퍼스널컬러 진단 다시 하게). 상품·피팅은 버리고 `make ingest` 로 eBay 상품 적재 → PRODUCT 평균은 배치가 계산

## 미리 해둘 것 (단계 0 전/중)

- [ ] YouCam API 키 · 크레딧 확인, 피부톤 분석 / 의류 피팅 응답 **샘플 저장** (개발 중 목업용)
- [ ] 네이버 쇼핑 검색 API 키 발급
- [x] S3 비공개 버킷 `youcamapi-hackathon-1013` (ap-northeast-2). 로컬은 `~/.aws/credentials`, `.env`에 키 안 넣음
- [ ] EC2 인스턴스 롤: 위 버킷 `s3:PutObject/GetObject/DeleteObject`
- [ ] EC2: 임베딩 모델(torch CPU) 때문에 **RAM 4GB 이상** (t3.medium 이상)

## 컷 라인 (시간 부족 시 이 순서로 버림)

1. wardrobe (F3) — 추천은 스와이프만으로 동작
2. 스와이프 적응형 노출 순서 — 균등 샘플링만
3. 추천 이유 텍스트 임베딩 — 상품 style 태그 + 시즌명으로 대체
