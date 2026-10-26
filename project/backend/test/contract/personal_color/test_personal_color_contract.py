"""personal_color 슬라이스 계약 테스트. 컨텍스트 카드(슬라이스: personal_color)의 백엔드 API 계약만 검증한다.

POST /api/personal-color (multipart: selfie + bodyImage)
- Response 200 PersonalColorDto { season, subtype, palette, avoidPalette, analysis, selfieUrl, bodyImageUrl }
  analysis = { faceColors, warmth, depth, clarity, skinLightness, contrast } — YouCam 얼굴 색 5개 전부로 12유형 판정
- Error: INVALID_IMAGE(400), VALIDATION_ERROR(422), FACE_NOT_DETECTED(422), EXTERNAL_API_FAILED(502), UNAUTHORIZED(401)
"""
import re

import pytest
from sqlalchemy import select

from common.dto import FaceColorsDto
from common.entity import Fitting, User
from common.enums import FittingStatus, Season, SeasonSubtype
from common.error import ErrorCode
from shared.color import AVOID_PALETTES, SUBTYPE_PALETTES

PERSONAL_COLOR_PATH = "/api/personal-color"
PERSONAL_COLOR_DTO_FIELDS = {"season", "subtype", "palette", "avoidPalette", "analysis", "selfieUrl", "bodyImageUrl"}
ANALYSIS_FIELDS = {"faceColors", "warmth", "depth", "clarity", "skinLightness", "contrast"}
FACE_COLORS_FIELDS = {"skin", "lip", "eye", "eyebrow", "hair", "eyeColorName", "hairColorName"}
PREVIOUS_FACE_COLORS = {
    "skin": "#C9A79A", "lip": "#A8354F", "eye": "#1E1714", "eyebrow": "#1A1514", "hair": "#141212",
    "eyeColorName": None, "hairColorName": None,
}


def face_colors_of(skin: str, lip: str, eye: str, eyebrow: str, hair: str) -> FaceColorsDto:
    return FaceColorsDto(
        skin=skin, lip=lip, eye=eye, eyebrow=eyebrow, hair=hair, eye_color_name="Brown", hair_color_name="Black"
    )
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
    """이전 분석 결과(season·season_subtype·face_colors·두 키·저장소 파일)를 가진 사용자."""
    user = create_user(
        nickname=nickname, season=Season.WINTER_COOL, season_subtype=SeasonSubtype.TRUE, face_colors=PREVIOUS_FACE_COLORS
    )
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
# 카드 "판정 규칙" 예시: (skin, lip, eye, eyebrow, hair) → (season, subtype, (warmth, depth, clarity))
@pytest.mark.parametrize(
    ("colors", "expected_season", "expected_subtype", "expected_axes"),
    [
        (("#F6DCC2", "#E8907A", "#8A6A4A", "#A08060", "#B08A60"), Season.SPRING_WARM, SeasonSubtype.LIGHT, (1.26, -1.34, -0.54)),
        (("#F2D3B1", "#E07A5F", "#6B4A2B", "#7A5A3A", "#8B6A45"), Season.SPRING_WARM, SeasonSubtype.TRUE, (1.39, -0.83, 0.33)),
        (("#D8C0B8", "#B88890", "#5A5048", "#6A605A", "#5A524C"), Season.SUMMER_COOL, SeasonSubtype.SOFT, (-1.17, -0.64, -2.03)),
        (("#B07B4F", "#B5553A", "#3B2414", "#3A2618", "#2E1C10"), Season.AUTUMN_WARM, SeasonSubtype.DEEP, (0.68, 0.79, 2.06)),
        (("#E3C0A6", "#C8646E", "#3A2A22", "#3B2E28", "#231C19"), Season.AUTUMN_WARM, SeasonSubtype.TRUE, (0.32, 0.13, -0.11)),
        (("#C9A79A", "#A8354F", "#1E1714", "#1A1514", "#141212"), Season.WINTER_COOL, SeasonSubtype.TRUE, (-0.92, 0.57, -0.38)),
    ],
)
def test_analyze_returns_personal_color_dto_and_stores_judgment_and_keys(
    client, create_user, auth_headers, database_session, storage, youcam_client, sample_image_bytes,
    colors, expected_season, expected_subtype, expected_axes,
):
    user = create_user(nickname="fresh")
    youcam_client.face_colors = face_colors_of(*colors)

    response = client.post(PERSONAL_COLOR_PATH, files=build_files(sample_image_bytes), headers=auth_headers(user))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == PERSONAL_COLOR_DTO_FIELDS
    assert body["season"] == expected_season.value
    assert body["subtype"] == expected_subtype.value
    assert body["palette"] == SUBTYPE_PALETTES[(expected_season, expected_subtype)]
    assert body["avoidPalette"] == AVOID_PALETTES[expected_season]
    assert all(HEX_COLOR_PATTERN.match(color) for color in body["palette"] + body["avoidPalette"])
    assert isinstance(body["selfieUrl"], str) and body["selfieUrl"]
    assert isinstance(body["bodyImageUrl"], str) and body["bodyImageUrl"]

    analysis = body["analysis"]
    assert set(analysis) == ANALYSIS_FIELDS
    assert set(analysis["faceColors"]) == FACE_COLORS_FIELDS
    assert [analysis["faceColors"][key] for key in ("skin", "lip", "eye", "eyebrow", "hair")] == list(colors)
    assert (analysis["faceColors"]["eyeColorName"], analysis["faceColors"]["hairColorName"]) == ("Brown", "Black")
    assert (analysis["warmth"], analysis["depth"], analysis["clarity"]) == expected_axes
    for key in ("skinLightness", "contrast"):
        assert isinstance(analysis[key], float | int) and round(analysis[key], 2) == analysis[key]

    stored_user = load_user(database_session, user.id)
    assert stored_user.season == expected_season
    assert stored_user.season_subtype == expected_subtype
    assert stored_user.face_colors == analysis["faceColors"]
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
    youcam_client.face_colors = face_colors_of("#F2D3B1", "#E07A5F", "#6B4A2B", "#7A5A3A", "#8B6A45")

    response = client.post(
        PERSONAL_COLOR_PATH,
        files=build_files(sample_image_bytes, selfie_format="PNG", body_image_format="PNG"),
        headers=auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json()["season"] == Season.SPRING_WARM.value

    stored_user = load_user(database_session, user.id)
    assert stored_user.season == Season.SPRING_WARM
    assert stored_user.season_subtype == SeasonSubtype.TRUE
    assert stored_user.face_colors["skin"] == "#F2D3B1"
    assert re.fullmatch(rf"selfies/{user.id}/[0-9a-f-]+\.png", stored_user.selfie_key)
    assert re.fullmatch(rf"body-images/{user.id}/[0-9a-f-]+\.png", stored_user.body_image_key)
    assert previous_keys.isdisjoint(storage.objects)
    assert set(storage.objects) == {stored_user.selfie_key, stored_user.body_image_key} | other_keys
    assert load_fittings(database_session, user.id) == []

    # 본인 외 사용자는 변하지 않는다
    stored_other_user = load_user(database_session, other_user.id)
    assert stored_other_user.season == Season.WINTER_COOL
    assert stored_other_user.face_colors == PREVIOUS_FACE_COLORS
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
    assert stored_user.season_subtype == SeasonSubtype.TRUE
    assert stored_user.face_colors == PREVIOUS_FACE_COLORS
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
