"""auth 슬라이스 계약 테스트. 컨텍스트 카드(슬라이스: auth)의 백엔드 API 계약만 검증한다.

사용자 확정 사항 (카드 명세 보완, 2026-10-11):
- login 요청의 길이 위반은 VALIDATION_ERROR(422) (signup 과 동일한 AuthRequest 검증)
- 닉네임은 trim 하지 않고 대소문자를 구분한다 ("Abc" 와 "abc" 는 다른 닉네임)
- 토큰은 유효하나 해당 사용자가 DB 에 없으면 UNAUTHORIZED(401)
- auth 는 age_group·gender·season 등을 쓰지 않으므로 가입 직후 UserDto 의 ageGroup·gender·personalColor 는 null
"""
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from common.entity import User
from common.dto import FaceColorsDto
from common.enums import AgeGroup, Gender, Season, SeasonSubtype
from common.error import ErrorCode
from shared.color import AVOID_PALETTES, SUBTYPE_PALETTES, judge_personal_color
from shared.config import get_settings
from shared.security import verify_password

USER_DTO_FIELDS = {"id", "nickname", "ageGroup", "gender", "personalColor"}
PERSONAL_COLOR_DTO_FIELDS = {"season", "subtype", "palette", "avoidPalette", "analysis", "selfieUrl", "bodyImageUrl"}
FACE_COLORS = {
    "skin": "#E3C0A6", "lip": "#C8646E", "eye": "#3A2A22", "eyebrow": "#3B2E28", "hair": "#231C19",
    "eyeColorName": "Brown", "hairColorName": "Black",
}
AUTH_RESPONSE_FIELDS = {"accessToken", "user"}


def assert_error(response, status_code: int, error_code: ErrorCode) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == error_code.value
    assert isinstance(body["error"]["message"], str)


def assert_user_dto_without_progress(user_json: dict, nickname: str) -> None:
    assert set(user_json) == USER_DTO_FIELDS
    assert isinstance(user_json["id"], int)
    assert user_json["nickname"] == nickname
    assert user_json["ageGroup"] is None
    assert user_json["gender"] is None
    assert user_json["personalColor"] is None


def assert_auth_response(response, nickname: str) -> dict:
    assert response.status_code == 200
    body = response.json()
    assert set(body) == AUTH_RESPONSE_FIELDS
    assert isinstance(body["accessToken"], str) and body["accessToken"]
    assert_user_dto_without_progress(body["user"], nickname)
    return body


# ---- POST /api/auth/signup ----
def test_signup_returns_auth_response_and_stores_only_password_hash(client, database_session):
    password = "secret-password-1234"

    response = client.post("/api/auth/signup", json={"nickname": "newbie", "password": password})

    body = assert_auth_response(response, "newbie")
    assert password not in response.text
    stored_user = database_session.scalars(select(User).where(User.nickname == "newbie")).one()
    assert stored_user.id == body["user"]["id"]
    assert stored_user.password_hash != password
    assert verify_password(password, stored_user.password_hash)
    # 발급된 토큰으로 인증 가능해야 한다
    me_response = client.get("/api/users/me", headers={"Authorization": f"Bearer {body['accessToken']}"})
    assert me_response.status_code == 200
    assert me_response.json()["id"] == stored_user.id


def test_signup_with_taken_nickname_returns_nickname_taken(client, create_user):
    create_user(nickname="duplicate")

    response = client.post("/api/auth/signup", json={"nickname": "duplicate", "password": "password1234"})

    assert_error(response, 409, ErrorCode.NICKNAME_TAKEN)


@pytest.mark.parametrize(
    ("nickname", "password"),
    [
        ("a", "password1234"),  # 닉네임 1자 (최소 2)
        ("a" * 21, "password1234"),  # 닉네임 21자 (최대 20)
        ("validname", "abc"),  # 비밀번호 3자 (최소 4)
        ("validname", "a" * 73),  # 비밀번호 73자 (최대 72)
    ],
)
def test_signup_with_length_violation_returns_validation_error(client, database_session, nickname, password):
    response = client.post("/api/auth/signup", json={"nickname": nickname, "password": password})

    assert_error(response, 422, ErrorCode.VALIDATION_ERROR)
    assert database_session.scalars(select(User)).first() is None


# ---- POST /api/auth/login ----
def test_login_returns_auth_response(client, create_user):
    create_user(nickname="member", password="password1234")

    response = client.post("/api/auth/login", json={"nickname": "member", "password": "password1234"})

    body = assert_auth_response(response, "member")
    assert "password1234" not in response.text
    me_response = client.get("/api/users/me", headers={"Authorization": f"Bearer {body['accessToken']}"})
    assert me_response.status_code == 200


def test_login_does_not_distinguish_unknown_nickname_from_wrong_password(client, create_user):
    create_user(nickname="member", password="password1234")

    unknown_nickname_response = client.post("/api/auth/login", json={"nickname": "nobody", "password": "password1234"})
    wrong_password_response = client.post("/api/auth/login", json={"nickname": "member", "password": "wrong-password"})

    assert_error(unknown_nickname_response, 401, ErrorCode.INVALID_CREDENTIALS)
    assert_error(wrong_password_response, 401, ErrorCode.INVALID_CREDENTIALS)
    assert unknown_nickname_response.json() == wrong_password_response.json()


# ---- GET /api/users/me ----
def test_me_fills_personal_color_only_when_season_subtype_face_colors_selfie_and_body_image_all_exist(
    client, create_user, auth_headers, storage
):
    complete_user = create_user(
        nickname="complete",
        age_group=AgeGroup.TWENTIES,
        gender=Gender.FEMALE,
        season=Season.AUTUMN_WARM,
        season_subtype=SeasonSubtype.DEEP,
        face_colors=FACE_COLORS,
        selfie_key="selfies/1/face.jpg",
        body_image_key="body-images/1/body.jpg",
    )
    partial_user = create_user(
        nickname="partial", season=Season.AUTUMN_WARM, season_subtype=SeasonSubtype.TRUE, face_colors=FACE_COLORS,
        selfie_key="selfies/2/face.jpg",
    )
    # 시즌·사진은 있지만 face_colors 가 없는 사용자 (판정 근거를 만들 수 없음)
    no_face_colors_user = create_user(
        nickname="nocolors", season=Season.AUTUMN_WARM, season_subtype=SeasonSubtype.TRUE,
        selfie_key="selfies/3/face.jpg", body_image_key="body-images/3/body.jpg",
    )

    complete_response = client.get("/api/users/me", headers=auth_headers(complete_user))
    partial_response = client.get("/api/users/me", headers=auth_headers(partial_user))
    no_face_colors_response = client.get("/api/users/me", headers=auth_headers(no_face_colors_user))

    assert complete_response.status_code == 200
    complete_body = complete_response.json()
    assert set(complete_body) == USER_DTO_FIELDS
    assert complete_body["id"] == complete_user.id
    assert complete_body["nickname"] == "complete"
    assert complete_body["ageGroup"] == AgeGroup.TWENTIES.value
    assert complete_body["gender"] == Gender.FEMALE.value
    personal_color = complete_body["personalColor"]
    assert set(personal_color) == PERSONAL_COLOR_DTO_FIELDS
    assert personal_color["season"] == Season.AUTUMN_WARM.value
    assert personal_color["subtype"] == SeasonSubtype.DEEP.value
    assert personal_color["palette"] == SUBTYPE_PALETTES[(Season.AUTUMN_WARM, SeasonSubtype.DEEP)]
    assert personal_color["avoidPalette"] == AVOID_PALETTES[Season.AUTUMN_WARM]
    # analysis 는 저장된 face_colors 로 다시 계산한 판정 근거
    expected_analysis = judge_personal_color(FaceColorsDto.model_validate(FACE_COLORS)).analysis
    assert personal_color["analysis"] == expected_analysis.model_dump(by_alias=True)
    assert personal_color["selfieUrl"] == storage.get_url("selfies/1/face.jpg")
    assert personal_color["bodyImageUrl"] == storage.get_url("body-images/1/body.jpg")

    assert partial_response.status_code == 200
    assert partial_response.json()["personalColor"] is None
    assert no_face_colors_response.status_code == 200
    assert no_face_colors_response.json()["personalColor"] is None


def _token_with(user_id: int, secret: str, expires_at: datetime) -> str:
    return jwt.encode({"sub": str(user_id), "exp": expires_at}, secret, algorithm="HS256")


@pytest.mark.parametrize("token_kind", ["missing", "expired", "forged"])
def test_me_without_valid_token_returns_unauthorized(client, create_user, token_kind):
    user = create_user(nickname="member")
    secret = get_settings().jwt_secret
    headers = {
        "missing": {},
        "expired": {"Authorization": f"Bearer {_token_with(user.id, secret, datetime.now(UTC) - timedelta(minutes=1))}"},
        "forged": {"Authorization": f"Bearer {_token_with(user.id, 'forged-secret-key-0123456789abcdef', datetime.now(UTC) + timedelta(days=1))}"},
    }[token_kind]

    response = client.get("/api/users/me", headers=headers)

    assert_error(response, 401, ErrorCode.UNAUTHORIZED)
