import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import setup_logger

logger = setup_logger()

TESTNET_BASE_URL = "https://testnet.binancefuture.com"


class BinanceAPIError(Exception):
    """Raised when Binance returns a non-200 response or an API error code."""

    def __init__(self, message: str, code: Optional[int] = None):
        super().__init__(message)
        self.code = code


class BinanceClient:
    """
    Lightweight wrapper around the Binance USDT-M Futures Testnet REST API.

    Handles HMAC-SHA256 request signing, a persistent HTTP session,
    and consistent error handling so callers don't have to think about
    transport-level details.
    """

    def __init__(self, api_key: str, api_secret: str):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must be non-empty.")
        self._api_key = api_key
        self._api_secret = api_secret

        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": self._api_key})

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adds a timestamp and HMAC-SHA256 signature to params.
        Binance requires both on every signed endpoint.
        """
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        params["signature"] = hmac.new(
            self._api_secret.encode(),
            query_string.encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()
        return params

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = True,
    ) -> Dict[str, Any]:
        params = params or {}
        if signed:
            params = self._sign(params)

        url = f"{TESTNET_BASE_URL}{endpoint}"

        # Log outgoing request (signature redacted)
        safe_params = {k: ("***" if k == "signature" else v) for k, v in params.items()}
        logger.debug(">> %s %s  params=%s", method.upper(), endpoint, safe_params)

        try:
            resp = self._session.request(method, url, params=params, timeout=10)
        except requests.exceptions.ConnectionError as exc:
            raise BinanceAPIError(
                f"Could not connect to {TESTNET_BASE_URL}. "
                "Check your internet connection."
            ) from exc
        except requests.exceptions.Timeout:
            raise BinanceAPIError("Request timed out after 10 seconds.")

        logger.debug("<< HTTP %d  body=%s", resp.status_code, resp.text[:600])

        try:
            data = resp.json()
        except ValueError:
            raise BinanceAPIError(
                f"Unexpected non-JSON response (HTTP {resp.status_code}): "
                f"{resp.text[:200]}"
            )

        # Binance signals errors via non-200 status with a 'code'/'msg' body
        if resp.status_code != 200:
            code = data.get("code")
            msg = data.get("msg", "Unknown error")
            raise BinanceAPIError(f"[{code}] {msg}", code=code)

        return data

    # ------------------------------------------------------------------ #
    # Public API methods                                                   #
    # ------------------------------------------------------------------ #

    def place_order(self, **kwargs: Any) -> Dict[str, Any]:
        """
        POST /fapi/v1/order
        Used for MARKET and LIMIT orders.
        """
        return self._request("POST", "/fapi/v1/order", params=dict(kwargs))

    def place_algo_order(self, **kwargs: Any) -> Dict[str, Any]:
        """
        POST /fapi/v1/algoOrder
        Required for conditional orders (STOP_MARKET, TAKE_PROFIT_MARKET, etc.)
        after Binance's December 2025 API migration.
        """
        return self._request("POST", "/fapi/v1/algoOrder", params=dict(kwargs))

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """GET /fapi/v1/order — fetch current state of an existing order."""
        return self._request(
            "GET", "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
        )
