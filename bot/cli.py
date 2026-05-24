#!/usr/bin/env python3
"""
Entry point for the Binance Futures Testnet trading bot.

Usage:
    python -m bot.cli --symbol BTCUSDT --side BUY  --type MARKET      --quantity 0.01
    python -m bot.cli --symbol ETHUSDT --side SELL --type LIMIT        --quantity 0.1  --price 3500
    python -m bot.cli --symbol BTCUSDT --side SELL --type STOP_MARKET  --quantity 0.01 --stop-price 61000

For a guided interactive mode:
    python -m bot.interactive
"""

import argparse
import os
import sys

from dotenv import load_dotenv

from .client import BinanceAPIError, BinanceClient
from .logging_config import setup_logger
from .orders import (
    format_response,
    place_limit_order,
    place_market_order,
    place_stop_market_order,
)
from .validators import (
    ValidationError,
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_stop_price,
    validate_symbol,
)

load_dotenv()
logger = setup_logger()


# --------------------------------------------------------------------------- #
# CLI definition                                                               #
# --------------------------------------------------------------------------- #

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Place orders on the Binance Futures Testnet (USDT-M).",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=(
            "Examples:\n"
            "  Market buy:\n"
            "    python -m bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01\n\n"
            "  Limit sell:\n"
            "    python -m bot.cli --symbol ETHUSDT --side SELL --type LIMIT "
            "--quantity 0.1 --price 3500\n\n"
            "  Stop-market sell (stop-loss):\n"
            "    python -m bot.cli --symbol BTCUSDT --side SELL --type STOP_MARKET "
            "--quantity 0.01 --stop-price 61000\n\n"
            "  Interactive guided mode:\n"
            "    python -m bot.interactive\n"
        ),
    )

    parser.add_argument("--symbol",     required=True,
                        help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side",       required=True, choices=["BUY", "SELL"],
                        help="BUY or SELL")
    parser.add_argument("--type",       required=True, dest="order_type",
                        choices=["MARKET", "LIMIT", "STOP_MARKET"],
                        help="Order type")
    parser.add_argument("--quantity",   required=True,
                        help="Order size in base-asset units")
    parser.add_argument("--price",      default=None,
                        help="Limit price (required for LIMIT orders)")
    parser.add_argument("--stop-price", dest="stop_price", default=None,
                        help="Stop trigger price (required for STOP_MARKET orders)")
    parser.add_argument("--tif",        dest="time_in_force", default="GTC",
                        choices=["GTC", "IOC", "FOK"],
                        help="Time-in-force for LIMIT orders (default: GTC)")
    return parser


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _print_request_summary(
    symbol, side, order_type, quantity,
    price=None, stop_price=None, tif="GTC",
):
    sep = "─" * 50
    print(f"\n{sep}")
    print("         ORDER REQUEST")
    print(sep)
    print(f"  {'Symbol':<14}: {symbol}")
    print(f"  {'Side':<14}: {side}")
    print(f"  {'Type':<14}: {order_type}")
    print(f"  {'Quantity':<14}: {quantity}")
    if price is not None:
        print(f"  {'Price':<14}: {price}")
    if stop_price is not None:
        print(f"  {'Stop Price':<14}: {stop_price}")
    if order_type == "LIMIT":
        print(f"  {'Time In Force':<14}: {tif}")
    print(sep)


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Validate inputs
    try:
        symbol     = validate_symbol(args.symbol)
        side       = validate_side(args.side)
        order_type = validate_order_type(args.order_type)
        quantity   = validate_quantity(args.quantity)
        price      = validate_price(args.price, order_type)
        stop_price = validate_stop_price(args.stop_price, order_type)
    except ValidationError as exc:
        logger.error("Validation error: %s", exc)
        print(f"\n  [ERROR] {exc}\n")
        sys.exit(1)

    # Load credentials from .env
    api_key    = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()

    if not api_key or not api_secret:
        msg = (
            "BINANCE_API_KEY and BINANCE_API_SECRET are not set. "
            "Copy .env.example to .env and fill them in."
        )
        logger.error(msg)
        print(f"\n  [ERROR] {msg}\n")
        sys.exit(1)

    _print_request_summary(
        symbol, side, order_type, quantity,
        price, stop_price, args.time_in_force,
    )

    client = BinanceClient(api_key=api_key, api_secret=api_secret)

    try:
        if order_type == "MARKET":
            response = place_market_order(client, symbol, side, quantity)
        elif order_type == "LIMIT":
            response = place_limit_order(
                client, symbol, side, quantity, price, args.time_in_force
            )
        else:  # STOP_MARKET
            response = place_stop_market_order(client, symbol, side, quantity, stop_price)

    except BinanceAPIError as exc:
        logger.error("Order rejected: %s", exc)
        print(f"\n  [FAILED] {exc}\n")
        sys.exit(1)
    except Exception as exc:
        logger.exception("Unexpected error")
        print(f"\n  [FAILED] Unexpected error: {exc}\n")
        sys.exit(1)

    print(format_response(response))
    print("\n  [SUCCESS] Order placed.\n")

    # Algo orders (STOP_MARKET) use algoId/algoStatus; regular orders use orderId/status
    order_id = response.get("algoId") or response.get("orderId")
    status   = response.get("algoStatus") or response.get("status")
    logger.info("Done | orderId=%s status=%s", order_id, status)


if __name__ == "__main__":
    main()
