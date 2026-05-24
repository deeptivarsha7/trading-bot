from typing import Optional


class ValidationError(Exception):
    """Raised when user-supplied parameters don't pass validation."""
    pass


def validate_symbol(symbol: str) -> str:
    symbol = symbol.strip().upper()
    if not symbol:
        raise ValidationError("Symbol cannot be empty. Example: BTCUSDT")
    if not symbol.isalnum():
        raise ValidationError(
            f"'{symbol}' doesn't look like a valid symbol. "
            "Expected something like BTCUSDT or ETHUSDT."
        )
    return symbol


def validate_side(side: str) -> str:
    side = side.strip().upper()
    if side not in ("BUY", "SELL"):
        raise ValidationError(f"Side must be BUY or SELL, got '{side}'.")
    return side


def validate_order_type(order_type: str) -> str:
    order_type = order_type.strip().upper()
    valid = ("MARKET", "LIMIT", "STOP_MARKET")
    if order_type not in valid:
        raise ValidationError(
            f"Order type must be one of {valid}, got '{order_type}'."
        )
    return order_type


def validate_quantity(raw: str) -> float:
    try:
        qty = float(raw)
    except (TypeError, ValueError):
        raise ValidationError(
            f"Quantity must be a number, got '{raw}'."
        )
    if qty <= 0:
        raise ValidationError(f"Quantity must be greater than zero, got {qty}.")
    return qty


def validate_price(raw: Optional[str], order_type: str) -> Optional[float]:
    """
    --price is required only for LIMIT orders.
    For MARKET/STOP_MARKET it's ignored even if supplied.
    """
    if order_type != "LIMIT":
        return None

    if raw is None:
        raise ValidationError("--price is required for LIMIT orders.")

    try:
        price = float(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"Price must be a number, got '{raw}'.")

    if price <= 0:
        raise ValidationError(f"Price must be greater than zero, got {price}.")

    return price


def validate_stop_price(raw: Optional[str], order_type: str) -> Optional[float]:
    """
    --stop-price is required only for STOP_MARKET orders.
    """
    if order_type != "STOP_MARKET":
        return None

    if raw is None:
        raise ValidationError("--stop-price is required for STOP_MARKET orders.")

    try:
        sp = float(raw)
    except (TypeError, ValueError):
        raise ValidationError(f"Stop price must be a number, got '{raw}'.")

    if sp <= 0:
        raise ValidationError(f"Stop price must be greater than zero, got {sp}.")

    return sp
