"""naver_client 단위 테스트. 실제 네이버 API 는 호출하지 않는다 (httpx.MockTransport)."""
import httpx
import pytest

from common.error import AppError, ErrorCode
from feature.product_ingest import naver_client
from shared.config import get_settings

SAMPLE_ITEMS = [{"productId": "1", "title": "<b>니트</b>", "link": "l", "image": "i", "lprice": "1000", "mallName": "m"}]


def http_client_with(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_search_products_sends_credentials_and_query_and_returns_items():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"total": 1, "items": SAMPLE_ITEMS})

    items = naver_client.search_products("여성 20대 미니멀 상의", 50, http_client=http_client_with(handler))

    assert items == SAMPLE_ITEMS
    (request,) = requests
    settings = get_settings()
    assert str(request.url).startswith(naver_client.NAVER_SHOP_SEARCH_URL)
    assert request.method == "GET"
    assert request.headers["X-Naver-Client-Id"] == settings.naver_client_id
    assert request.headers["X-Naver-Client-Secret"] == settings.naver_client_secret
    assert dict(request.url.params) == {"query": "여성 20대 미니멀 상의", "display": "50", "start": "1", "sort": "sim"}


@pytest.mark.parametrize(
    "handler",
    [
        lambda request: httpx.Response(401, json={"errorMessage": "unauthorized"}),
        lambda request: httpx.Response(200, json={"total": 0}),
        lambda request: httpx.Response(200, content=b"not json"),
    ],
    ids=["http-error-status", "missing-items", "invalid-json"],
)
def test_search_products_failure_raises_external_api_failed(handler):
    with pytest.raises(AppError) as raised:
        naver_client.search_products("검색어", 50, http_client=http_client_with(handler))

    assert raised.value.error_code == ErrorCode.EXTERNAL_API_FAILED


def test_search_products_network_error_raises_external_api_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(AppError) as raised:
        naver_client.search_products("검색어", 50, http_client=http_client_with(handler))

    assert raised.value.error_code == ErrorCode.EXTERNAL_API_FAILED
