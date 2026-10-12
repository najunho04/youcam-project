"""LiveYouCamClient 응답 해석. 실제 호출 없이 httpx.MockTransport 로 공식 스펙 형태의 응답을 흉내 낸다."""
import httpx
import pytest

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


def test_analyze_skin_tone_returns_skin_color():
    client = make_client({"task_status": "success", "results": {"color": {"skin_color": "#b9947c"}}})

    assert client.analyze_skin_tone("https://image.test/selfie.jpg").skin_color_hex == "#b9947c"


@pytest.mark.parametrize("error_code", ["error_no_face", "error_face_position_too_small", "error_below_min_image_size"])
def test_face_errors_become_face_not_detected(error_code):
    client = make_client({"task_status": "error", "error": error_code})

    with pytest.raises(AppError) as raised:
        client.analyze_skin_tone("https://image.test/selfie.jpg")
    assert raised.value.error_code == ErrorCode.FACE_NOT_DETECTED


def test_other_errors_become_external_api_failed():
    client = make_client({"task_status": "error", "error": "error_download_image"})

    with pytest.raises(AppError) as raised:
        client.analyze_skin_tone("https://image.test/selfie.jpg")
    assert raised.value.error_code == ErrorCode.EXTERNAL_API_FAILED
