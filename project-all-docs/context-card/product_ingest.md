# 슬라이스: product_ingest

## 목적
eBay Browse API 로 상의 상품을 수집하고, 이미지 임베딩과 대표색을 계산해 products 에 upsert 하는 오프라인 배치. 적재가 끝나면 상품 임베딩 평균을 다시 계산한다. **HTTP 엔드포인트 없음.**

## 경로
- 백: backend/src/feature/product_ingest/ (`python -m feature.product_ingest` 로 실행 → `make ingest`)
- 프론트: 없음
- 계약 테스트: backend/test/contract/product_ingest/ · 단위 테스트: backend/test/unit/product_ingest/

## 데이터
- 읽기: products ((source, external_id) 로 기존 행 조회)
- 쓰기: products (이 테이블의 유일한 쓰기 주체), embedding_centroids (PRODUCT 행만)
- 스키마 발췌 (products):
  - id bigserial PK
  - source varchar — ProductSource (`EBAY`), external_id varchar(100) — UNIQUE (source, external_id) = upsert 키
  - title varchar(255), price numeric(10,2), currency varchar(3), mall_name varchar(100), purchase_url text, image_url text — 전부 NOT NULL
  - gender Gender, age_group AgeGroup, style Style, category Category — NOT NULL (수집 키워드 기준으로 부여)
  - color_lab real[3] NOT NULL — 대표색 CIE Lab
  - embedding vector(512) NOT NULL — L2 정규화
  - updated_at timestamptz NOT NULL
- embedding_centroids: domain(`PRODUCT`) PK, embedding vector(512), updated_at

## 계약 (배치 입출력)
- 입력: 수집 키워드 목록 = Gender × AgeGroup × Style × Category(TOP) — 네이버 때와 같은 조합 40개
  - 키워드별 검색어: `"{성별} {나이대} {스타일} top"` (예: `"women 20s minimal top"`)
    - 성별: FEMALE women / MALE men
    - 나이대: LATE_TEENS teen / TWENTIES 20s / THIRTIES 30s / FORTIES_PLUS 40s
    - 스타일: MINIMAL minimal / CASUAL casual / STREET streetwear / FORMAL formal / LOVELY feminine
  - 키워드당 수집 개수: 50 (API 1회, `limit=50, offset=0`). 키워드 40개 → 최대 약 2,000개
  - 추가 필터 없음 (네이버 때와 같다. 상태·판매 방식·가격으로 거르지 않는다)
- 외부 API: eBay Browse `GET https://api.ebay.com/buy/browse/v1/item_summary/search`
  - 토큰: `POST https://api.ebay.com/identity/v1/oauth2/token` (client credentials, scope `https://api.ebay.com/oauth/api_scope`). settings.ebay_client_id / ebay_client_secret. 토큰은 배치 1회 동안 재사용, 만료되면 다시 받음
  - 헤더 `Authorization: Bearer {token}`, `X-EBAY-C-MARKETPLACE-ID: EBAY_US`
  - 쿼리 `q`, `limit`, `offset`
  - 응답 itemSummaries[]: `itemId`, `title`, `price.value`(문자열), `price.currency`, `image.imageUrl`, `itemWebUrl` (10/31 실제 응답으로 확인)
- 매핑: source ← EBAY, external_id ← itemId, title ← title, price ← Decimal(price.value), currency ← price.currency, mall_name ← 항상 `"eBay"` (판매자 아이디 `seller.username` 은 eBay 사용자 정보라 저장하지 않는다 — 계정 삭제 알림 면제 조건), purchase_url ← itemWebUrl, image_url ← image.imageUrl
- 출력: products upsert. 같은 (source, external_id) 면 갱신, 없으면 삽입
- 이미지: `shared.image.download_image(url)` 로 받아 임베딩·대표색 계산에만 쓰고 **저장하지 않는다**
- 임베딩: `shared.embedding.get_embedding_model().embed_images([...])`
- 착용컷(사람이 입은 사진)도 거르지 않는다. `cloth-v4` 는 착용컷을 참고 이미지로 써도 피팅 품질이 괜찮다
- 대표색 추출 (상품마다 이 배치에서 1회 계산해 `color_lab` 에 저장. 추천은 저장값을 읽기만 하고 다시 계산하지 않는다. K-means 는 상품들이 아니라 사진 한 장의 픽셀을 묶는다): 이미지를 RGB 로 변환 → 가로·세로 가운데 80% 영역 →
  1. 배경 제거: 원본 테두리 1px 픽셀의 중앙값을 배경색으로 보고, 배경색과 ΔE < 12 인 픽셀을 뺀다
  2. 남은 픽셀이 영역의 5% 미만이면 영역 전체를 쓴다
  3. 남은 픽셀을 Lab 으로 바꿔 K-means(k=3, 초기 중심은 L\* 기준 하위·중간·상위 분위수 픽셀, 최대 10회 반복)로 묶는다
  4. 픽셀이 가장 많은 묶음의 중심이 대표색. 무작위는 쓰지 않는다 (같은 이미지면 같은 결과)
  - 착용컷은 피부·머리·하의 색이 섞일 수 있다. 적재 결과를 보고 대표색이 틀리면 피부색과 가까운 묶음을 후보에서 빼는 규칙을 추가한다 (지금은 넣지 않음)
- 상품 임베딩 평균: 모든 키워드 처리 후 products 전체 embedding 평균을 embedding_centroids(PRODUCT) 에 upsert
- 실패 처리 (건너뛰고 계속):
  - 상품 단위 실패(이미지 다운로드 실패, 이미지로 열 수 없음, 필수 필드 누락·변환 실패) → 그 상품만 건너뜀, 실패 상품 수에 더함
  - eBay API 실패 → 그 키워드만 건너뜀, 실패 키워드 수에 더함
  - 키워드가 **전부** 실패하면 종료 코드 1, 그 외 0
- 진입점 (계약 테스트 대상):
  - `feature.product_ingest.run_ingest(search, download) -> IngestReport`
    - `search(query: str, limit: int) -> list[dict]` — eBay 응답 itemSummaries[] 를 그대로 반환. 실패 시 `AppError(EXTERNAL_API_FAILED)`
    - `download(url: str) -> bytes` — 실패 시 `AppError(EXTERNAL_API_FAILED)`
    - `IngestReport { saved: int, failed_products: int, failed_keywords: int }` — saved 는 삽입 + 갱신 건수
  - `python -m feature.product_ingest` 는 실제 eBay 호출 함수와 `shared.image.download_image` 를 넘겨 `run_ingest` 를 실행하고, 결과를 출력한 뒤 위 종료 코드로 끝난다
- 네이버 수집 코드(`naver_client.py`)는 지우지 않는다. 한국어 UI용 네이버 상품(source = NAVER, currency = KRW)은 최후순위로 나중에 붙인다

## 상하류
- 상류: 사람이 `make ingest` 실행 (하루 1회)
- 하류: recommendation(랭킹 대상, PRODUCT 평균), fitting(상품 이미지 URL)

## 공유 상태 - 호출 없이 얽히는 관계
- 무효화 필요 캐시: embedding_centroids(PRODUCT) — 상품이 바뀌면 다시 계산 (이 배치가 한다)
- 기타: 상품이 삭제되면 fittings 행도 CASCADE 삭제됨. 배치는 상품을 삭제하지 않는다 (검색 결과에서 빠진 상품도 남긴다). 네이버 상품을 eBay 로 바꿀 때는 DB 볼륨을 재생성한다 (Alembic 없음)

## 횡단 관심사
- 권한: 없음 (내부 배치)
- 트랜잭션 경계: `shared.database.session_scope()` 사용. 경계 단위는 키워드 1개 = 트랜잭션 1개 (한 키워드 저장 중 DB 오류가 나면 그 키워드만 롤백). 상품 평균 계산은 별도 트랜잭션 1개
- 에러 처리: 외부 실패는 `AppError(EXTERNAL_API_FAILED)`

## 불변조건
- products 의 모든 NOT NULL 컬럼이 채워진 행만 저장한다
- 같은 배치를 두 번 돌려도 행이 중복되지 않는다 ((source, external_id) 기준)
- 같은 상품이 여러 키워드에 나오면 나중 키워드의 값(gender·age_group·style 포함)으로 덮어쓴다. 키워드 순서는 Gender → AgeGroup → Style enum 정의 순서
- 갱신 시 updated_at 이 갱신된다
- 상품 이미지 바이트는 디스크·S3 어디에도 저장하지 않는다
- 배치가 끝나면 embedding_centroids(PRODUCT) 는 products 전체 embedding 평균과 같다

## 충돌 주의
- products 쓰는 다른 피쳐: 없음 (나머지는 읽기 전용)
- embedding_centroids 쓰는 다른 피쳐: 없음 (PIN 행은 핀 적재 스크립트가 1회 계산)

## 허용 의존
- `common/`, `shared/`만. eBay API 호출 코드는 이 슬라이스 안에 둔다 (httpx, `ebay_client.py`)

## UI 결과
- 없음. 콘솔에 키워드별 수집·저장·실패 건수 출력

## 테스트 환경
- 공용 fixture: backend/test/conftest.py. 테스트에서는 embedding=fake, eBay API·이미지 다운로드는 `run_ingest` 에 가짜 `search`·`download` 를 넘겨 대체한다. 이미지 바이트는 `sample_image_bytes`, 결과 확인은 `database_session`
