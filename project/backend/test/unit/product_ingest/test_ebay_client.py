"""ebay_client 단위 테스트. 실제 eBay API 는 호출하지 않는다 (httpx.MockTransport)."""
import httpx
import pytest

from common.error import AppError, ErrorCode
from feature.product_ingest import ebay_client
from shared.config import get_settings

SAMPLE_ITEMS = [{"itemId": "v1|1|0", "title": "Top"}]


def client_with(handler) -> ebay_client.EbayClient:
    return ebay_client.EbayClient(
        http_client=httpx.Client(base_url="https://api.ebay.test", transport=httpx.MockTransport(handler))
    )


def token_response() -> httpx.Response:
    return httpx.Response(200, json={"access_token": "token-1", "expires_in": 7200, "token_type": "Application Access Token"})


def test_search_items_gets_token_once_and_sends_query_with_marketplace():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == ebay_client.TOKEN_PATH:
            return token_response()
        return httpx.Response(200, json={"itemSummaries": SAMPLE_ITEMS})

    client = client_with(handler)
    first_items = client.search_items("women trendy minimal top", 50, 50, "53159")
    client.search_items("men casual top", 50)

    assert first_items == SAMPLE_ITEMS
    token_requests = [request for request in requests if request.url.path == ebay_client.TOKEN_PATH]
    search_requests = [request for request in requests if request.url.path == ebay_client.SEARCH_PATH]
    assert len(token_requests) == 1
    assert b"grant_type=client_credentials" in token_requests[0].content
    assert token_requests[0].headers["Authorization"].startswith("Basic ")
    assert search_requests[0].headers["Authorization"] == "Bearer token-1"
    assert search_requests[0].headers["X-EBAY-C-MARKETPLACE-ID"] == get_settings().ebay_marketplace_id
    assert dict(search_requests[0].url.params) == {
        "q": "women trendy minimal top", "limit": "50", "offset": "50", "category_ids": "53159",
    }
    assert dict(search_requests[1].url.params) == {"q": "men casual top", "limit": "50", "offset": "0"}


def test_search_items_without_results_returns_empty_list():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == ebay_client.TOKEN_PATH:
            return token_response()
        return httpx.Response(200, json={"total": 0})

    assert client_with(handler).search_items("q", 50) == []


@pytest.mark.parametrize("failing_path", [ebay_client.TOKEN_PATH, ebay_client.SEARCH_PATH])
def test_failures_raise_external_api_failed(failing_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == failing_path:
            return httpx.Response(500)
        if request.url.path == ebay_client.TOKEN_PATH:
            return token_response()
        return httpx.Response(200, json={"itemSummaries": SAMPLE_ITEMS})

    with pytest.raises(AppError) as error:
        client_with(handler).search_items("q", 50)
    assert error.value.error_code == ErrorCode.EXTERNAL_API_FAILED


def test_invalid_item_summaries_raise_external_api_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == ebay_client.TOKEN_PATH:
            return token_response()
        return httpx.Response(200, json={"itemSummaries": "not a list"})

    with pytest.raises(AppError) as error:
        client_with(handler).search_items("q", 50)
    assert error.value.error_code == ErrorCode.EXTERNAL_API_FAILED


def test_search_items_without_query_sends_only_category():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == ebay_client.TOKEN_PATH:
            return token_response()
        return httpx.Response(200, json={"itemSummaries": SAMPLE_ITEMS})

    client_with(handler).search_items("", 100, 0, "53159")

    search_request = [request for request in requests if request.url.path == ebay_client.SEARCH_PATH][0]
    assert dict(search_request.url.params) == {"limit": "100", "offset": "0", "category_ids": "53159"}
