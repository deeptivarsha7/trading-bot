from typing import Any, Dict, Optional

from .client import BinanceAPIError, BinanceClient
from .logging_config import setup_logger

logger = setup_logger()


def place_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
) -> Dict[str, Any]:
    """Place a MARKET order. Executes immediately at the current best price."""
    logger.info("Placing MARKET %s | symbol=%s qty=%s", side, symbol, quantity)
    try:
        response = client.place_order(
            symbol=symbol,
            side=side,
            type="MARKET",
            quantity=quantity,
        )
    except BinanceAPIError:
        logger.exception("MARKET order failed")
        raise

    logger.info("MARKET order accepted | orderId=%s status=%s",
                response.get("orderId"), response.get("status"))
    return response


def place_limit_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
    price: float,
    time_in_force: str = "GTC",
) -> Dict[str, Any]:
    """
    Place a LIMIT order. Rests on the book until filled or cancelled.
    time_in_force: GTC (default), IOC, or FOK.
    """
    logger.info(
        "Placing LIMIT %s | symbol=%s qty=%s price=%s tif=%s",
        side, symbol, quantity, price, time_in_force,
    )
    try:
        response = client.place_order(
            symbol=symbol,
            side=side,
            type="LIMIT",
            quantity=quantity,
            price=price,
            timeInForce=time_in_force,
        )
    except BinanceAPIError:
        logger.exception("LIMIT order failed")
        raise

    logger.info("LIMIT order accepted | orderId=%s status=%s",
                response.get("orderId"), response.get("status"))
    return response


def place_stop_market_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    quantity: float,
    stop_price: float,
) -> Dict[str, Any]:
    """
    Place a STOP_MARKET order via the Algo Order API.

    Since December 2025, Binance migrated all conditional order types
    (STOP_MARKET, TAKE_PROFIT_MARKET, etc.) to POST /fapi/v1/algoOrder.
    The old /fapi/v1/order endpoint returns -4120 for these types.

    Once the stop price is touched, a market order fires automatically.
    Useful for stop-loss protection on open positions.
    """
    logger.info(
        "Placing STOP_MARKET %s | symbol=%s qty=%s stopPrice=%s",
        side, symbol, quantity, stop_price,
    )
    try:
        response = client.place_algo_order(
            algoType="CONDITIONAL",
            symbol=symbol,
            side=side,
            type="STOP_MARKET",
            quantity=quantity,
            triggerPrice=stop_price,
        )
    except BinanceAPIError:
        logger.exception("STOP_MARKET order failed")
        raise

    logger.info(
        "STOP_MARKET order accepted | algoId=%s status=%s",
        response.get("algoId"), response.get("algoStatus"),
    )
    return response


def format_response(response: Dict[str, Any]) -> str:
    """Return a formatted string of the key order response fields."""

    # Algo orders (STOP_MARKET) use different field names than regular orders
    is_algo = "algoId" in response

    if is_algo:
        fields = [
            ("Algo ID",      response.get("algoId",       "N/A")),
            ("Symbol",       response.get("symbol",        "N/A")),
            ("Side",         response.get("side",          "N/A")),
            ("Type",         response.get("orderType",     "N/A")),
            ("Status",       response.get("algoStatus",    "N/A")),
            ("Quantity",     response.get("quantity",      "N/A")),
            ("Trigger Price",response.get("triggerPrice",  "N/A")),
            ("Working Type", response.get("workingType",   "N/A")),
            ("Update Time",  response.get("updateTime",    "N/A")),
        ]
    else:
        # avgPrice is only populated once the order is filled.
        # Show the actual value if available, otherwise mark it as pending.
        raw_avg = response.get("avgPrice", "0")
        try:
            avg_price = raw_avg if float(raw_avg) > 0 else "Pending fill"
        except (TypeError, ValueError):
            avg_price = raw_avg

        fields = [
            ("Order ID",     response.get("orderId",       "N/A")),
            ("Symbol",       response.get("symbol",        "N/A")),
            ("Side",         response.get("side",          "N/A")),
            ("Type",         response.get("type",          "N/A")),
            ("Status",       response.get("status",        "N/A")),
            ("Orig Qty",     response.get("origQty",       "N/A")),
            ("Executed Qty", response.get("executedQty",   "0")),
            ("Avg Price",    avg_price),
            ("Limit Price",  response.get("price",         "N/A")),
            ("Update Time",  response.get("updateTime",    "N/A")),
        ]

    sep = "─" * 50
    lines = ["", sep, "        ORDER RESPONSE", sep]
    for label, value in fields:
        lines.append(f"  {label:<14}: {value}")
    lines.append(sep)
    return "\n".join(lines)
