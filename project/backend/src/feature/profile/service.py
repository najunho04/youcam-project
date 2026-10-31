"""profile 슬라이스 비즈니스 로직. 실패는 AppError 로만 알린다."""
from sqlalchemy.orm import Session

from common.dto import FaceColorsDto, PersonalColorDto, ProfileUpdateRequest, UserDto
from common.entity import User
from feature.profile import repository
from shared.color import AVOID_PALETTES, SUBTYPE_PALETTES, judge_personal_color
from shared.storage import get_storage


def update_profile(database_session: Session, user: User, request: ProfileUpdateRequest) -> UserDto:
    updated_user = repository.update_age_group_and_gender(database_session, user, request.age_group, request.gender)
    return to_user_dto(updated_user)


def to_user_dto(user: User) -> UserDto:
    return UserDto(
        id=user.id,
        nickname=user.nickname,
        age_group=user.age_group,
        gender=user.gender,
        personal_color=_to_personal_color_dto(user),
    )


def _to_personal_color_dto(user: User) -> PersonalColorDto | None:
    """season·season_subtype·face_colors·두 사진 키가 모두 있을 때만. 판정 근거는 저장된 face_colors 로 다시 계산한다."""
    if (
        user.season is None
        or user.season_subtype is None
        or user.face_colors is None
        or user.selfie_key is None
        or user.body_image_key is None
    ):
        return None
    storage = get_storage()
    return PersonalColorDto(
        season=user.season,
        subtype=user.season_subtype,
        palette=SUBTYPE_PALETTES[(user.season, user.season_subtype)],
        avoid_palette=AVOID_PALETTES[user.season],
        analysis=judge_personal_color(FaceColorsDto.model_validate(user.face_colors)).analysis,
        selfie_url=storage.get_url(user.selfie_key),
        body_image_url=storage.get_url(user.body_image_key),
    )
