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
PersonalColorDto    { season: Season, subtype: SeasonSubtype,
                      palette: string[] /* hex, 12유형별 어울리는 색 8개 */,
                      avoidPalette: string[] /* hex, 계절별 피해야 할 색 6개 */,
                      analysis: PersonalColorAnalysisDto, selfieUrl: string, bodyImageUrl: string }
PersonalColorAnalysisDto { faceColors: FaceColorsDto,
                      warmth: number   /* ≥ 0 웜, < 0 쿨 */,
                      depth: number    /* ≥ 0 딥, < 0 라이트 */,
                      clarity: number  /* ≥ 0 선명, < 0 소프트 */,
                      skinLightness: number /* 피부 L* */, contrast: number /* 피부 L* − 머리·눈썹·눈 중 가장 어두운 L* */ }
FaceColorsDto       { skin: string, lip: string, eye: string, eyebrow: string, hair: string /* hex */,
                      eyeColorName: string | null, hairColorName: string | null /* YouCam 이 준 영어 이름 그대로 */ }
SwipeCardDto        { pinId: number, imageUrl: string, style: Style }   // 핀(코디 사진)
WardrobePhotoDto    { id: number, imageUrl: string }
ProductDto          { id: number, title: string, price: number /* 소수 2자리까지 */, currency: string /* ISO 4217, 예: "USD" */,
                      mallName: string, purchaseUrl: string, imageUrl: string, style: Style }
RecommendationItem  { product: ProductDto, score: number, tasteScore: number, colorScore: number,
                      reasonTags: string[] /* 예: "선호하는 미니멀", "가을 웜톤 컬러" */ }
RecommendationResponse { styleTags: string[], season: Season, subtype: SeasonSubtype, palette: string[],
                         isFallback: boolean /* 좋아요 < 3 → 컬러 점수만 */, items: RecommendationItem[] /* 최대 6개 */ }
FittingDto          { id: number, productId: number, status: FittingStatus,
                      originalImageUrl: string, resultImageUrl: string | null }
```

## Enum

| Enum | 값 |
|---|---|
| AgeGroup | `LATE_TEENS` `TWENTIES` `THIRTIES` `FORTIES_PLUS` |
| Gender | `FEMALE` `MALE` |
| Season | `SPRING_WARM` `SUMMER_COOL` `AUTUMN_WARM` `WINTER_COOL` |
| SeasonSubtype | `TRUE` `LIGHT` `DEEP` `BRIGHT` `SOFT` — 계절마다 3개만 유효 (봄: TRUE·LIGHT·BRIGHT / 여름: TRUE·LIGHT·SOFT / 가을: TRUE·DEEP·SOFT / 겨울: TRUE·DEEP·BRIGHT) |
| ProductSource | `EBAY` `NAVER` (NAVER 는 한국어 UI용, 최후순위) |
| Style | `MINIMAL` `CASUAL` `STREET` `FORMAL` `LOVELY` |
| Category | `TOP` (MVP는 상의만) |
| FittingStatus | `PENDING` `DONE` `FAILED` |
| ErrorCode | `UNAUTHORIZED` `VALIDATION_ERROR` `EXTERNAL_API_FAILED` `INTERNAL_ERROR` `NICKNAME_TAKEN` `INVALID_CREDENTIALS` `FACE_NOT_DETECTED` `INVALID_IMAGE` `PROFILE_REQUIRED` `PERSONAL_COLOR_REQUIRED` `PRODUCT_NOT_FOUND` `PIN_NOT_FOUND` `WARDROBE_LIMIT_EXCEEDED` `FITTING_NOT_FOUND` |

## 동작 메모

- **personal_color**: 사진 2장 업로드 (YouCam 조건이 달라서 분리 — 얼굴 색 분석: 얼굴 폭이 사진 폭의 60% 이상 / 피팅: 가슴 위 상반신). 얼굴 사진만 YouCam 얼굴 색 분석 → 응답의 얼굴 색 5개 + 색 이름 2개를 `users.face_colors`에 그대로 저장 → 3축 판정으로 `season`·`season_subtype` 저장. 상반신 사진은 저장만 하고 피팅 원본으로 쓴다. 재업로드 시 덮어씀. 판정 함수·팔레트는 `shared.color`에 둔다 (auth 의 `UserDto.personalColor` 도 같은 함수로 `analysis` 를 다시 계산하므로 슬라이스 안에 두면 안 됨).
- **swipe/cards**: 카드는 상품이 아니라 Pinterest 코디 사진(`pins`). 사용자 성별·나이대 필터 → 스타일별 균등 샘플링(여자 5개 스타일, 남자 미니멀·캐주얼·스트릿 3개), 이미 스와이프한 핀 제외. 답변은 스와이프가 끝난 뒤 한 번에 제출(재제출 시 upsert).
- **recommendation**: 요청마다 계산(저장 X). L·D 는 스와이프한 핀, P·Q 는 핀평균·상품평균(`embedding_centroids`). `u = normalize(mean(L−P) + 1.5·mean(C) − 0.5·mean(D−P))`, `c_i = cos(u, e_i − Q)`, `score = 0.7·taste + 0.3·color`, 성별·나이대 일치 상품 전체 중 상위 6개. color 는 12유형 팔레트 기준이고, 피해야 할 팔레트와 ΔE < 15 이면 절반.
- **fitting**: 같은 (user, product) 결과가 `DONE`이면 캐시 반환. 아니면 `PENDING` 행 생성 후 백그라운드에서 YouCam 호출 → 프론트는 `GET`을 2초 간격 폴링. 실패 시 `FAILED`, 재시도는 다시 `POST`.
- **구매 연결(F6)**: 별도 API 없음. `ProductDto.purchaseUrl`(eBay 상품 페이지)로 이동. 가격은 `currency` 기준으로 표시 (USD 는 `$19.99`).
- **한국어 UI → 네이버 상품 (최후순위)**: products 에 `source` 를 두고, 추천 후보를 화면 언어로 거른다 (en → EBAY, ko → NAVER). 프론트가 요청에 언어를 실어 보내는 방식은 그때 정한다. 지금은 EBAY 만 적재.
- PRD는 비로그인이지만, 사진·결과를 사용자에 묶기 위해 **닉네임+비밀번호 최소 로그인**으로 변경.
