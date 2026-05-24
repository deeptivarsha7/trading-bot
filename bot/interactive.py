#!/usr/bin/env python3
"""
interactive.py — guided interactive mode for the trading bot.

Walks the user through placing an order step by step with menus,
inline validation messages, and a confirmation prompt before sending.

Run with:
    python -m bot.interactive
"""

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
from .validators import ValidationError, validate_price, validate_quantity, validate_stop_price

load_dotenv()
logger = setup_logger()

# ── Minimal colour helpers (no external deps) ────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def _green(t):  return f"{GREEN}{t}{RESET}"
def _red(t):    return f"{RED}{t}{RESET}"
def _yellow(t): return f"{YELLOW}{t}{RESET}"
def _cyan(t):   return f"{CYAN}{t}{RESET}"
def _bold(t):   return f"{BOLD}{t}{RESET}"


def _header():
    sep = "=" * 52
    print(f"\n{sep}")
    print("     Binance Futures Testnet -- Order Placer")
    print(f"{sep}\n")


def _menu(prompt: str, options: list) -> str:
    """Numbered menu — keeps re-prompting until a valid choice is made."""
    print(f"  {prompt}")
    for i, opt in enumerate(options, 1):
        print(f"    {i}.  {opt}")
    while True:
        raw = input("  Enter number: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            chosen = options[int(raw) - 1]
            print(f"  OK: {chosen}\n")
            return chosen
        print(f"  Invalid. Enter a number between 1 and {len(options)}.")


def _ask(prompt: str, validator=None, example: str = "") -> str:
    """Free-text prompt with optional validation. Re-prompts on failure."""
    hint = f" (e.g. {example})" if example else ""
    print(f"  {prompt}{hint}")
    while True:
        raw = input("  > ").strip()
        if not raw:
            print("  Cannot be empty. Please try again.")
            continue
        if validator:
            try:
                result = validator(raw)
                print("  OK\n")
                return result
            except (ValidationError, ValueError) as exc:
                print(f"  Error: {exc}  Please try again.")
        else:
            print("  OK\n")
            return raw


def _confirm(symbol, side, order_type, quantity, price=None, stop_price=None, tif="GTC") -> bool:
    """Shows a summary and waits for y/n confirmation."""
    sep = "-" * 50
    print(f"\n{sep}")
    print("  Confirm your order:")
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
    while True:
        ans = input("\n  Place this order? [y/n]: ").strip().lower()
        if ans == "y":
            return True
        if ans == "n":
            return False
        print("  Please enter y or n.")


def main():
    _header()

    api_key    = os.getenv("BINANCE_API_KEY", "").strip()
    api_secret = os.getenv("BINANCE_API_SECRET", "").strip()
    if not api_key or not api_secret:
        print(
            "  [ERROR] BINANCE_API_KEY and BINANCE_API_SECRET are not set.\n"
            "  Copy .env.example to .env and fill them in."
        )
        sys.exit(1)

    client = BinanceClient(api_key=api_key, api_secret=api_secret)

    while True:
        # Step 1: Symbol
        print("  Step 1 of 4 - Symbol")
        symbol = _ask("Enter trading pair:", example="BTCUSDT").upper().strip()
        if not symbol.isalnum():
            print("  Invalid symbol. Use something like BTCUSDT.\n")
            continue

        # Step 2: Side
        print("  Step 2 of 4 - Side")
        side = _menu("Choose order side:", ["BUY", "SELL"])

        # Step 3: Order type
        print("  Step 3 of 4 - Order type")
        order_type_choice = _menu(
            "Choose order type:",
            [
                "MARKET      - execute immediately at best price",
                "LIMIT       - set your own price, rest on the book",
                "STOP_MARKET - trigger a market order at a stop price",
            ],
        )
        order_type = order_type_choice.split()[0]

        # Step 4: Parameters
        print("  Step 4 of 4 - Parameters")
        quantity = _ask(
            "Quantity (base asset units):",
            validator=lambda v: validate_quantity(v),
            example="0.01",
        )

        price      = None
        stop_price = None
        tif        = "GTC"

        if order_type == "LIMIT":
            price = _ask(
                "Limit price (USDT):",
                validator=lambda v: validate_price(v, "LIMIT"),
                example="75000",
            )
            tif = _menu("Time-in-force:", ["GTC", "IOC", "FOK"])

        elif order_type == "STOP_MARKET":
            stop_price = _ask(
                "Stop trigger price (USDT):",
                validator=lambda v: validate_stop_price(v, "STOP_MARKET"),
                example="61000",
            )

        # Confirmation
        confirmed = _confirm(symbol, side, order_type, quantity, price, stop_price, tif)
        if not confirmed:
            print("\n  Order cancelled.\n")
            again = input("  Place another order? [y/n]: ").strip().lower()
            if again != "y":
                print("\n  Exiting. Goodbye.\n")
                break
            print()
            continue

        # Place order
        print("\n  Sending order...")
        try:
            if order_type == "MARKET":
                response = place_market_order(client, symbol, side, float(quantity))
            elif order_type == "LIMIT":
                response = place_limit_order(
                    client, symbol, side, float(quantity), float(price), tif
                )
            else:
                response = place_stop_market_order(
                    client, symbol, side, float(quantity), float(stop_price)
                )

        except BinanceAPIError as exc:
            logger.error("Order rejected: %s", exc)
            print(f"\n  [FAILED] {exc}\n")
        except Exception as exc:
            logger.exception("Unexpected error")
            print(f"\n  [FAILED] Unexpected error: {exc}\n")
        else:
            print(format_response(response))
            print("\n  [SUCCESS] Order placed successfully.\n")
            order_id = response.get("algoId") or response.get("orderId")
            status   = response.get("algoStatus") or response.get("status")
            logger.info("Done | orderId=%s status=%s", order_id, status)

        again = input("  Place another order? [y/n]: ").strip().lower()
        if again != "y":
            print("\n  Exiting. Goodbye.\n")
            break
        print()


if __name__ == "__main__":
    main()
