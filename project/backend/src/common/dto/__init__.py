"""요청·응답 DTO. JSON 은 camelCase (alias). 원본 명세는 project-all-docs/api.md. 프론트 타입은 front/src/common/type 과 1:1."""
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from common.enums import AgeGroup, FittingStatus, Gender, Season, SeasonSubtype, Style
from common.error import ErrorCode


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


# ---- 공통 ----
class ErrorBody(CamelModel):
    code: ErrorCode
    message: str


class ErrorResponse(CamelModel):
    error: ErrorBody


# ---- auth ----
class AuthRequest(CamelModel):
    nickname: str = Field(min_length=2, max_length=20)
    password: str = Field(min_length=4, max_length=72)


class FaceColorsDto(CamelModel):
    """YouCam 얼굴 색 분석 응답 그대로. hex 는 대문자 #RRGGBB. users.face_colors 에 이 JSON 을 저장한다."""
    skin: str
    lip: str
    eye: str
    eyebrow: str
    hair: str
    eye_color_name: str | None  # YouCam 이 준 영어 이름 (Brown, Blue …)
    hair_color_name: str | None


class PersonalColorAnalysisDto(CamelModel):
    """판정 근거. 축 3개는 0 이 경계. 숫자는 소수 둘째 자리 반올림."""
    face_colors: FaceColorsDto
    warmth: float  # ≥ 0 웜, < 0 쿨
    depth: float  # ≥ 0 딥, < 0 라이트
    clarity: float  # ≥ 0 선명, < 0 소프트
    skin_lightness: float  # 피부 L*
    contrast: float  # 피부 L* − 머리·눈썹·눈 중 가장 어두운 L*


class PersonalColorDto(CamelModel):
    season: Season
    subtype: SeasonSubtype
    palette: list[str]  # hex 8개, 12유형별 어울리는 색. 예: "#C8A27A"
    avoid_palette: list[str]  # hex 6개, 시즌별 피해야 할 색
    analysis: PersonalColorAnalysisDto
    selfie_url: str  # 얼굴 사진
    body_image_url: str  # 상반신 사진 (가상 피팅 원본)


class UserDto(CamelModel):
    id: int
    nickname: str
    age_group: AgeGroup | None
    gender: Gender | None
    personal_color: PersonalColorDto | None


class AuthResponse(CamelModel):
    access_token: str
    user: UserDto


# ---- profile ----
class ProfileUpdateRequest(CamelModel):
    age_group: AgeGroup
    gender: Gender


# ---- swipe ----
class SwipeCardDto(CamelModel):
    pin_id: int
    image_url: str
    style: Style


class SwipeCardsResponse(CamelModel):
    cards: list[SwipeCardDto]


class SwipeAnswer(CamelModel):
    pin_id: int
    liked: bool


class SwipeAnswersRequest(CamelModel):
    answers: list[SwipeAnswer] = Field(min_length=1)


class SwipeAnswersResponse(CamelModel):
    liked_count: int
    total_count: int


# ---- wardrobe ----
class WardrobePhotoDto(CamelModel):
    id: int
    image_url: str


class WardrobePhotosResponse(CamelModel):
    photos: list[WardrobePhotoDto]


# ---- recommendation ----
class ProductDto(CamelModel):
    id: int
    title: str
    price: float  # 소수 2자리까지 (DB numeric)
    currency: str  # ISO 4217, 예: "USD"
    mall_name: str
    purchase_url: str
    image_url: str
    style: Style


class RecommendationItem(CamelModel):
    product: ProductDto
    score: float
    taste_score: float
    color_score: float
    reason_tags: list[str]


class RecommendationResponse(CamelModel):
    style_tags: list[str]
    season: Season
    subtype: SeasonSubtype
    palette: list[str]
    is_fallback: bool
    items: list[RecommendationItem]


# ---- fitting ----
class FittingCreateRequest(CamelModel):
    product_id: int


class FittingDto(CamelModel):
    id: int
    product_id: int
    product: ProductDto  # 피팅 화면의 상품 정보(이름·가격·구매 링크)
    status: FittingStatus
    original_image_url: str
    result_image_url: str | None
