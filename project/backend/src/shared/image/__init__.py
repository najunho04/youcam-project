"""업로드 이미지 검증과 외부 이미지 다운로드."""
import io

import httpx
from fastapi import UploadFile
from PIL import Image, ImageOps, UnidentifiedImageError

from common.error import AppError, ErrorCode

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # YouCam 입력 제한과 동일
ALLOWED_IMAGE_FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png"}
# YouCam 은 긴 변 4096px 초과 사진을 얼굴 에러가 아닌 에러로 거절하고, 1080px 넘으면 어차피 줄여서 분석한다
MAX_IMAGE_SIDE = 2048
_EXIF_ORIENTATION_TAG = 0x0112


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
    return ValidatedImage(
        _normalize_image(data, image_format), ALLOWED_IMAGE_FORMATS[image_format], "png" if image_format == "PNG" else "jpg"
    )


def _normalize_image(data: bytes, image_format: str) -> bytes:
    """긴 변이 MAX_IMAGE_SIDE 를 넘거나 EXIF 회전 정보가 있으면 회전 적용 + 축소해 같은 형식으로 다시 저장한다.
    YouCam 은 URL 로 받은 원본을 그대로 읽으므로 업로드 시점에 맞춰 둔다."""
    with Image.open(io.BytesIO(data)) as image:
        orientation = image.getexif().get(_EXIF_ORIENTATION_TAG, 1)
        if max(image.size) <= MAX_IMAGE_SIDE and orientation == 1:
            return data
        normalized = ImageOps.exif_transpose(image)
        normalized.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        if image_format == "JPEG" and normalized.mode != "RGB":
            normalized = normalized.convert("RGB")
        buffer = io.BytesIO()
        normalized.save(buffer, format=image_format, **({"quality": 92} if image_format == "JPEG" else {}))
        return buffer.getvalue()


def download_image(url: str, timeout_seconds: float = 20.0) -> bytes:
    """외부 이미지(상품 이미지, YouCam 결과) 다운로드. 실패 시 EXTERNAL_API_FAILED."""
    try:
        response = httpx.get(url, timeout=timeout_seconds, follow_redirects=True)
        response.raise_for_status()
        return response.content
    except httpx.HTTPError as error:
        raise AppError(ErrorCode.EXTERNAL_API_FAILED, "이미지 다운로드 실패") from error
