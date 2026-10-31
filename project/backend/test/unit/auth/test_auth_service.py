"""auth service 단위 테스트."""
import pytest
from sqlalchemy import select

from common.dto import AuthRequest, FaceColorsDto
from common.entity import User
from common.enums import AgeGroup, Gender, Season, SeasonSubtype
from common.error import AppError, ErrorCode
from feature.auth import repository, service
from shared.color import AVOID_PALETTES, SUBTYPE_PALETTES, judge_personal_color

FACE_COLORS = {"skin": "#C9A79A", "lip": "#A8354F", "eye": "#1E1714", "eyebrow": "#1A1514", "hair": "#141212", "eyeColorName": None, "hairColorName": None}
from shared.security import get_current_user, verify_password


# ---- signup ----
def test_signup_stores_password_hash_and_returns_usable_token(database_session):
    response = service.signup(database_session, AuthRequest(nickname="newbie", password="password1234"))
    database_session.commit()

    stored_user = database_session.scalars(select(User).where(User.nickname == "newbie")).one()
    assert verify_password("password1234", stored_user.password_hash)
    assert response.user.id == stored_user.id
    assert get_current_user(database_session, f"Bearer {response.access_token}").id == stored_user.id


def test_signup_with_taken_nickname_raises_nickname_taken(database_session, create_user):
    create_user(nickname="duplicate")

    with pytest.raises(AppError) as error:
        service.signup(database_session, AuthRequest(nickname="duplicate", password="password1234"))

    assert error.value.error_code == ErrorCode.NICKNAME_TAKEN


def test_signup_converts_unique_violation_to_nickname_taken(database_session, create_user, monkeypatch):
    # 동시 가입: 조회 시점엔 없었지만 insert 시 UNIQUE 위반
    create_user(nickname="racer")
    monkeypatch.setattr(repository, "find_user_by_nickname", lambda database_session, nickname: None)

    with pytest.raises(AppError) as error:
        service.signup(database_session, AuthRequest(nickname="racer", password="password1234"))

    assert error.value.error_code == ErrorCode.NICKNAME_TAKEN


def test_signup_treats_nickname_case_sensitively(database_session, create_user):
    create_user(nickname="Abc")

    response = service.signup(database_session, AuthRequest(nickname="abc", password="password1234"))

    assert response.user.nickname == "abc"


# ---- login ----
def test_login_returns_token_for_matching_credentials(database_session, create_user):
    user = create_user(nickname="member", password="password1234")

    response = service.login(database_session, AuthRequest(nickname="member", password="password1234"))

    assert response.user.id == user.id
    assert get_current_user(database_session, f"Bearer {response.access_token}").id == user.id


@pytest.mark.parametrize(
    ("nickname", "password"),
    [("nobody", "password1234"), ("member", "wrong-password"), ("Member", "password1234")],
)
def test_login_with_wrong_credentials_raises_invalid_credentials(database_session, create_user, nickname, password):
    create_user(nickname="member", password="password1234")

    with pytest.raises(AppError) as error:
        service.login(database_session, AuthRequest(nickname=nickname, password=password))

    assert error.value.error_code == ErrorCode.INVALID_CREDENTIALS


# ---- to_user_dto ----
def test_to_user_dto_fills_personal_color_when_season_selfie_and_body_image_exist(create_user, storage):
    user = create_user(
        nickname="complete",
        age_group=AgeGroup.THIRTIES,
        gender=Gender.MALE,
        season=Season.WINTER_COOL,
        season_subtype=SeasonSubtype.DEEP,
        face_colors=FACE_COLORS,
        selfie_key="selfies/1/face.jpg",
        body_image_key="body-images/1/body.jpg",
    )

    user_dto = service.to_user_dto(user)

    assert user_dto.id == user.id
    assert user_dto.nickname == "complete"
    assert user_dto.age_group == AgeGroup.THIRTIES
    assert user_dto.gender == Gender.MALE
    assert user_dto.personal_color is not None
    assert user_dto.personal_color.season == Season.WINTER_COOL
    assert user_dto.personal_color.subtype == SeasonSubtype.DEEP
    assert user_dto.personal_color.palette == SUBTYPE_PALETTES[(Season.WINTER_COOL, SeasonSubtype.DEEP)]
    assert user_dto.personal_color.avoid_palette == AVOID_PALETTES[Season.WINTER_COOL]
    assert user_dto.personal_color.analysis == judge_personal_color(FaceColorsDto.model_validate(FACE_COLORS)).analysis
    assert user_dto.personal_color.selfie_url == storage.get_url("selfies/1/face.jpg")
    assert user_dto.personal_color.body_image_url == storage.get_url("body-images/1/body.jpg")


@pytest.mark.parametrize(
    "missing_column",
    ["season", "season_subtype", "face_colors", "selfie_key", "body_image_key"],
)
def test_to_user_dto_leaves_personal_color_null_when_any_column_missing(create_user, missing_column):
    columns = dict(
        season=Season.SPRING_WARM, season_subtype=SeasonSubtype.TRUE, face_colors=FACE_COLORS,
        selfie_key="selfies/1/face.jpg", body_image_key="body-images/1/body.jpg",
    )
    columns[missing_column] = None
    user = create_user(nickname="partial", **columns)

    assert service.to_user_dto(user).personal_color is None


def test_to_user_dto_does_not_expose_password_hash(create_user):
    user = create_user(nickname="member")

    dumped = service.to_user_dto(user).model_dump(by_alias=True)

    assert "passwordHash" not in dumped and "password_hash" not in dumped
    assert user.password_hash not in str(dumped)
