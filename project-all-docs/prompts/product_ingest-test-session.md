아래 명세를 보고 계약 테스트를 작성해줘. 3~7개.

- 구현 코드는 열지 말 것. 명세만 보고 작성. (`backend/src/common/`, `backend/src/shared/`, `backend/test/conftest.py` 는 읽어도 됨. `feature/` 는 열지 말 것)
- 이 슬라이스는 HTTP 엔드포인트가 없는 배치다. 계약 대상은 `feature.product_ingest.run_ingest(search, download)` 의 입출력과 products 테이블 상태다.
- 정상 케이스 + 불변조건(upsert 중복 없음, 키워드 간 덮어쓰기, NOT NULL) + 실패 처리(상품 단위·키워드 단위 건너뛰기)를 다룰 것.
- `IngestReport` 의 필드와 값, 저장된 products 의 컬럼 값(매핑·검색어별 gender/age_group/style/category·color_lab·embedding 512차원)을 검증할 것.
- 네이버 API·이미지 다운로드는 가짜 `search`·`download` 함수를 넘겨 대체할 것. 실제 네트워크를 호출하지 말 것. 이미지 바이트는 `sample_image_bytes`, 결과는 `database_session` 으로 확인할 것.
- 대표색 검증은 단색 이미지처럼 기대값이 명확한 경우만 사용할 것.
- 종료 코드·콘솔 출력(`python -m feature.product_ingest`)은 테스트하지 말 것.
- 명세에 없어서 판단이 안 서는 부분은 지어내지 말고 질문으로 남겨줘.
- 저장 위치: backend/test/contract/product_ingest/ (pytest, 공용 fixture 는 backend/test/conftest.py)
- 이 슬라이스 폴더 밖에는 쓰지 말 것. 작성 후 커밋하지 말고 멈춰서 승인을 기다릴 것.
- 구현이 없으므로 테스트는 실패하는 것이 정상. `SLICE=product_ingest make test-slice` 로 수집 오류(import 에러 등)만 없는지 확인할 것. 구현이 없어서 import 가 실패하면 테스트 함수 안에서 import 할 것.

[컨텍스트 카드]

# 슬라이스: product_ingest

## 목적
네이버 쇼핑 검색 API 로 상의 상품을 수집하고, 이미지 임베딩과 대표색을 계산해 products 에 upsert 하는 오프라인 배치. **HTTP 엔드포인트 없음.**

## 경로
- 백: backend/src/feature/product_ingest/ (`python -m feature.product_ingest` 로 실행 → `make ingest`)
- 프론트: 없음
- 계약 테스트: backend/test/contract/product_ingest/ · 단위 테스트: backend/test/unit/product_ingest/

## 데이터
- 읽기: products (naver_product_id 로 기존 행 조회)
- 쓰기: products (이 테이블의 유일한 쓰기 주체)
- 스키마 발췌 (products):
  - id bigserial PK
  - naver_product_id varchar(50) NOT NULL UNIQUE — upsert 키
  - title varchar(255), price int, mall_name varchar(100), purchase_url text, image_url text — 전부 NOT NULL
  - gender Gender, age_group AgeGroup, style Style, category Category — NOT NULL (수집 키워드 기준으로 부여)
  - color_lab real[3] NOT NULL — 대표색 CIE Lab
  - embedding vector(512) NOT NULL — L2 정규화
  - updated_at timestamptz NOT NULL

## 계약 (배치 입출력)
- 입력: 수집 키워드 목록 = Gender × AgeGroup × Style × Category(TOP)
  - 키워드별 검색어 문자열: `"{성별} {나이대} {스타일} 상의"` (예: `"여성 20대 미니멀 상의"`)
    - 성별: FEMALE 여성 / MALE 남성
    - 나이대: LATE_TEENS 10대 / TWENTIES 20대 / THIRTIES 30대 / FORTIES_PLUS 40대
    - 스타일: MINIMAL 미니멀 / CASUAL 캐주얼 / STREET 스트릿 / FORMAL 포멀 / LOVELY 러블리
  - 키워드당 수집 개수 N: 50 (API 1회, `display=50, start=1, sort=sim`). 키워드 40개 → 최대 약 2,000개
- 외부 API: 네이버 쇼핑 검색 `GET https://openapi.naver.com/v1/search/shop.json`
  - 헤더 `X-Naver-Client-Id`, `X-Naver-Client-Secret` (settings.naver_client_id / naver_client_secret)
  - 쿼리 `query`, `display`(≤100), `start`, `sort`
  - 응답 items[]: `productId`, `title`(HTML `<b>` 태그 포함), `link`, `image`, `lprice`(문자열), `mallName`
- 매핑: naver_product_id ← productId, title ← title(HTML 태그 제거 + HTML 엔티티 복원), price ← int(lprice), mall_name ← mallName, purchase_url ← link, image_url ← image
- 출력: products upsert. 같은 naver_product_id 면 갱신, 없으면 삽입
- 이미지: `shared.image.download_image(url)` 로 받아 임베딩·대표색 계산에만 쓰고 **저장하지 않는다**
- 임베딩: `shared.embedding.get_embedding_model().embed_images([...])`
- 대표색 추출 방법: 이미지를 RGB 로 변환 → 가로·세로 가운데 50% 영역 → R·G·B 가 모두 240 이상인 픽셀(흰 배경)을 제외하고 평균 → `shared.color.rgb_to_lab`. 제외 후 남는 픽셀이 없으면 가운데 영역 전체 평균
- 실패 처리 (건너뛰고 계속):
  - 상품 단위 실패(이미지 다운로드 실패, 이미지로 열 수 없음, 필수 필드 누락·변환 실패) → 그 상품만 건너뜀, 실패 상품 수에 더함
  - 네이버 API 실패 → 그 키워드만 건너뜀, 실패 키워드 수에 더함
  - 키워드가 **전부** 실패하면 종료 코드 1, 그 외 0
- 진입점 (계약 테스트 대상):
  - `feature.product_ingest.run_ingest(search, download) -> IngestReport`
    - `search(query: str, display: int) -> list[dict]` — 네이버 응답 items[] 를 그대로 반환. 실패 시 `AppError(EXTERNAL_API_FAILED)`
    - `download(url: str) -> bytes` — 실패 시 `AppError(EXTERNAL_API_FAILED)`
    - `IngestReport { saved: int, failed_products: int, failed_keywords: int }` — saved 는 삽입 + 갱신 건수
  - `python -m feature.product_ingest` 는 실제 네이버 호출 함수와 `shared.image.download_image` 를 넘겨 `run_ingest` 를 실행하고, 결과를 출력한 뒤 위 종료 코드로 끝난다

## 상하류
- 상류: 사람이 `make ingest` 실행 (하루 1회)
- 하류: swipe(카드 풀), recommendation(랭킹 대상), fitting(상품 이미지 URL)

## 공유 상태 - 호출 없이 얽히는 관계
- 무효화 필요 캐시: 없음
- 기타: 상품이 삭제되면 swipes·fittings 행도 CASCADE 삭제됨. 배치는 상품을 삭제하지 않는다 (검색 결과에서 빠진 상품도 남긴다)

## 횡단 관심사
- 권한: 없음 (내부 배치)
- 트랜잭션 경계: `shared.database.session_scope()` 사용. 경계 단위는 키워드 1개 = 트랜잭션 1개 (한 키워드 저장 중 DB 오류가 나면 그 키워드만 롤백)
- 에러 처리: 외부 실패는 `AppError(EXTERNAL_API_FAILED)`

## 불변조건
- products 의 모든 NOT NULL 컬럼이 채워진 행만 저장한다
- 같은 배치를 두 번 돌려도 행이 중복되지 않는다 (naver_product_id 기준)
- 같은 상품이 여러 키워드에 나오면 나중 키워드의 값(gender·age_group·style 포함)으로 덮어쓴다. 키워드 순서는 Gender → AgeGroup → Style enum 정의 순서
- 갱신 시 updated_at 이 갱신된다
- 상품 이미지 바이트는 디스크·S3 어디에도 저장하지 않는다

## 충돌 주의
- products 쓰는 다른 피쳐: 없음 (나머지는 읽기 전용)

## 허용 의존
- `common/`, `shared/`만. 네이버 API 호출 코드는 이 슬라이스 안에 둔다 (httpx)

## UI 결과
- 없음. 콘솔에 키워드별 수집·저장·실패 건수 출력

## 테스트 환경
- 공용 fixture: backend/test/conftest.py. 테스트에서는 embedding=fake, 네이버 API·이미지 다운로드는 `run_ingest` 에 가짜 `search`·`download` 를 넘겨 대체한다. 이미지 바이트는 `sample_image_bytes`, 결과 확인은 `database_session`
