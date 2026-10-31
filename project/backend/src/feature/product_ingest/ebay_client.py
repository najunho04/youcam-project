"""eBay Browse API 호출. 실패는 AppError(EXTERNAL_API_FAILED) 로만 알린다.

토큰: client credentials (Application access token). 배치 1회 동안 재사용하고, 만료 1분 전이면 다시 받는다.
"""
import time

import httpx

from common.error import AppError, ErrorCode
from shared.config import get_settings

TOKEN_PATH = "/identity/v1/oauth2/token"
SEARCH_PATH = "/buy/browse/v1/item_summary/search"
TOKEN_SCOPE = "https://api.ebay.com/oauth/api_scope"
_TIMEOUT_SECONDS = 15.0
_TOKEN_REFRESH_MARGIN_SECONDS = 60


class EbayClient:
    def __init__(self, http_client: httpx.Client | None = None) -> None:
        settings = get_settings()
        self._client_id = settings.ebay_client_id
        self._client_secret = settings.ebay_client_secret
        self._marketplace_id = settings.ebay_marketplace_id
        self._http = http_client or httpx.Client(base_url=settings.ebay_base_url, timeout=_TIMEOUT_SECONDS)
        self._access_token: str | None = None
        self._token_expires_at = 0.0

    def _token(self) -> str:
        if self._access_token is not None and time.monotonic() < self._token_expires_at:
            return self._access_token
        try:
            response = self._http.post(
                TOKEN_PATH,
                auth=(self._client_id, self._client_secret),
                data={"grant_type": "client_credentials", "scope": TOKEN_SCOPE},
            )
            response.raise_for_status()
            body = response.json()
            self._access_token = str(body["access_token"])
            self._token_expires_at = time.monotonic() + float(body["expires_in"]) - _TOKEN_REFRESH_MARGIN_SECONDS
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as error:
            raise AppError(ErrorCode.EXTERNAL_API_FAILED, "eBay 토큰 발급 실패") from error
        return self._access_token

    def search_items(self, query: str, limit: int) -> list[dict]:
        """itemSummaries[] 를 그대로 돌려준다. 결과가 없으면 빈 목록. offset=0 고정."""
        try:
            response = self._http.get(
                SEARCH_PATH,
                headers={"Authorization": f"Bearer {self._token()}", "X-EBAY-C-MARKETPLACE-ID": self._marketplace_id},
                params={"q": query, "limit": limit, "offset": 0},
            )
            response.raise_for_status()
            items = response.json().get("itemSummaries", [])
        except (httpx.HTTPError, ValueError, AttributeError) as error:
            raise AppError(ErrorCode.EXTERNAL_API_FAILED, "eBay 검색 실패") from error
        if not isinstance(items, list):
            raise AppError(ErrorCode.EXTERNAL_API_FAILED, "eBay 검색 응답 형식 오류")
        return items

    def close(self) -> None:
        self._http.close()
