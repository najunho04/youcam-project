"""personal_color 슬라이스 계약 테스트. 컨텍스트 카드(슬라이스: personal_color)의 백엔드 API 계약만 검증한다.

POST /api/personal-color (multipart: selfie + bodyImage)
- Response 200 PersonalColorDto { season, palette, selfieUrl, bodyImageUrl }
- Error: INVALID_IMAGE(400), VALIDATION_ERROR(422), FACE_NOT_DETECTED(422), EXTERNAL_API_FAILED(502), UNAUTHORIZED(401)
"""
import re

import pytest
from sqlalchemy import select

from common.entity import Fitting, User
from common.enums import FittingStatus, Season
from common.error import ErrorCode
from shared.color import SEASON_PALETTES

PERSONAL_COLOR_PATH = "/api/personal-color"
PERSONAL_COLOR_DTO_FIELDS = {"season", "palette", "selfieUrl", "bodyImageUrl"}
HEX_COLOR_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


def assert_error(response, status_code: int, error_code: ErrorCode) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == error_code.value
    assert isinstance(body["error"]["message"], str)


def load_user(database_session, user_id: int) -> User:
    database_session.expire_all()
    return database_session.scalars(select(User).where(User.id == user_id)).one()


def load_fittings(database_session, user_id: int) -> list[Fitting]:
    database_session.expire_all()
    return list(database_session.scalars(select(Fitting).where(Fitting.user_id == user_id)))


def build_files(sample_image_bytes, selfie_format: str = "JPEG", body_image_format: str = "JPEG") -> dict:
    def to_part(file_name: str, image_format: str) -> tuple[str, bytes, str]:
        extension, content_type = ("png", "image/png") if image_format == "PNG" else ("jpg", "image/jpeg")
        return f"{file_name}.{extension}", sample_image_bytes(image_format=image_format), content_type

    return {"selfie": to_part("face", selfie_format), "bodyImage": to_part("body", body_image_format)}


def create_analyzed_user(create_user, database_session, storage, nickname: str = "analyzed") -> User:
    """이전 분석 결과(season·두 키·저장소 파일)를 가진 사용자."""
    user = create_user(nickname=nickname, season=Season.WINTER_COOL)
    user.selfie_key = f"selfies/{user.id}/previous-selfie.jpg"
    user.body_image_key = f"body-images/{user.id}/previous-body.jpg"
    database_session.commit()
    storage.objects[user.selfie_key] = b"previous-selfie"
    storage.objects[user.body_image_key] = b"previous-body"
    return user


def add_fitting(database_session, user: User, product_id: int) -> None:
    database_session.add(
        Fitting(user_id=user.id, product_id=product_id, status=FittingStatus.DONE, result_key=f"fittings/{user.id}/{product_id}.jpg")
    )
    database_session.commit()


# ---- 정상 ----
@pytest.mark.parametrize(
    ("skin_color_hex", "expected_season"),
    [
        ("#F2D3B1", Season.SPRING_WARM),
        ("#F5D5C8", Season.SUMMER_COOL),
        ("#B07B4F", Season.AUTUMN_WARM),
        ("#8E6A63", Season.WINTER_COOL),
    ],
)
def test_analyze_returns_personal_color_dto_and_stores_season_and_keys(
    client, create_user, auth_headers, database_session, storage, youcam_client, sample_image_bytes,
    skin_color_hex, expected_season,
):
    user = create_user(nickname="fresh")
    youcam_client.skin_color_hex = skin_color_hex

    response = client.post(PERSONAL_COLOR_PATH, files=build_files(sample_image_bytes), headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == PERSONAL_COLOR_DTO_FIELDS
    assert body["season"] == expected_season.value
    assert body["palette"] == SEASON_PALETTES[expected_season]
    assert all(isinstance(color, str) and HEX_COLOR_PATTERN.match(color) for color in body["palette"])
    assert isinstance(body["selfieUrl"], str) and body["selfieUrl"]
    assert isinstance(body["bodyImageUrl"], str) and body["bodyImageUrl"]

    stored_user = load_user(database_session, user.id)
    assert stored_user.season == expected_season
    assert re.fullmatch(rf"selfies/{user.id}/[0-9a-f-]+\.jpg", stored_user.selfie_key)
    assert re.fullmatch(rf"body-images/{user.id}/[0-9a-f-]+\.jpg", stored_user.body_image_key)
    assert set(storage.objects) == {stored_user.selfie_key, stored_user.body_image_key}


def test_analyze_replaces_previous_photos_and_deletes_only_own_fittings(
    client, create_user, create_product, auth_headers, database_session, storage, youcam_client, sample_image_bytes
):
    user = create_analyzed_user(create_user, database_session, storage)
    previous_keys = {user.selfie_key, user.body_image_key}
    other_user = create_analyzed_user(create_user, database_session, storage, nickname="other")
    other_keys = {other_user.selfie_key, other_user.body_image_key}
    first_product, second_product = create_product(), create_product()
    add_fitting(database_session, user, first_product.id)
    add_fitting(database_session, user, second_product.id)
    add_fitting(database_session, other_user, first_product.id)
    youcam_client.skin_color_hex = "#F2D3B1"

    response = client.post(
        PERSONAL_COLOR_PATH,
        files=build_files(sample_image_bytes, selfie_format="PNG", body_image_format="PNG"),
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json()["season"] == Season.SPRING_WARM.value

    stored_user = load_user(database_session, user.id)
    assert stored_user.season == Season.SPRING_WARM
    assert re.fullmatch(rf"selfies/{user.id}/[0-9a-f-]+\.png", stored_user.selfie_key)
    assert re.fullmatch(rf"body-images/{user.id}/[0-9a-f-]+\.png", stored_user.body_image_key)
    assert previous_keys.isdisjoint(storage.objects)
    assert set(storage.objects) == {stored_user.selfie_key, stored_user.body_image_key} | other_keys
    assert load_fittings(database_session, user.id) == []

    # 본인 외 사용자는 변하지 않는다
    stored_other_user = load_user(database_session, other_user.id)
    assert stored_other_user.season == Season.WINTER_COOL
    assert {stored_other_user.selfie_key, stored_other_user.body_image_key} == other_keys
    assert len(load_fittings(database_session, other_user.id)) == 1


# ---- 불변조건 위반 ----
def test_face_not_detected_keeps_user_fittings_and_storage_unchanged(
    client, create_user, create_product, auth_headers, database_session, storage, youcam_client, sample_image_bytes
):
    user = create_analyzed_user(create_user, database_session, storage)
    previous_keys = {user.selfie_key, user.body_image_key}
    add_fitting(database_session, user, create_product().id)
    youcam_client.face_detected = False

    response = client.post(PERSONAL_COLOR_PATH, files=build_files(sample_image_bytes), headers=auth_headers(user))

    assert_error(response, 422, ErrorCode.FACE_NOT_DETECTED)
    stored_user = load_user(database_session, user.id)
    assert stored_user.season == Season.WINTER_COOL
    assert {stored_user.selfie_key, stored_user.body_image_key} == previous_keys
    assert set(storage.objects) == previous_keys
    assert len(load_fittings(database_session, user.id)) == 1


def test_invalid_body_image_returns_invalid_image_and_changes_nothing(
    client, create_user, auth_headers, database_session, storage, sample_image_bytes
):
    user = create_analyzed_user(create_user, database_session, storage)
    previous_keys = {user.selfie_key, user.body_image_key}
    files = build_files(sample_image_bytes)
    files["bodyImage"] = ("body.jpg", b"not an image", "image/jpeg")

    response = client.post(PERSONAL_COLOR_PATH, files=files, headers=auth_headers(user))

    assert_error(response, 400, ErrorCode.INVALID_IMAGE)
    stored_user = load_user(database_session, user.id)
    assert stored_user.season == Season.WINTER_COOL
    assert {stored_user.selfie_key, stored_user.body_image_key} == previous_keys
    assert set(storage.objects) == previous_keys


def test_missing_body_image_returns_validation_error(
    client, create_user, auth_headers, database_session, storage, sample_image_bytes
):
    user = create_user(nickname="fresh")
    files = build_files(sample_image_bytes)
    del files["bodyImage"]

    response = client.post(PERSONAL_COLOR_PATH, files=files, headers=auth_headers(user))

    assert_error(response, 422, ErrorCode.VALIDATION_ERROR)
    stored_user = load_user(database_session, user.id)
    assert stored_user.season is None
    assert stored_user.selfie_key is None
    assert stored_user.body_image_key is None
    assert storage.objects == {}


# ---- 권한 위반 ----
def test_analyze_without_token_returns_unauthorized(client, storage, sample_image_bytes):
    response = client.post(PERSONAL_COLOR_PATH, files=build_files(sample_image_bytes))

    assert_error(response, 401, ErrorCode.UNAUTHORIZED)
    assert storage.objects == {}
