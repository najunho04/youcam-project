# 전체 ERD

> 테이블, 관계, 제약. 사람용. 세션에는 슬라이스 카드의 "스키마 발췌"로만 전달한다.

해커톤 최소 설계: **테이블 5개.** 취향 벡터·추천 결과·팔레트는 저장하지 않는다(요청 시 계산 / 코드 상수).

```mermaid
erDiagram
  users ||--o{ swipes : makes
  users ||--o{ wardrobe_photos : uploads
  users ||--o{ fittings : requests
  products ||--o{ swipes : "is swiped"
  products ||--o{ fittings : "is fitted"

  users {
    bigint id PK
    varchar nickname UK
    varchar password_hash
    varchar age_group
    varchar gender
    varchar season
    varchar selfie_key
    varchar body_image_key
    timestamptz created_at
  }
  products {
    bigint id PK
    varchar naver_product_id UK
    varchar title
    int price
    varchar mall_name
    text purchase_url
    text image_url
    varchar gender
    varchar age_group
    varchar style
    varchar category
    real_array color_lab
    vector embedding
    timestamptz updated_at
  }
  swipes {
    bigint user_id PK,FK
    bigint product_id PK,FK
    boolean liked
    timestamptz created_at
  }
  wardrobe_photos {
    bigint id PK
    bigint user_id FK
    varchar image_key
    vector embedding
    timestamptz created_at
  }
  fittings {
    bigint id PK
    bigint user_id FK
    bigint product_id FK
    varchar status
    varchar result_key
    timestamptz created_at
  }
```

## 테이블

### users — 계정 + 프로필 + 퍼스널컬러 (1:1 정보는 분리하지 않음)
| 컬럼 | 타입 | 제약 | 쓰는 슬라이스 |
|---|---|---|---|
| id | bigserial | PK | auth |
| nickname | varchar(20) | NOT NULL, UNIQUE | auth |
| password_hash | varchar(255) | NOT NULL (bcrypt) | auth |
| age_group | AgeGroup | NULL (프로필 입력 전) | profile |
| gender | Gender | NULL | profile |
| season | Season | NULL (진단 전) | personal_color |
| selfie_key | varchar(255) | NULL. 얼굴 사진. S3 키 `selfies/{userId}/{uuid}.jpg` | personal_color (피부톤 분석) |
| body_image_key | varchar(255) | NULL. 상반신 사진. S3 키 `body-images/{userId}/{uuid}.jpg` | personal_color (쓰기) · fitting (원본으로 읽기) |
| created_at | timestamptz | NOT NULL DEFAULT now() | |

### products — 네이버 쇼핑 상품 + 임베딩 (벡터DB 역할)
| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | bigserial | PK |
| naver_product_id | varchar(50) | NOT NULL, UNIQUE (배치 upsert 키) |
| title | varchar(255) | NOT NULL |
| price | int | NOT NULL |
| mall_name | varchar(100) | NOT NULL |
| purchase_url | text | NOT NULL |
| image_url | text | NOT NULL (외부 URL. 이미지 저장 X) |
| gender | Gender | NOT NULL |
| age_group | AgeGroup | NOT NULL |
| style | Style | NOT NULL (수집 키워드 기준) |
| category | Category | NOT NULL |
| color_lab | real[3] | NOT NULL. 대표색 Lab |
| embedding | vector(512) | NOT NULL. L2 정규화 |
| updated_at | timestamptz | NOT NULL |

- 인덱스: `(gender, age_group, category)`. 상품 수천 개 규모라 벡터 인덱스(HNSW)는 생략 — 필터 후 전수 계산으로 충분.
- 쓰기는 `product_ingest`만. 나머지 슬라이스는 읽기 전용.

### swipes — 좋아요/싫어요
| 컬럼 | 타입 | 제약 |
|---|---|---|
| user_id | bigint | PK, FK → users.id ON DELETE CASCADE |
| product_id | bigint | PK, FK → products.id ON DELETE CASCADE |
| liked | boolean | NOT NULL |
| created_at | timestamptz | NOT NULL DEFAULT now() |

### wardrobe_photos — 옷장 사진 (F3, 선택)
| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | bigserial | PK |
| user_id | bigint | NOT NULL, FK → users.id ON DELETE CASCADE |
| image_key | varchar(255) | NOT NULL. S3 키 `wardrobe/{userId}/{uuid}.jpg` |
| embedding | vector(512) | NOT NULL |
| created_at | timestamptz | NOT NULL DEFAULT now() |

- 사용자당 최대 4장 (애플리케이션 검사).

### fittings — 가상 피팅 결과 + 캐시
| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | bigserial | PK |
| user_id | bigint | NOT NULL, FK → users.id ON DELETE CASCADE |
| product_id | bigint | NOT NULL, FK → products.id ON DELETE CASCADE |
| status | FittingStatus | NOT NULL |
| result_key | varchar(255) | NULL (DONE일 때만). S3 키 `fittings/{userId}/{id}.jpg` |
| created_at | timestamptz | NOT NULL DEFAULT now() |

- UNIQUE `(user_id, product_id)` — 캐시 키. 실패 후 재시도는 같은 행을 `PENDING`으로 갱신.
- 사진을 다시 올리면 해당 사용자의 `fittings` 행을 삭제(원본이 바뀌므로 캐시 무효).

## 저장하지 않는 것
- 취향 벡터 / 추천 결과: 요청 시 swipes + wardrobe_photos로 계산 (스와이프 20개 평균이라 수 ms)
- 시즌별 팔레트, 스타일 태그 텍스트 임베딩: 코드 상수 / 서버 기동 시 1회 계산
- enum은 DB enum 타입 대신 `varchar` + 애플리케이션 enum (마이그레이션 단순화)
- 스키마 관리: 해커톤이라 Alembic 없이 `create_all` + 시드. 스키마 변경 시 DB 볼륨 재생성
