"""foundation 스모크 테스트. 공용 레이어가 슬라이스 전에 동작하는지 확인한다."""
import io

import pytest
from PIL import Image
from fastapi import APIRouter, UploadFile

from common.error import AppError, ErrorCode
from main import app
from shared.color import AVOID_PALETTES, SUBTYPE_PALETTES, delta_e, hex_to_lab
from shared.image import MAX_IMAGE_SIDE, read_upload_image
from shared.security import CurrentUser

probe_router = APIRouter()


@probe_router.get("/api/_probe/me")
def probe_me(current_user: CurrentUser) -> dict:
    return {"id": current_user.id}


@probe_router.get("/api/_probe/error")
def probe_error() -> dict:
    raise AppError(ErrorCode.PRODUCT_NOT_FOUND)


app.include_router(probe_router)


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_current_user_requires_token(client):
    response = client.get("/api/_probe/me")
    assert response.status_code == 401
    assert response.json() == {"error": {"code": "UNAUTHORIZED", "message": "UNAUTHORIZED"}}


def test_current_user_with_token(client, create_user, auth_headers):
    user = create_user()
    assert client.get("/api/_probe/me", headers=auth_headers(user)).json() == {"id": user.id}


def test_app_error_format(client):
    response = client.get("/api/_probe/error")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PRODUCT_NOT_FOUND"


def test_product_factory_and_vector(create_product):
    product = create_product()
    assert len(product.embedding) == 512


def test_read_upload_image(sample_image_bytes):
    image = read_upload_image(UploadFile(io.BytesIO(sample_image_bytes(image_format="PNG"))))
    assert image.content_type == "image/png"
    with pytest.raises(AppError) as error:
        read_upload_image(UploadFile(io.BytesIO(b"not an image")))
    assert error.value.error_code == ErrorCode.INVALID_IMAGE


def test_read_upload_image_shrinks_large_image(sample_image_bytes):
    image = read_upload_image(UploadFile(io.BytesIO(sample_image_bytes(size=5000))))
    with Image.open(io.BytesIO(image.data)) as resized:
        assert max(resized.size) == MAX_IMAGE_SIDE
        assert resized.format == "JPEG"


def test_read_upload_image_keeps_small_image_bytes(sample_image_bytes):
    data = sample_image_bytes()
    assert read_upload_image(UploadFile(io.BytesIO(data))).data == data


def test_color_utils():
    assert delta_e(hex_to_lab("#FFFFFF"), hex_to_lab("#FFFFFF")) == 0
    assert all(len(palette) == 8 for palette in SUBTYPE_PALETTES.values())
    assert all(len(palette) == 6 for palette in AVOID_PALETTES.values())
