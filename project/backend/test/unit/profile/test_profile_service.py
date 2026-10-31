"""profile service 단위 테스트."""
import pytest
from sqlalchemy import select

from common.dto import FaceColorsDto, ProfileUpdateRequest
from common.entity import User
from common.enums import AgeGroup, Gender, Season, SeasonSubtype
from feature.profile import service
from shared.color import AVOID_PALETTES, SUBTYPE_PALETTES, judge_personal_color

FACE_COLORS = {"skin": "#C9A79A", "lip": "#A8354F", "eye": "#1E1714", "eyebrow": "#1A1514", "hair": "#141212", "eyeColorName": None, "hairColorName": None}


def load_user(database_session, user_id: int) -> User:
    database_session.expire_all()
    return database_session.scalars(select(User).where(User.id == user_id)).one()


# ---- update_profile ----
def test_update_profile_stores_age_group_and_gender(database_session, create_user):
    user = create_user(nickname="fresh")

    user_dto = service.update_profile(
        database_session, user, ProfileUpdateRequest(age_group=AgeGroup.TWENTIES, gender=Gender.FEMALE)
    )
    database_session.commit()

    stored_user = load_user(database_session, user.id)
    assert stored_user.age_group == AgeGroup.TWENTIES
    assert stored_user.gender == Gender.FEMALE
    assert user_dto.id == user.id
    assert user_dto.age_group == AgeGroup.TWENTIES
    assert user_dto.gender == Gender.FEMALE


def test_update_profile_does_not_touch_other_columns(database_session, create_user):
    user = create_user(
        nickname="complete",
        age_group=AgeGroup.LATE_TEENS,
        gender=Gender.MALE,
        season=Season.SUMMER_COOL,
        selfie_key="selfies/1/face.jpg",
        body_image_key="body-images/1/body.jpg",
    )
    password_hash = user.password_hash

    service.update_profile(
        database_session, user, ProfileUpdateRequest(age_group=AgeGroup.FORTIES_PLUS, gender=Gender.FEMALE)
    )
    database_session.commit()

    stored_user = load_user(database_session, user.id)
    assert stored_user.nickname == "complete"
    assert stored_user.password_hash == password_hash
    assert stored_user.season == Season.SUMMER_COOL
    assert stored_user.selfie_key == "selfies/1/face.jpg"
    assert stored_user.body_image_key == "body-images/1/body.jpg"


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

    assert user_dto.nickname == "complete"
    assert user_dto.personal_color is not None
    assert user_dto.personal_color.season == Season.WINTER_COOL
    assert user_dto.personal_color.subtype == SeasonSubtype.DEEP
    assert user_dto.personal_color.palette == SUBTYPE_PALETTES[(Season.WINTER_COOL, SeasonSubtype.DEEP)]
    assert user_dto.personal_color.avoid_palette == AVOID_PALETTES[Season.WINTER_COOL]
    assert user_dto.personal_color.analysis == judge_personal_color(FaceColorsDto.model_validate(FACE_COLORS)).analysis
    assert user_dto.personal_color.selfie_url == storage.get_url("selfies/1/face.jpg")
    assert user_dto.personal_color.body_image_url == storage.get_url("body-images/1/body.jpg")


@pytest.mark.parametrize("missing_column", ["season", "season_subtype", "face_colors", "selfie_key", "body_image_key"])
def test_to_user_dto_leaves_personal_color_null_when_any_column_missing(create_user, missing_column):
    columns = dict(
        season=Season.SPRING_WARM, season_subtype=SeasonSubtype.TRUE, face_colors=FACE_COLORS,
        selfie_key="selfies/1/face.jpg", body_image_key="body-images/1/body.jpg",
    )
    columns[missing_column] = None
    user = create_user(nickname="partial", **columns)

    assert service.to_user_dto(user).personal_color is None
