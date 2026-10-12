"""wardrobe 슬라이스 비즈니스 로직. 실패는 AppError 로만 알린다."""
from fastapi import UploadFile
from sqlalchemy.orm import Session

from common.dto import WardrobePhotoDto, WardrobePhotosResponse
from common.entity import WARDROBE_PHOTO_LIMIT, User
from common.error import AppError, ErrorCode
from feature.wardrobe import repository
from shared.embedding import get_embedding_model
from shared.image import read_upload_image
from shared.storage import get_storage, new_object_key

_STORAGE_KEY_PREFIX = "wardrobe"


def upload_wardrobe_photos(database_session: Session, user: User, upload_files: list[UploadFile]) -> WardrobePhotosResponse:
    """검증(개수·한도·이미지) → 저장소 업로드 → 원본 임베딩 → 행 저장. 하나라도 실패하면 아무것도 남기지 않는다."""
    if not 1 <= len(upload_files) <= WARDROBE_PHOTO_LIMIT:
        raise AppError(ErrorCode.VALIDATION_ERROR, f"사진은 1~{WARDROBE_PHOTO_LIMIT}장 올릴 수 있습니다")
    if repository.count_photos_by_user(database_session, user.id) + len(upload_files) > WARDROBE_PHOTO_LIMIT:
        raise AppError(ErrorCode.WARDROBE_LIMIT_EXCEEDED, f"사진은 최대 {WARDROBE_PHOTO_LIMIT}장까지 저장할 수 있습니다")
    validated_images = [read_upload_image(upload_file) for upload_file in upload_files]

    storage = get_storage()
    uploaded_keys: list[str] = []
    try:
        for validated_image in validated_images:
            image_key = new_object_key(_STORAGE_KEY_PREFIX, user.id, validated_image.extension)
            storage.upload(image_key, validated_image.data, validated_image.content_type)
            uploaded_keys.append(image_key)
        embeddings = get_embedding_model().embed_images([validated_image.data for validated_image in validated_images])
        repository.add_photos(database_session, user.id, uploaded_keys, embeddings)
    except Exception:
        for image_key in uploaded_keys:
            storage.delete(image_key)
        raise

    return WardrobePhotosResponse(
        photos=[
            WardrobePhotoDto(id=photo.id, image_url=storage.get_url(photo.image_key))
            for photo in repository.find_photos_by_user(database_session, user.id)
        ]
    )
