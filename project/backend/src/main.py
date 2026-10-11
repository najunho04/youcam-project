"""FastAPI 앱 조립 지점. 슬라이스는 아래 '슬라이스 라우터' 구역에 한 줄씩만 추가한다."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from shared.config import StorageMode, get_settings
from shared.database import initialize_database
from shared.exception import register_exception_handlers
from shared.storage import LocalStorage

# ---- 슬라이스 라우터 (슬라이스당 한 줄. 각 router 는 prefix 없이 "/api/..." 전체 경로를 쓴다) ----
FEATURE_ROUTERS: list[APIRouter] = [
]
# ---- 슬라이스 라우터 끝 ----


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


def create_app() -> FastAPI:
    application = FastAPI(title="ColorFit API", lifespan=lifespan)
    register_exception_handlers(application)

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    for router in FEATURE_ROUTERS:
        application.include_router(router)

    settings = get_settings()
    if settings.storage_mode == StorageMode.LOCAL:
        directory = Path(settings.local_storage_directory)
        directory.mkdir(parents=True, exist_ok=True)
        application.mount(LocalStorage.URL_PATH, StaticFiles(directory=directory), name="local-files")
    return application


app = create_app()
