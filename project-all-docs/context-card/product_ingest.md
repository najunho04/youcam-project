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
  - 키워드별 검색어 문자열: {미정}
  - 키워드당 수집 개수 N: {미정}
- 외부 API: 네이버 쇼핑 검색 `GET https://openapi.naver.com/v1/search/shop.json`
  - 헤더 `X-Naver-Client-Id`, `X-Naver-Client-Secret` (settings.naver_client_id / naver_client_secret)
  - 쿼리 `query`, `display`(≤100), `start`, `sort`
  - 응답 items[]: `productId`, `title`(HTML `<b>` 태그 포함), `link`, `image`, `lprice`(문자열), `mallName`
- 매핑: naver_product_id ← productId, title ← title(태그 제거), price ← int(lprice), mall_name ← mallName, purchase_url ← link, image_url ← image
- 출력: products upsert. 같은 naver_product_id 면 갱신, 없으면 삽입
- 이미지: `shared.image.download_image(url)` 로 받아 임베딩·대표색 계산에만 쓰고 **저장하지 않는다**
- 임베딩: `shared.embedding.get_embedding_model().embed_images([...])`
- 대표색 추출 방법: {미정}. Lab 변환은 `shared.color.rgb_to_lab`
- 실패 처리: {미정 — 이미지 다운로드 실패 상품, 네이버 API 실패 시 동작}

## 상하류
- 상류: 사람이 `make ingest` 실행 (하루 1회)
- 하류: swipe(카드 풀), recommendation(랭킹 대상), fitting(상품 이미지 URL)

## 공유 상태 - 호출 없이 얽히는 관계
- 무효화 필요 캐시: 없음
- 기타: 상품이 삭제되면 swipes·fittings 행도 CASCADE 삭제됨. 배치는 상품을 삭제하지 않는다 {삭제 정책 미정 — 보고 참고}

## 횡단 관심사
- 권한: 없음 (내부 배치)
- 트랜잭션 경계: `shared.database.session_scope()` 사용. 경계 단위 {미정 — 키워드 단위 / 전체 1회}
- 에러 처리: 외부 실패는 `AppError(EXTERNAL_API_FAILED)`

## 불변조건
- products 의 모든 NOT NULL 컬럼이 채워진 행만 저장한다
- 같은 배치를 두 번 돌려도 행이 중복되지 않는다 (naver_product_id 기준)
- 상품 이미지 바이트는 디스크·S3 어디에도 저장하지 않는다

## 충돌 주의
- products 쓰는 다른 피쳐: 없음 (나머지는 읽기 전용)

## 허용 의존
- `common/`, `shared/`만. 네이버 API 호출 코드는 이 슬라이스 안에 둔다 (httpx)

## UI 결과
- 없음. 콘솔에 키워드별 수집·저장·실패 건수 출력

## 테스트 환경
- 공용 fixture: backend/test/conftest.py. 테스트에서는 embedding=fake, 네이버 API·이미지 다운로드는 테스트에서 대체해야 함
