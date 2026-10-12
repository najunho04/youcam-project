"""네이버 쇼핑 검색 API 호출. 실패는 AppError(EXTERNAL_API_FAILED) 로만 알린다."""
import httpx

from common.error import AppError, ErrorCode
from shared.config import get_settings

NAVER_SHOP_SEARCH_URL = "https://openapi.naver.com/v1/search/shop.json"
_TIMEOUT_SECONDS = 10.0


def search_products(query: str, display: int, http_client: httpx.Client | None = None) -> list[dict]:
    """검색 결과 items[] 를 그대로 돌려준다. start=1, sort=sim 고정."""
    settings = get_settings()
    client = http_client or httpx.Client(timeout=_TIMEOUT_SECONDS)
    try:
        response = client.get(
            NAVER_SHOP_SEARCH_URL,
            headers={
                "X-Naver-Client-Id": settings.naver_client_id,
                "X-Naver-Client-Secret": settings.naver_client_secret,
            },
            params={"query": query, "display": display, "start": 1, "sort": "sim"},
        )
        response.raise_for_status()
        items = response.json()["items"]
    except (httpx.HTTPError, KeyError, ValueError) as error:
        raise AppError(ErrorCode.EXTERNAL_API_FAILED, "네이버 쇼핑 검색 실패") from error
    finally:
        if http_client is None:
            client.close()
    if not isinstance(items, list):
        raise AppError(ErrorCode.EXTERNAL_API_FAILED, "네이버 쇼핑 검색 응답 형식 오류")
    return items
