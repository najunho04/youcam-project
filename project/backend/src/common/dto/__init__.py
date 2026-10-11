"""요청·응답 DTO. JSON 은 camelCase (alias). 원본 명세는 project-all-docs/api.md. 프론트 타입은 front/src/common/type 과 1:1."""
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from common.enums import AgeGroup, FittingStatus, Gender, Season, Style
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


class PersonalColorDto(CamelModel):
    season: Season
    palette: list[str]  # hex, 예: "#C8A27A"
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
    product_id: int
    image_url: str
    style: Style


class SwipeCardsResponse(CamelModel):
    cards: list[SwipeCardDto]


class SwipeAnswer(CamelModel):
    product_id: int
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
    price: int
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
    palette: list[str]
    is_fallback: bool
    items: list[RecommendationItem]


# ---- fitting ----
class FittingCreateRequest(CamelModel):
    product_id: int


class FittingDto(CamelModel):
    id: int
    product_id: int
    status: FittingStatus
    original_image_url: str
    result_image_url: str | None
