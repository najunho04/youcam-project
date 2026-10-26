"""LiveYouCamClient 응답 해석. 실제 호출 없이 httpx.MockTransport 로 공식 스펙 형태의 응답을 흉내 낸다."""
import httpx
import pytest

from common.dto import FaceColorsDto
from common.error import AppError, ErrorCode
from shared.youcam import LiveYouCamClient


def make_client(task_result: dict) -> LiveYouCamClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json={"status": 200, "data": {"task_id": "task-1"}})
        return httpx.Response(200, json={"status": 200, "data": task_result})

    client = LiveYouCamClient("https://youcam.test", "key", poll_interval_seconds=0, poll_timeout_seconds=1)
    client._http = httpx.Client(base_url="https://youcam.test", transport=httpx.MockTransport(handler))
    return client


# 공식 문서 Outputs 예시 그대로
OFFICIAL_COLOR_RESULT = {
    "eye_color": "#293F9B",
    "eye_color_name": "Blue",
    "lip_color": "#D23245",
    "eyebrow_color": "#5B2B31",
    "skin_color": "#b9947c",
    "hair_color": "#a0a0a0",
    "hair_color_name": "Auburn",
}


def test_analyze_face_colors_returns_all_colors_in_uppercase_hex():
    client = make_client({"task_status": "success", "results": {"color": OFFICIAL_COLOR_RESULT}})

    face_colors = client.analyze_face_colors("https://image.test/selfie.jpg")

    assert face_colors == FaceColorsDto(
        skin="#B9947C", lip="#D23245", eye="#293F9B", eyebrow="#5B2B31", hair="#A0A0A0",
        eye_color_name="Blue", hair_color_name="Auburn",
    )


def test_missing_color_names_become_none():
    color_result = {key: value for key, value in OFFICIAL_COLOR_RESULT.items() if not key.endswith("_name")}
    client = make_client({"task_status": "success", "results": {"color": color_result}})

    face_colors = client.analyze_face_colors("https://image.test/selfie.jpg")

    assert face_colors.eye_color_name is None
    assert face_colors.hair_color_name is None


@pytest.mark.parametrize("missing_key", ["skin_color", "lip_color", "eye_color", "eyebrow_color", "hair_color"])
def test_missing_hex_becomes_external_api_failed(missing_key):
    color_result = {key: value for key, value in OFFICIAL_COLOR_RESULT.items() if key != missing_key}
    client = make_client({"task_status": "success", "results": {"color": color_result}})

    with pytest.raises(AppError) as raised:
        client.analyze_face_colors("https://image.test/selfie.jpg")
    assert raised.value.error_code == ErrorCode.EXTERNAL_API_FAILED


def test_invalid_hex_becomes_external_api_failed():
    client = make_client({"task_status": "success", "results": {"color": {**OFFICIAL_COLOR_RESULT, "lip_color": "red"}}})

    with pytest.raises(AppError) as raised:
        client.analyze_face_colors("https://image.test/selfie.jpg")
    assert raised.value.error_code == ErrorCode.EXTERNAL_API_FAILED


@pytest.mark.parametrize("error_code", ["error_no_face", "error_face_position_too_small", "error_below_min_image_size"])
def test_face_errors_become_face_not_detected(error_code):
    client = make_client({"task_status": "error", "error": error_code})

    with pytest.raises(AppError) as raised:
        client.analyze_face_colors("https://image.test/selfie.jpg")
    assert raised.value.error_code == ErrorCode.FACE_NOT_DETECTED


def test_other_errors_become_external_api_failed():
    client = make_client({"task_status": "error", "error": "error_download_image"})

    with pytest.raises(AppError) as raised:
        client.analyze_face_colors("https://image.test/selfie.jpg")
    assert raised.value.error_code == ErrorCode.EXTERNAL_API_FAILED
