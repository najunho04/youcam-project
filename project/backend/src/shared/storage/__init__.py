"""사용자 사진·피팅 결과 저장소. 슬라이스는 get_storage() 의존성으로만 접근한다.

키 규칙 (erd.md): selfies/{userId}/{uuid}.jpg, body-images/{userId}/{uuid}.jpg, wardrobe/{userId}/{uuid}.jpg, fittings/{userId}/{fittingId}.jpg
"""
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from common.error import AppError, ErrorCode
from shared.config import StorageMode, get_settings


class Storage(Protocol):
    def upload(self, key: str, data: bytes, content_type: str) -> None: ...
    def get_url(self, key: str) -> str: ...  # 브라우저·YouCam 이 바로 열 수 있는 URL (S3 는 presigned)
    def delete(self, key: str) -> None: ...


def new_object_key(prefix: str, user_id: int, extension: str = "jpg") -> str:
    return f"{prefix}/{user_id}/{uuid.uuid4().hex}.{extension}"


class S3Storage:
    def __init__(self, bucket: str, region: str, expire_seconds: int) -> None:
        import boto3

        self._client = boto3.client("s3", region_name=region)
        self._bucket = bucket
        self._expire_seconds = expire_seconds

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        try:
            self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)
        except Exception as error:
            raise AppError(ErrorCode.EXTERNAL_API_FAILED, "이미지 저장 실패") from error

    def get_url(self, key: str) -> str:
        return self._client.generate_presigned_url(
            "get_object", Params={"Bucket": self._bucket, "Key": key}, ExpiresIn=self._expire_seconds
        )

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)


class LocalStorage:
    URL_PATH = "/api/local-files"

    def __init__(self, directory: str, public_base_url: str) -> None:
        self.directory = Path(directory)
        self._public_base_url = public_base_url.rstrip("/")

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        path = self.directory / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get_url(self, key: str) -> str:
        return f"{self._public_base_url}{self.URL_PATH}/{key}"

    def delete(self, key: str) -> None:
        (self.directory / key).unlink(missing_ok=True)


class MemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    def get_url(self, key: str) -> str:
        return f"https://storage.test/{key}"

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    match settings.storage_mode:
        case StorageMode.S3:
            return S3Storage(settings.s3_bucket, settings.aws_region, settings.presigned_url_expire_seconds)
        case StorageMode.LOCAL:
            return LocalStorage(settings.local_storage_directory, settings.public_base_url)
        case StorageMode.MEMORY:
            return MemoryStorage()
