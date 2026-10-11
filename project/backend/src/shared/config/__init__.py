from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageMode(StrEnum):
    S3 = "s3"
    LOCAL = "local"    # 개발용. backend/var/storage 에 저장, /api/local-files 로 서빙
    MEMORY = "memory"  # 테스트용


class YouCamMode(StrEnum):
    LIVE = "live"
    MOCK = "mock"  # 크레딧 절약. 고정 응답


class EmbeddingMode(StrEnum):
    FASHION_CLIP = "fashion_clip"
    FAKE = "fake"  # 테스트용. 입력 바이트 해시 기반 결정적 벡터


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://colorfit:colorfit@localhost:5432/colorfit"

    jwt_secret: str = "change-me"
    jwt_expire_days: int = 7

    storage_mode: StorageMode = StorageMode.LOCAL
    s3_bucket: str = ""
    aws_region: str = "ap-northeast-2"
    presigned_url_expire_seconds: int = 3600
    local_storage_directory: str = "var/storage"
    public_base_url: str = "http://localhost:8000"  # local 모드 이미지 URL 접두

    youcam_mode: YouCamMode = YouCamMode.MOCK
    youcam_api_key: str = ""
    youcam_base_url: str = "https://yce-api-01.makeupar.com"
    youcam_poll_interval_seconds: float = 2.0
    youcam_poll_timeout_seconds: float = 120.0

    embedding_mode: EmbeddingMode = EmbeddingMode.FASHION_CLIP
    embedding_model_name: str = "patrickjohncyh/fashion-clip"

    naver_client_id: str = ""
    naver_client_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
