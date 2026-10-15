# 전체 API 명세

> 사람이 조망하는 용도. 세션에는 넣지 않는다. 여기서 나온 DTO/enum은 `project/*/src/common/`에 코드로 내려놓는다.

## 기술 스택 / 인프라

| 구분 | 선택 | 이유 |
|---|---|---|
| 백엔드 | Python 3.13 · FastAPI · SQLAlchemy 2 · Pydantic v2 · uv | 임베딩(FashionCLIP)이 파이썬 생태계. 서버·배치를 한 언어로 |
| DB | PostgreSQL 16 + pgvector (컨테이너) | 벡터DB를 따로 안 띄우고 상품 메타 + 벡터를 한 테이블에 |
| 프론트 | React 18 · Vite · TypeScript · React Router | |
| 스토리지 | S3 (private 버킷, presigned GET URL로 노출) | 사용자 사진·피팅 결과만. 상품 이미지는 저장 X (URL만) |
| 배포 | EC2 1대 · Docker Compose (`db` / `backend` / `web`=nginx) | nginx가 프론트 정적 파일 서빙 + `/api` → backend 프록시 |
| 테스트 | pytest(백) · Vitest(프론트) · Playwright(E2E) | |

## 공통 규약

- Base path: `/api`. JSON은 **camelCase** (Pydantic alias).
- 인증: `Authorization: Bearer {accessToken}` (JWT, 만료 7일, 리프레시 없음). `auth` 외 전부 필요.
- 에러 응답: `{ "error": { "code": ErrorCode, "message": string } }`
- 공통 에러: `UNAUTHORIZED`(401, 토큰 없음/만료), `VALIDATION_ERROR`(422), `EXTERNAL_API_FAILED`(502, YouCam·S3 실패), `INTERNAL_ERROR`(500)
- 이미지 URL은 전부 presigned URL(만료 1시간) 또는 외부 상품 URL. 클라이언트는 그대로 `<img src>`에 쓴다.

## 엔드포인트

| 슬라이스 | Method | Path | Request | Response | Error |
|---|---|---|---|---|---|
| auth | POST | /api/auth/signup | `{ nickname, password }` | `AuthResponse` | NICKNAME_TAKEN(409) |
| auth | POST | /api/auth/login | `{ nickname, password }` | `AuthResponse` | INVALID_CREDENTIALS(401) |
| auth | GET | /api/users/me | - | `UserDto` | UNAUTHORIZED |
| profile | PUT | /api/users/me/profile | `{ ageGroup, gender }` | `UserDto` | - |
| personal_color | POST | /api/personal-color | multipart `selfie`(얼굴) + `bodyImage`(상반신), 각 jpg/png ≤10MB | `PersonalColorDto` | FACE_NOT_DETECTED(422), INVALID_IMAGE(400) |
| swipe | GET | /api/swipe/cards?count=20 | - | `{ cards: SwipeCardDto[] }` | PROFILE_REQUIRED(409) |
| swipe | POST | /api/swipe/answers | `{ answers: { pinId, liked }[] }` | `{ likedCount, totalCount }` | PIN_NOT_FOUND(404) |
| wardrobe | POST | /api/wardrobe-photos | multipart `images[]` 1~4장 | `{ photos: WardrobePhotoDto[] }` | INVALID_IMAGE(400), WARDROBE_LIMIT_EXCEEDED(409) |
| recommendation | GET | /api/recommendations | - | `RecommendationResponse` | PROFILE_REQUIRED(409), PERSONAL_COLOR_REQUIRED(409) |
| fitting | POST | /api/fittings | `{ productId }` | `FittingDto` (202) | PRODUCT_NOT_FOUND(404), PERSONAL_COLOR_REQUIRED(409, 상반신 사진 없음) |
| fitting | GET | /api/fittings/{fittingId} | - | `FittingDto` | FITTING_NOT_FOUND(404) |
| product_ingest | (CLI) | `make ingest` | - | - | HTTP 없음. 오프라인 배치 |

## DTO

```ts
AuthResponse        { accessToken: string, user: UserDto }
UserDto             { id: number, nickname: string, ageGroup: AgeGroup | null, gender: Gender | null,
                      personalColor: PersonalColorDto | null }
PersonalColorDto    { season: Season, palette: string[] /* hex */, selfieUrl: string, bodyImageUrl: string }
SwipeCardDto        { pinId: number, imageUrl: string, style: Style }   // 핀(코디 사진)
WardrobePhotoDto    { id: number, imageUrl: string }
ProductDto          { id: number, title: string, price: number, mallName: string,
                      purchaseUrl: string, imageUrl: string, style: Style }
RecommendationItem  { product: ProductDto, score: number, tasteScore: number, colorScore: number,
                      reasonTags: string[] /* 예: "미니멀", "가을 웜톤 베이지" */ }
RecommendationResponse { styleTags: string[], season: Season, palette: string[],
                         isFallback: boolean /* 좋아요 < 3 → 인기 상품 */, items: RecommendationItem[] /* 5개 */ }
FittingDto          { id: number, productId: number, status: FittingStatus,
                      originalImageUrl: string, resultImageUrl: string | null }
```

## Enum

| Enum | 값 |
|---|---|
| AgeGroup | `LATE_TEENS` `TWENTIES` `THIRTIES` `FORTIES_PLUS` |
| Gender | `FEMALE` `MALE` |
| Season | `SPRING_WARM` `SUMMER_COOL` `AUTUMN_WARM` `WINTER_COOL` |
| Style | `MINIMAL` `CASUAL` `STREET` `FORMAL` `LOVELY` |
| Category | `TOP` (MVP는 상의만) |
| FittingStatus | `PENDING` `DONE` `FAILED` |
| ErrorCode | `UNAUTHORIZED` `VALIDATION_ERROR` `EXTERNAL_API_FAILED` `INTERNAL_ERROR` `NICKNAME_TAKEN` `INVALID_CREDENTIALS` `FACE_NOT_DETECTED` `INVALID_IMAGE` `PROFILE_REQUIRED` `PERSONAL_COLOR_REQUIRED` `PRODUCT_NOT_FOUND` `PIN_NOT_FOUND` `WARDROBE_LIMIT_EXCEEDED` `FITTING_NOT_FOUND` |

## 동작 메모

- **personal_color**: 사진 2장 업로드 (YouCam 조건이 달라서 분리 — 피부톤: 얼굴 폭이 사진 폭의 60% 이상 / 피팅: 가슴 위 상반신). 얼굴 사진만 피부톤 분석 → 시즌 매핑 → `users`에 저장. 상반신 사진은 저장만 하고 피팅 원본으로 쓴다. 재업로드 시 덮어씀. 시즌별 팔레트는 코드 상수(`common/enums` 옆 매핑 테이블).
- **swipe/cards**: 카드는 상품이 아니라 Pinterest 코디 사진(`pins`). 사용자 성별·나이대 필터 → 스타일별 균등 샘플링(여자 5개 스타일, 남자 미니멀·캐주얼·스트릿 3개), 이미 스와이프한 핀 제외. 답변은 스와이프가 끝난 뒤 한 번에 제출(재제출 시 upsert).
- **recommendation**: 요청마다 계산(저장 X). L·D 는 스와이프한 핀, P·Q 는 핀평균·상품평균(`embedding_centroids`). `u = normalize(mean(L−P) + 1.5·mean(C) − 0.5·mean(D−P))`, `c_i = cos(u, e_i − Q)`, `score = 0.7·taste + 0.3·color`, 성별·나이대 일치 상품 전체 중 상위 5개.
- **fitting**: 같은 (user, product) 결과가 `DONE`이면 캐시 반환. 아니면 `PENDING` 행 생성 후 백그라운드에서 YouCam 호출 → 프론트는 `GET`을 2초 간격 폴링. 실패 시 `FAILED`, 재시도는 다시 `POST`.
- **구매 연결(F6)**: 별도 API 없음. `ProductDto.purchaseUrl`(네이버 쇼핑 링크)로 이동.
- PRD는 비로그인이지만, 사진·결과를 사용자에 묶기 위해 **닉네임+비밀번호 최소 로그인**으로 변경.
