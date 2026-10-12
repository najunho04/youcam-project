"""personal_color service 단위 테스트."""
import io

import pytest
from fastapi import UploadFile
from sqlalchemy import select

from common.entity import Fitting, User
from common.enums import FittingStatus, Season
from common.error import AppError, ErrorCode
from feature.personal_color import service
from shared.color import SEASON_PALETTES


def upload_file(data: bytes, file_name: str = "photo.jpg") -> UploadFile:
    return UploadFile(file=io.BytesIO(data), filename=file_name)


def load_user(database_session, user_id: int) -> User:
    database_session.expire_all()
    return database_session.scalars(select(User).where(User.id == user_id)).one()


def load_fittings(database_session, user_id: int) -> list[Fitting]:
    database_session.expire_all()
    return list(database_session.scalars(select(Fitting).where(Fitting.user_id == user_id)))


def create_analyzed_user(create_user, database_session, storage, nickname: str = "analyzed") -> User:
    user = create_user(nickname=nickname, season=Season.WINTER_COOL)
    user.selfie_key = f"selfies/{user.id}/previous-selfie.jpg"
    user.body_image_key = f"body-images/{user.id}/previous-body.jpg"
    database_session.commit()
    storage.objects[user.selfie_key] = b"previous-selfie"
    storage.objects[user.body_image_key] = b"previous-body"
    return user


def add_fitting(database_session, user_id: int, product_id: int) -> None:
    database_session.add(Fitting(user_id=user_id, product_id=product_id, status=FittingStatus.DONE))
    database_session.commit()


# ---- determine_season ----
@pytest.mark.parametrize(
    ("skin_color_hex", "expected_season"),
    [
        ("#F2D3B1", Season.SPRING_WARM),
        ("#F5D5C8", Season.SUMMER_COOL),
        ("#B07B4F", Season.AUTUMN_WARM),
        ("#8E6A63", Season.WINTER_COOL),
    ],
)
def test_determine_season_matches_card_examples(skin_color_hex, expected_season):
    assert service.determine_season(skin_color_hex) == expected_season


@pytest.mark.parametrize(
    ("lightness", "yellow_blue", "expected_season"),
    [
        (70.0, 18.0, Season.SPRING_WARM),  # 두 기준값 모두 경계 포함 → 밝음·웜
        (70.0, 17.99, Season.SUMMER_COOL),
        (69.99, 18.0, Season.AUTUMN_WARM),
        (69.99, 17.99, Season.WINTER_COOL),
    ],
)
def test_determine_season_boundaries_include_threshold_values(monkeypatch, lightness, yellow_blue, expected_season):
    monkeypatch.setattr(service, "hex_to_lab", lambda hex_color: (lightness, 0.0, yellow_blue))

    assert service.determine_season("#000000") == expected_season


def test_season_thresholds_are_slice_constants():
    assert service.WARM_YELLOW_BLUE_THRESHOLD == 18
    assert service.BRIGHT_LIGHTNESS_THRESHOLD == 70


# ---- analyze_personal_color: 정상 ----
def test_analyze_stores_season_and_keys_and_returns_dto(
    database_session, create_user, storage, youcam_client, sample_image_bytes
):
    user = create_user(nickname="fresh")
    selfie_bytes = sample_image_bytes(color=(220, 180, 150), image_format="JPEG", size=64)
    body_image_bytes = sample_image_bytes(color=(90, 90, 90), image_format="PNG", size=64)
    youcam_client.skin_color_hex = "#B07B4F"

    personal_color_dto = service.analyze_personal_color(
        database_session, user, upload_file(selfie_bytes, "face.jpg"), upload_file(body_image_bytes, "body.png")
    )
    database_session.commit()

    stored_user = load_user(database_session, user.id)
    assert stored_user.season == Season.AUTUMN_WARM
    assert stored_user.selfie_key.startswith(f"selfies/{user.id}/") and stored_user.selfie_key.endswith(".jpg")
    assert stored_user.body_image_key.startswith(f"body-images/{user.id}/") and stored_user.body_image_key.endswith(".png")
    assert storage.objects == {stored_user.selfie_key: selfie_bytes, stored_user.body_image_key: body_image_bytes}
    assert personal_color_dto.season == Season.AUTUMN_WARM
    assert personal_color_dto.palette == SEASON_PALETTES[Season.AUTUMN_WARM]
    assert personal_color_dto.selfie_url == storage.get_url(stored_user.selfie_key)
    assert personal_color_dto.body_image_url == storage.get_url(stored_user.body_image_key)


def test_analyze_sends_only_selfie_url_to_youcam(
    database_session, create_user, storage, youcam_client, sample_image_bytes, monkeypatch
):
    user = create_user(nickname="fresh")
    analyzed_image_urls: list[str] = []
    original_analyze_skin_tone = youcam_client.analyze_skin_tone

    def record_analyze_skin_tone(image_url: str):
        analyzed_image_urls.append(image_url)
        return original_analyze_skin_tone(image_url)

    monkeypatch.setattr(youcam_client, "analyze_skin_tone", record_analyze_skin_tone)

    service.analyze_personal_color(
        database_session, user, upload_file(sample_image_bytes(size=64)), upload_file(sample_image_bytes(size=64))
    )

    assert analyzed_image_urls == [storage.get_url(user.selfie_key)]


def test_analyze_deletes_previous_photos_and_own_fittings_only(
    database_session, create_user, create_product, storage, sample_image_bytes
):
    user = create_analyzed_user(create_user, database_session, storage)
    previous_keys = {user.selfie_key, user.body_image_key}
    other_user = create_analyzed_user(create_user, database_session, storage, nickname="other")
    product = create_product()
    add_fitting(database_session, user.id, product.id)
    add_fitting(database_session, other_user.id, product.id)

    service.analyze_personal_color(
        database_session, user, upload_file(sample_image_bytes(size=64)), upload_file(sample_image_bytes(size=64))
    )
    database_session.commit()

    stored_user = load_user(database_session, user.id)
    assert previous_keys.isdisjoint(storage.objects)
    assert {stored_user.selfie_key, stored_user.body_image_key} <= set(storage.objects)
    assert load_fittings(database_session, user.id) == []
    assert len(load_fittings(database_session, other_user.id)) == 1
    assert other_user.selfie_key in storage.objects and other_user.body_image_key in storage.objects


# ---- analyze_personal_color: 실패 시 불변조건 ----
def test_face_not_detected_removes_new_uploads_and_keeps_previous_state(
    database_session, create_user, create_product, storage, youcam_client, sample_image_bytes
):
    user = create_analyzed_user(create_user, database_session, storage)
    previous_keys = {user.selfie_key, user.body_image_key}
    add_fitting(database_session, user.id, create_product().id)
    youcam_client.face_detected = False

    with pytest.raises(AppError) as error:
        service.analyze_personal_color(
            database_session, user, upload_file(sample_image_bytes(size=64)), upload_file(sample_image_bytes(size=64))
        )
    database_session.rollback()

    assert error.value.error_code == ErrorCode.FACE_NOT_DETECTED
    stored_user = load_user(database_session, user.id)
    assert stored_user.season == Season.WINTER_COOL
    assert {stored_user.selfie_key, stored_user.body_image_key} == previous_keys
    assert set(storage.objects) == previous_keys
    assert len(load_fittings(database_session, user.id)) == 1


def test_external_api_failure_removes_new_uploads(
    database_session, create_user, storage, youcam_client, sample_image_bytes, monkeypatch
):
    user = create_analyzed_user(create_user, database_session, storage)
    previous_keys = {user.selfie_key, user.body_image_key}

    def fail_analyze_skin_tone(image_url: str):
        raise AppError(ErrorCode.EXTERNAL_API_FAILED)

    monkeypatch.setattr(youcam_client, "analyze_skin_tone", fail_analyze_skin_tone)

    with pytest.raises(AppError) as error:
        service.analyze_personal_color(
            database_session, user, upload_file(sample_image_bytes(size=64)), upload_file(sample_image_bytes(size=64))
        )

    assert error.value.error_code == ErrorCode.EXTERNAL_API_FAILED
    assert set(storage.objects) == previous_keys


def test_body_image_upload_failure_removes_already_uploaded_selfie(
    database_session, create_user, storage, sample_image_bytes, monkeypatch
):
    user = create_user(nickname="fresh")
    original_upload = storage.upload

    def fail_body_image_upload(key: str, data: bytes, content_type: str) -> None:
        if key.startswith("body-images/"):
            raise AppError(ErrorCode.EXTERNAL_API_FAILED)
        original_upload(key, data, content_type)

    monkeypatch.setattr(storage, "upload", fail_body_image_upload)

    with pytest.raises(AppError) as error:
        service.analyze_personal_color(
            database_session, user, upload_file(sample_image_bytes(size=64)), upload_file(sample_image_bytes(size=64))
        )

    assert error.value.error_code == ErrorCode.EXTERNAL_API_FAILED
    assert storage.objects == {}


@pytest.mark.parametrize("invalid_field", ["selfie", "body_image"])
def test_invalid_image_uploads_nothing(database_session, create_user, storage, sample_image_bytes, invalid_field):
    user = create_user(nickname="fresh")
    files = {"selfie": upload_file(sample_image_bytes(size=64)), "body_image": upload_file(sample_image_bytes(size=64))}
    files[invalid_field] = upload_file(b"not an image")

    with pytest.raises(AppError) as error:
        service.analyze_personal_color(database_session, user, files["selfie"], files["body_image"])

    assert error.value.error_code == ErrorCode.INVALID_IMAGE
    assert storage.objects == {}
    assert load_user(database_session, user.id).season is None
