"""wardrobe 슬라이스 계약 테스트. 컨텍스트 카드(슬라이스: wardrobe)의 백엔드 API 계약만 검증한다.

POST /api/wardrobe-photos (multipart/form-data, 필드 images 1~4개, 각각 jpg/png 10MB 이하)
- Response 200 WardrobePhotosResponse { photos: WardrobePhotoDto[] } — 업로드 후 사용자 전체 사진, id 오름차순
- Error: INVALID_IMAGE(400), WARDROBE_LIMIT_EXCEEDED(409), VALIDATION_ERROR(422), UNAUTHORIZED(401)
- 불변조건: 사용자당 4장 이하, embedding 512차원, 거부된 요청은 행을 남기지 않음
"""
import re
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from sqlalchemy import select

from common.entity import EMBEDDING_DIMENSION, WARDROBE_PHOTO_LIMIT, WardrobePhoto
from common.error import ErrorCode
from shared.config import get_settings

WARDROBE_PHOTOS_PATH = "/api/wardrobe-photos"
WARDROBE_PHOTOS_RESPONSE_FIELDS = {"photos"}
WARDROBE_PHOTO_DTO_FIELDS = {"id", "imageUrl"}
IMAGE_EXTENSION_BY_FORMAT = {"JPEG": "jpg", "PNG": "png"}
IMAGE_CONTENT_TYPE_BY_FORMAT = {"JPEG": "image/jpeg", "PNG": "image/png"}


def assert_error(response, status_code: int, error_code: ErrorCode) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == error_code.value
    assert isinstance(body["error"]["message"], str)


def image_file(data: bytes, image_format: str = "JPEG", file_name: str | None = None) -> tuple:
    extension = IMAGE_EXTENSION_BY_FORMAT[image_format]
    return ("images", (file_name or f"photo.{extension}", data, IMAGE_CONTENT_TYPE_BY_FORMAT[image_format]))


def distinct_images(sample_image_bytes, count: int) -> list[bytes]:
    return [sample_image_bytes(color=(10 + index * 40, 80, 120)) for index in range(count)]


def insert_existing_photos(database_session, embedding_model, user_id: int, count: int) -> list[WardrobePhoto]:
    photos = [
        WardrobePhoto(
            user_id=user_id,
            image_key=f"wardrobe/{user_id}/existing{index}.jpg",
            embedding=embedding_model.embed_texts([f"existing-{user_id}-{index}"])[0],
        )
        for index in range(count)
    ]
    database_session.add_all(photos)
    database_session.commit()
    return photos


def load_photos(database_session, user_id: int) -> list[WardrobePhoto]:
    database_session.expire_all()
    return list(
        database_session.scalars(
            select(WardrobePhoto).where(WardrobePhoto.user_id == user_id).order_by(WardrobePhoto.id)
        ).all()
    )


def assert_wardrobe_photos_response(response) -> list[dict]:
    assert response.status_code == 200
    body = response.json()
    assert set(body) == WARDROBE_PHOTOS_RESPONSE_FIELDS
    assert isinstance(body["photos"], list)
    for photo in body["photos"]:
        assert set(photo) == WARDROBE_PHOTO_DTO_FIELDS
        assert isinstance(photo["id"], int)
        assert isinstance(photo["imageUrl"], str) and photo["imageUrl"]
    photo_ids = [photo["id"] for photo in body["photos"]]
    assert photo_ids == sorted(photo_ids)
    return body["photos"]


# ---- 정상 ----
def test_upload_returns_all_user_photos_and_stores_original_images_with_embeddings(
    client, create_user, auth_headers, database_session, storage, embedding_model, sample_image_bytes
):
    user = create_user(nickname="dresser")
    existing_photo = insert_existing_photos(database_session, embedding_model, user.id, 1)[0]
    jpeg_bytes = sample_image_bytes(color=(200, 30, 30), image_format="JPEG")
    png_bytes = sample_image_bytes(color=(30, 200, 30), image_format="PNG")

    response = client.post(
        WARDROBE_PHOTOS_PATH,
        files=[image_file(jpeg_bytes, "JPEG"), image_file(png_bytes, "PNG")],
        headers=auth_headers(user),
    )

    photos = assert_wardrobe_photos_response(response)
    stored_photos = load_photos(database_session, user.id)
    assert len(stored_photos) == 3
    assert [photo["id"] for photo in photos] == [stored_photo.id for stored_photo in stored_photos]
    assert photos[0]["id"] == existing_photo.id

    new_photos = stored_photos[1:]
    uploaded_images = sorted(
        [(jpeg_bytes, "jpg"), (png_bytes, "png")], key=lambda image: image[0]
    )
    stored_images = sorted(
        [(storage.objects[photo.image_key], photo.image_key.rsplit(".", 1)[1]) for photo in new_photos],
        key=lambda image: image[0],
    )
    assert stored_images == uploaded_images  # 원본 그대로 저장, 확장자는 형식과 일치

    for photo in new_photos:
        assert re.fullmatch(rf"wardrobe/{user.id}/[0-9a-f]{{32}}\.(jpg|png)", photo.image_key)
        assert len(photo.embedding) == EMBEDDING_DIMENSION
        expected_embedding = embedding_model.embed_images([storage.objects[photo.image_key]])[0]
        assert list(photo.embedding) == pytest.approx(expected_embedding, abs=1e-5)  # 전처리 없이 원본 임베딩


@pytest.mark.parametrize(("existing_count", "upload_count"), [(0, 1), (0, WARDROBE_PHOTO_LIMIT), (2, 2), (3, 1)])
def test_upload_within_limit_succeeds(
    client, create_user, auth_headers, database_session, embedding_model, sample_image_bytes,
    existing_count, upload_count,
):
    user = create_user(nickname="dresser")
    insert_existing_photos(database_session, embedding_model, user.id, existing_count)

    response = client.post(
        WARDROBE_PHOTOS_PATH,
        files=[image_file(data) for data in distinct_images(sample_image_bytes, upload_count)],
        headers=auth_headers(user),
    )

    photos = assert_wardrobe_photos_response(response)
    assert len(photos) == existing_count + upload_count
    assert len(load_photos(database_session, user.id)) == existing_count + upload_count


# ---- 불변조건 위반 ----
@pytest.mark.parametrize(("existing_count", "upload_count"), [(4, 1), (3, 2), (1, 4)])
def test_upload_over_limit_returns_wardrobe_limit_exceeded_and_keeps_rows(
    client, create_user, auth_headers, database_session, embedding_model, sample_image_bytes,
    existing_count, upload_count,
):
    user = create_user(nickname="dresser")
    insert_existing_photos(database_session, embedding_model, user.id, existing_count)
    before_ids = [photo.id for photo in load_photos(database_session, user.id)]

    response = client.post(
        WARDROBE_PHOTOS_PATH,
        files=[image_file(data) for data in distinct_images(sample_image_bytes, upload_count)],
        headers=auth_headers(user),
    )

    assert_error(response, 409, ErrorCode.WARDROBE_LIMIT_EXCEEDED)
    assert [photo.id for photo in load_photos(database_session, user.id)] == before_ids


@pytest.mark.parametrize("invalid_kind", ["text", "gif", "oversized", "empty"])
def test_upload_with_any_invalid_image_rejects_all_and_stores_no_rows(
    client, create_user, auth_headers, database_session, sample_image_bytes, invalid_kind
):
    user = create_user(nickname="dresser")
    invalid_file = {
        "text": ("images", ("note.jpg", b"this is not an image", "image/jpeg")),
        "gif": ("images", ("photo.gif", sample_image_bytes(image_format="GIF"), "image/gif")),
        "oversized": ("images", ("huge.jpg", b"\xff\xd8\xff" + b"0" * (10 * 1024 * 1024), "image/jpeg")),
        "empty": ("images", ("empty.jpg", b"", "image/jpeg")),
    }[invalid_kind]
    valid_files = [image_file(data) for data in distinct_images(sample_image_bytes, 2)]

    response = client.post(
        WARDROBE_PHOTOS_PATH,
        files=[valid_files[0], invalid_file, valid_files[1]],
        headers=auth_headers(user),
    )

    assert_error(response, 400, ErrorCode.INVALID_IMAGE)
    assert load_photos(database_session, user.id) == []


@pytest.mark.parametrize("upload_count", [0, WARDROBE_PHOTO_LIMIT + 1])
def test_upload_with_invalid_image_count_returns_validation_error(
    client, create_user, auth_headers, database_session, sample_image_bytes, upload_count
):
    user = create_user(nickname="dresser")

    response = client.post(
        WARDROBE_PHOTOS_PATH,
        files=[image_file(data) for data in distinct_images(sample_image_bytes, upload_count)],
        headers=auth_headers(user),
    )

    assert_error(response, 422, ErrorCode.VALIDATION_ERROR)
    assert load_photos(database_session, user.id) == []


# ---- 권한 ----
def test_upload_counts_and_returns_only_token_owner_photos(
    client, create_user, auth_headers, database_session, embedding_model, sample_image_bytes
):
    owner = create_user(nickname="owner")
    other_user = create_user(nickname="other")
    other_photos = insert_existing_photos(database_session, embedding_model, other_user.id, WARDROBE_PHOTO_LIMIT)
    other_photo_ids = [photo.id for photo in other_photos]

    response = client.post(
        WARDROBE_PHOTOS_PATH,
        files=[image_file(data) for data in distinct_images(sample_image_bytes, 1)],
        headers=auth_headers(owner),
    )

    photos = assert_wardrobe_photos_response(response)
    owner_photos = load_photos(database_session, owner.id)
    assert [photo["id"] for photo in photos] == [photo.id for photo in owner_photos]
    assert len(owner_photos) == 1
    assert owner_photos[0].image_key.startswith(f"wardrobe/{owner.id}/")
    assert [photo.id for photo in load_photos(database_session, other_user.id)] == other_photo_ids


def _token_with(user_id: int, secret: str, expires_at: datetime) -> str:
    return jwt.encode({"sub": str(user_id), "exp": expires_at}, secret, algorithm="HS256")


@pytest.mark.parametrize("token_kind", ["missing", "expired", "forged"])
def test_upload_without_valid_token_returns_unauthorized(
    client, create_user, database_session, sample_image_bytes, token_kind
):
    user = create_user(nickname="member")
    secret = get_settings().jwt_secret
    headers = {
        "missing": {},
        "expired": {"Authorization": f"Bearer {_token_with(user.id, secret, datetime.now(UTC) - timedelta(minutes=1))}"},
        "forged": {"Authorization": f"Bearer {_token_with(user.id, 'forged-secret-key-0123456789abcdef', datetime.now(UTC) + timedelta(days=1))}"},
    }[token_kind]

    response = client.post(
        WARDROBE_PHOTOS_PATH,
        files=[image_file(data) for data in distinct_images(sample_image_bytes, 1)],
        headers=headers,
    )

    assert_error(response, 401, ErrorCode.UNAUTHORIZED)
    assert load_photos(database_session, user.id) == []
