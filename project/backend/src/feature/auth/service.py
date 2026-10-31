"""auth 슬라이스 비즈니스 로직. 실패는 AppError 로만 알린다."""
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from common.dto import FaceColorsDto, AuthRequest, AuthResponse, PersonalColorDto, UserDto
from common.entity import User
from common.error import AppError, ErrorCode
from feature.auth import repository
from shared.color import AVOID_PALETTES, SUBTYPE_PALETTES, judge_personal_color
from shared.security import create_access_token, hash_password, verify_password
from shared.storage import get_storage


def signup(database_session: Session, request: AuthRequest) -> AuthResponse:
    if repository.find_user_by_nickname(database_session, request.nickname) is not None:
        raise AppError(ErrorCode.NICKNAME_TAKEN)
    try:
        user = repository.add_user(database_session, request.nickname, hash_password(request.password))
    except IntegrityError as error:
        raise AppError(ErrorCode.NICKNAME_TAKEN) from error
    return _to_auth_response(user)


def login(database_session: Session, request: AuthRequest) -> AuthResponse:
    user = repository.find_user_by_nickname(database_session, request.nickname)
    if user is None or not verify_password(request.password, user.password_hash):
        raise AppError(ErrorCode.INVALID_CREDENTIALS)
    return _to_auth_response(user)


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


def _to_auth_response(user: User) -> AuthResponse:
    return AuthResponse(access_token=create_access_token(user.id), user=to_user_dto(user))
