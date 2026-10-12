"""wardrobe service 단위 테스트."""
import io

import pytest
from fastapi import UploadFile
from sqlalchemy import select

from common.entity import EMBEDDING_DIMENSION, WARDROBE_PHOTO_LIMIT, WardrobePhoto
from common.error import AppError, ErrorCode
from feature.wardrobe import repository, service


def upload_file(data: bytes, file_name: str = "photo.jpg") -> UploadFile:
    return UploadFile(file=io.BytesIO(data), filename=file_name)


def distinct_upload_files(sample_image_bytes, count: int) -> list[UploadFile]:
    return [upload_file(sample_image_bytes(color=(10 + index * 40, 80, 120), size=64)) for index in range(count)]


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


def assert_app_error(raised: pytest.ExceptionInfo[AppError], error_code: ErrorCode) -> None:
    assert raised.value.error_code == error_code


# ---- upload_wardrobe_photos: 정상 ----
def test_upload_stores_original_images_and_embeddings_and_returns_all_photos_in_id_order(
    database_session, create_user, storage, embedding_model, sample_image_bytes
):
    user = create_user(nickname="dresser")
    existing_photo = insert_existing_photos(database_session, embedding_model, user.id, 1)[0]
    jpeg_bytes = sample_image_bytes(color=(200, 30, 30), image_format="JPEG", size=64)
    png_bytes = sample_image_bytes(color=(30, 200, 30), image_format="PNG", size=64)

    response = service.upload_wardrobe_photos(
        database_session, user, [upload_file(jpeg_bytes, "a.jpg"), upload_file(png_bytes, "b.png")]
    )
    database_session.commit()

    stored_photos = load_photos(database_session, user.id)
    assert [photo.id for photo in response.photos] == [photo.id for photo in stored_photos]
    assert response.photos[0].id == existing_photo.id
    assert [photo.image_url for photo in response.photos] == [storage.get_url(photo.image_key) for photo in stored_photos]

    jpeg_photo, png_photo = stored_photos[1:]
    assert jpeg_photo.image_key.startswith(f"wardrobe/{user.id}/") and jpeg_photo.image_key.endswith(".jpg")
    assert png_photo.image_key.startswith(f"wardrobe/{user.id}/") and png_photo.image_key.endswith(".png")
    assert storage.objects[jpeg_photo.image_key] == jpeg_bytes
    assert storage.objects[png_photo.image_key] == png_bytes
    for photo, original_bytes in [(jpeg_photo, jpeg_bytes), (png_photo, png_bytes)]:
        assert len(photo.embedding) == EMBEDDING_DIMENSION
        assert list(photo.embedding) == pytest.approx(embedding_model.embed_images([original_bytes])[0], abs=1e-5)


def test_upload_up_to_limit_including_existing_photos_succeeds(
    database_session, create_user, embedding_model, sample_image_bytes
):
    user = create_user(nickname="dresser")
    insert_existing_photos(database_session, embedding_model, user.id, WARDROBE_PHOTO_LIMIT - 1)

    response = service.upload_wardrobe_photos(database_session, user, distinct_upload_files(sample_image_bytes, 1))
    database_session.commit()

    assert len(response.photos) == WARDROBE_PHOTO_LIMIT
    assert len(load_photos(database_session, user.id)) == WARDROBE_PHOTO_LIMIT


def test_upload_returns_only_given_user_photos(database_session, create_user, embedding_model, sample_image_bytes):
    owner = create_user(nickname="owner")
    other_user = create_user(nickname="other")
    insert_existing_photos(database_session, embedding_model, other_user.id, WARDROBE_PHOTO_LIMIT)

    response = service.upload_wardrobe_photos(database_session, owner, distinct_upload_files(sample_image_bytes, 1))
    database_session.commit()

    assert [photo.id for photo in response.photos] == [photo.id for photo in load_photos(database_session, owner.id)]
    assert len(load_photos(database_session, other_user.id)) == WARDROBE_PHOTO_LIMIT


# ---- upload_wardrobe_photos: 거부 ----
@pytest.mark.parametrize("upload_count", [0, WARDROBE_PHOTO_LIMIT + 1])
def test_upload_with_invalid_image_count_raises_validation_error(
    database_session, create_user, storage, sample_image_bytes, upload_count
):
    user = create_user(nickname="dresser")

    with pytest.raises(AppError) as raised:
        service.upload_wardrobe_photos(database_session, user, distinct_upload_files(sample_image_bytes, upload_count))

    assert_app_error(raised, ErrorCode.VALIDATION_ERROR)
    assert storage.objects == {}


@pytest.mark.parametrize(("existing_count", "upload_count"), [(4, 1), (3, 2), (1, 4)])
def test_upload_over_limit_raises_wardrobe_limit_exceeded_without_storing(
    database_session, create_user, storage, embedding_model, sample_image_bytes, existing_count, upload_count
):
    user = create_user(nickname="dresser")
    insert_existing_photos(database_session, embedding_model, user.id, existing_count)

    with pytest.raises(AppError) as raised:
        service.upload_wardrobe_photos(database_session, user, distinct_upload_files(sample_image_bytes, upload_count))
    database_session.rollback()

    assert_app_error(raised, ErrorCode.WARDROBE_LIMIT_EXCEEDED)
    assert storage.objects == {}
    assert len(load_photos(database_session, user.id)) == existing_count


def test_upload_with_any_invalid_image_raises_invalid_image_without_storing(
    database_session, create_user, storage, sample_image_bytes
):
    user = create_user(nickname="dresser")
    valid_files = distinct_upload_files(sample_image_bytes, 2)

    with pytest.raises(AppError) as raised:
        service.upload_wardrobe_photos(
            database_session, user, [valid_files[0], upload_file(b"this is not an image"), valid_files[1]]
        )
    database_session.rollback()

    assert_app_error(raised, ErrorCode.INVALID_IMAGE)
    assert storage.objects == {}
    assert load_photos(database_session, user.id) == []


def test_upload_removes_uploaded_objects_when_embedding_fails(
    database_session, create_user, storage, embedding_model, sample_image_bytes, monkeypatch
):
    user = create_user(nickname="dresser")

    def failing_embed_images(images: list[bytes]) -> list[list[float]]:
        raise RuntimeError("embedding failed")

    monkeypatch.setattr(embedding_model, "embed_images", failing_embed_images)

    with pytest.raises(RuntimeError):
        service.upload_wardrobe_photos(database_session, user, distinct_upload_files(sample_image_bytes, 2))
    database_session.rollback()

    assert storage.objects == {}
    assert load_photos(database_session, user.id) == []


# ---- repository ----
def test_count_photos_by_user_counts_only_given_user(database_session, create_user, embedding_model):
    owner = create_user(nickname="owner")
    other_user = create_user(nickname="other")
    insert_existing_photos(database_session, embedding_model, owner.id, 2)
    insert_existing_photos(database_session, embedding_model, other_user.id, 3)

    assert repository.count_photos_by_user(database_session, owner.id) == 2


def test_find_photos_by_user_returns_photos_in_id_order(database_session, create_user, embedding_model):
    user = create_user(nickname="dresser")
    inserted_photos = insert_existing_photos(database_session, embedding_model, user.id, 3)

    found_photos = repository.find_photos_by_user(database_session, user.id)

    assert [photo.id for photo in found_photos] == sorted(photo.id for photo in inserted_photos)
