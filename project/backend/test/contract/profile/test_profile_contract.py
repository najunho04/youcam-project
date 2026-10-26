"""profile 슬라이스 계약 테스트. 컨텍스트 카드(슬라이스: profile)의 백엔드 API 계약만 검증한다.

PUT /api/users/me/profile
- Request ProfileUpdateRequest { ageGroup, gender } 둘 다 필수
- Response 200 UserDto
- Error: UNAUTHORIZED(401), VALIDATION_ERROR(422)
"""
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from common.entity import Swipe, User
from common.dto import FaceColorsDto
from common.enums import AgeGroup, Gender, Season, SeasonSubtype
from common.error import ErrorCode
from shared.color import AVOID_PALETTES, SUBTYPE_PALETTES, judge_personal_color
from shared.config import get_settings

PROFILE_PATH = "/api/users/me/profile"
USER_DTO_FIELDS = {"id", "nickname", "ageGroup", "gender", "personalColor"}
PERSONAL_COLOR_DTO_FIELDS = {"season", "subtype", "palette", "avoidPalette", "analysis", "selfieUrl", "bodyImageUrl"}
FACE_COLORS = {
    "skin": "#E3C0A6", "lip": "#C8646E", "eye": "#3A2A22", "eyebrow": "#3B2E28", "hair": "#231C19",
    "eyeColorName": "Brown", "hairColorName": "Black",
}


def assert_error(response, status_code: int, error_code: ErrorCode) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == error_code.value
    assert isinstance(body["error"]["message"], str)


def load_user(database_session, user_id: int) -> User:
    database_session.expire_all()
    return database_session.scalars(select(User).where(User.id == user_id)).one()


def snapshot_user_columns(user: User) -> dict:
    return {column.name: getattr(user, column.key) for column in User.__table__.columns}


# ---- 정상 ----
def test_update_profile_returns_user_dto_and_stores_age_group_and_gender(
    client, create_user, auth_headers, database_session
):
    user = create_user(nickname="fresh")

    response = client.put(
        PROFILE_PATH,
        json={"ageGroup": AgeGroup.TWENTIES.value, "gender": Gender.FEMALE.value},
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == USER_DTO_FIELDS
    assert isinstance(body["id"], int)
    assert body["id"] == user.id
    assert body["nickname"] == "fresh"
    assert body["ageGroup"] == AgeGroup.TWENTIES.value
    assert body["gender"] == Gender.FEMALE.value
    assert body["personalColor"] is None

    stored_user = load_user(database_session, user.id)
    assert stored_user.age_group == AgeGroup.TWENTIES
    assert stored_user.gender == Gender.FEMALE


def test_update_profile_overwrites_only_age_group_and_gender_and_fills_personal_color(
    client, create_user, auth_headers, database_session, storage
):
    user = create_user(
        nickname="complete",
        age_group=AgeGroup.TWENTIES,
        gender=Gender.FEMALE,
        season=Season.WINTER_COOL,
        season_subtype=SeasonSubtype.BRIGHT,
        face_colors=FACE_COLORS,
        selfie_key="selfies/1/face.jpg",
        body_image_key="body-images/1/body.jpg",
    )
    before = snapshot_user_columns(load_user(database_session, user.id))

    response = client.put(
        PROFILE_PATH,
        json={"ageGroup": AgeGroup.THIRTIES.value, "gender": Gender.MALE.value},
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == USER_DTO_FIELDS
    assert body["ageGroup"] == AgeGroup.THIRTIES.value
    assert body["gender"] == Gender.MALE.value
    personal_color = body["personalColor"]
    assert set(personal_color) == PERSONAL_COLOR_DTO_FIELDS
    assert personal_color["season"] == Season.WINTER_COOL.value
    assert personal_color["subtype"] == SeasonSubtype.BRIGHT.value
    assert personal_color["palette"] == SUBTYPE_PALETTES[(Season.WINTER_COOL, SeasonSubtype.BRIGHT)]
    assert personal_color["avoidPalette"] == AVOID_PALETTES[Season.WINTER_COOL]
    # analysis 는 저장된 face_colors 로 다시 계산한 판정 근거
    expected_analysis = judge_personal_color(FaceColorsDto.model_validate(FACE_COLORS)).analysis
    assert personal_color["analysis"] == expected_analysis.model_dump(by_alias=True)
    assert personal_color["selfieUrl"] == storage.get_url("selfies/1/face.jpg")
    assert personal_color["bodyImageUrl"] == storage.get_url("body-images/1/body.jpg")

    after = snapshot_user_columns(load_user(database_session, user.id))
    assert after["age_group"] == AgeGroup.THIRTIES
    assert after["gender"] == Gender.MALE
    unchanged_columns = {name for name in before if name not in {"age_group", "gender"}}
    assert {name: after[name] for name in unchanged_columns} == {name: before[name] for name in unchanged_columns}


def test_update_profile_is_idempotent(client, create_user, auth_headers, database_session):
    user = create_user(nickname="repeater")
    request_body = {"ageGroup": AgeGroup.FORTIES_PLUS.value, "gender": Gender.MALE.value}

    first_response = client.put(PROFILE_PATH, json=request_body, headers=auth_headers(user))
    first_snapshot = snapshot_user_columns(load_user(database_session, user.id))
    second_response = client.put(PROFILE_PATH, json=request_body, headers=auth_headers(user))
    second_snapshot = snapshot_user_columns(load_user(database_session, user.id))

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()
    assert first_snapshot == second_snapshot


def test_update_profile_keeps_existing_swipes(client, create_user, create_pin, auth_headers, database_session):
    user = create_user(nickname="swiper", age_group=AgeGroup.TWENTIES, gender=Gender.FEMALE)
    pin = create_pin(age_group=AgeGroup.TWENTIES, gender=Gender.FEMALE)
    database_session.add(Swipe(user_id=user.id, pin_id=pin.id, liked=True))
    database_session.commit()

    response = client.put(
        PROFILE_PATH,
        json={"ageGroup": AgeGroup.THIRTIES.value, "gender": Gender.MALE.value},
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    database_session.expire_all()
    swipes = database_session.scalars(select(Swipe).where(Swipe.user_id == user.id)).all()
    assert [(swipe.pin_id, swipe.liked) for swipe in swipes] == [(pin.id, True)]


# ---- 권한 ----
def test_update_profile_changes_only_token_owner(client, create_user, auth_headers, database_session):
    owner = create_user(nickname="owner")
    other_user = create_user(nickname="other", age_group=AgeGroup.LATE_TEENS, gender=Gender.FEMALE)
    other_before = snapshot_user_columns(load_user(database_session, other_user.id))

    response = client.put(
        PROFILE_PATH,
        json={"ageGroup": AgeGroup.THIRTIES.value, "gender": Gender.MALE.value},
        headers=auth_headers(owner),
    )

    assert response.status_code == 200
    assert response.json()["id"] == owner.id
    assert snapshot_user_columns(load_user(database_session, other_user.id)) == other_before


def _token_with(user_id: int, secret: str, expires_at: datetime) -> str:
    return jwt.encode({"sub": str(user_id), "exp": expires_at}, secret, algorithm="HS256")


@pytest.mark.parametrize("token_kind", ["missing", "expired", "forged"])
def test_update_profile_without_valid_token_returns_unauthorized(client, create_user, database_session, token_kind):
    user = create_user(nickname="member")
    before = snapshot_user_columns(load_user(database_session, user.id))
    secret = get_settings().jwt_secret
    headers = {
        "missing": {},
        "expired": {"Authorization": f"Bearer {_token_with(user.id, secret, datetime.now(UTC) - timedelta(minutes=1))}"},
        "forged": {"Authorization": f"Bearer {_token_with(user.id, 'forged-secret-key-0123456789abcdef', datetime.now(UTC) + timedelta(days=1))}"},
    }[token_kind]

    response = client.put(
        PROFILE_PATH,
        json={"ageGroup": AgeGroup.TWENTIES.value, "gender": Gender.FEMALE.value},
        headers=headers,
    )

    assert_error(response, 401, ErrorCode.UNAUTHORIZED)
    assert snapshot_user_columns(load_user(database_session, user.id)) == before


# ---- 검증 ----
@pytest.mark.parametrize(
    "request_body",
    [
        {"ageGroup": "FIFTIES", "gender": Gender.FEMALE.value},  # enum 밖 나이대
        {"ageGroup": AgeGroup.TWENTIES.value, "gender": "OTHER"},  # enum 밖 성별
        {"gender": Gender.FEMALE.value},  # ageGroup 누락
        {"ageGroup": AgeGroup.TWENTIES.value},  # gender 누락
        {},  # 둘 다 누락
    ],
)
def test_update_profile_with_invalid_body_returns_validation_error(
    client, create_user, auth_headers, database_session, request_body
):
    user = create_user(nickname="member", age_group=AgeGroup.LATE_TEENS, gender=Gender.MALE)
    before = snapshot_user_columns(load_user(database_session, user.id))

    response = client.put(PROFILE_PATH, json=request_body, headers=auth_headers(user))

    assert_error(response, 422, ErrorCode.VALIDATION_ERROR)
    assert snapshot_user_columns(load_user(database_session, user.id)) == before
