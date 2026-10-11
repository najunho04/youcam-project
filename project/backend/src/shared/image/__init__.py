"""업로드 이미지 검증과 외부 이미지 다운로드."""
import io

import httpx
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from common.error import AppError, ErrorCode

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # YouCam 입력 제한과 동일
ALLOWED_IMAGE_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png"}


class ValidatedImage:
    def __init__(self, data: bytes, content_type: str, extension: str) -> None:
        self.data = data
        self.content_type = content_type
        self.extension = extension


def read_upload_image(upload_file: UploadFile) -> ValidatedImage:
    """jpg/png, 10MB 이하, 실제 이미지인지 검사. 실패 시 INVALID_IMAGE."""
    data = upload_file.file.read(MAX_IMAGE_BYTES + 1)
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise AppError(ErrorCode.INVALID_IMAGE, "10MB 이하 이미지만 업로드할 수 있습니다")
    try:
        with Image.open(io.BytesIO(data)) as image:
            image_format = image.format
            image.verify()
    except (UnidentifiedImageError, OSError) as error:
        raise AppError(ErrorCode.INVALID_IMAGE, "이미지 파일이 아닙니다") from error
    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise AppError(ErrorCode.INVALID_IMAGE, "jpg 또는 png 만 업로드할 수 있습니다")
    return ValidatedImage(data, ALLOWED_IMAGE_FORMATS[image_format], "png" if image_format == "PNG" else "jpg")


def download_image(url: str, timeout_seconds: float = 20.0) -> bytes:
    """외부 이미지(상품 이미지, YouCam 결과) 다운로드. 실패 시 EXTERNAL_API_FAILED."""
    try:
        response = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
        response.raise_for_status()
        return response.content
    except httpx.HTTPError as error:
        raise AppError(ErrorCode.EXTERNAL_API_FAILED, "이미지 다운로드 실패") from error
