# Binance Futures Testnet Trading Bot

A Python CLI tool for placing orders on the Binance USDT-M Futures Testnet. Built with direct REST calls (no Binance SDK) using `requests`, structured across separate client/validation/order layers with proper logging throughout.

Supports two modes:
- **Direct CLI** — pass flags and place an order in one command
- **Interactive mode** — guided step-by-step prompts with menus and confirmation

---

## Project structure

```
trading_bot/
├── bot/
│   ├── __init__.py
│   ├── client.py          # REST client — signing, sessions, error handling
│   ├── orders.py          # order placement (market, limit, stop-market)
│   ├── validators.py      # input validation and custom exceptions
│   ├── logging_config.py  # shared logger setup
│   ├── cli.py             # direct CLI entry point (argparse)
│   └── interactive.py     # guided interactive mode
├── logs/
│   └── trading_20260524.log
├── .env.example
├── .gitignore
└── requirements.txt
```

---

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd trading_bot
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Get testnet API credentials

1. Go to [testnet.binancefuture.com](https://testnet.binancefuture.com) and register
2. Under **API Key**, generate a new key pair
3. Copy both the API Key and Secret Key (secret shown only once)

### 3. Configure credentials

```bash
cp .env.example .env
```

Edit `.env`:

```
BINANCE_API_KEY=your_key_here
BINANCE_API_SECRET=your_secret_here
```

---

## Usage

### Option A — Direct CLI (one command per order)

**Market order:**
```bash
python -m bot.cli --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
python -m bot.cli --symbol ETHUSDT --side SELL --type MARKET --quantity 0.05
```

**Limit order:**
```bash
python -m bot.cli --symbol BTCUSDT --side BUY --type LIMIT --quantity 0.01 --price 60000
python -m bot.cli --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.1 --price 3500 --tif IOC
```

**Stop-market order:**
```bash
python -m bot.cli --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 61000
```

### Option B — Interactive mode (guided prompts)

```bash
python -m bot.interactive
```

Walks you through each field one at a time with numbered menus, inline error messages, and a confirmation step before the order is sent. Useful when you want to double-check everything before submitting.

Example session:
```
====================================================
     Binance Futures Testnet -- Order Placer
====================================================

  Step 1 of 4 - Symbol
  Enter trading pair: (e.g. BTCUSDT)
  > BTCUSDT
  OK

  Step 2 of 4 - Side
  Choose order side:
    1.  BUY
    2.  SELL
  Enter number: 1
  OK: BUY

  Step 3 of 4 - Order type
  Choose order type:
    1.  MARKET      - execute immediately at best price
    2.  LIMIT       - set your own price, rest on the book
    3.  STOP_MARKET - trigger a market order at a stop price
  Enter number: 1
  OK: MARKET

  Step 4 of 4 - Parameters
  Quantity (base asset units): (e.g. 0.01)
  > 0.01
  OK

  --------------------------------------------------
  Confirm your order:
  --------------------------------------------------
  Symbol        : BTCUSDT
  Side          : BUY
  Type          : MARKET
  Quantity      : 0.01
  --------------------------------------------------

  Place this order? [y/n]: y

  Sending order...
  [SUCCESS] Order placed successfully.
```

---

## CLI flags reference

| Flag | Required | Description |
|------|----------|-------------|
| `--symbol` | yes | Trading pair e.g. `BTCUSDT` |
| `--side` | yes | `BUY` or `SELL` |
| `--type` | yes | `MARKET`, `LIMIT`, or `STOP_MARKET` |
| `--quantity` | yes | Order size in base asset units |
| `--price` | LIMIT only | Limit price |
| `--stop-price` | STOP_MARKET only | Stop trigger price |
| `--tif` | optional | `GTC` (default), `IOC`, or `FOK` |

---

## Logging

Each run appends to `logs/trading_YYYYMMDD.log`. The file captures DEBUG-level detail (full request params, raw API responses) while the console shows INFO and above only. Signatures are always redacted in log output.

---

## Notes and assumptions

- Hardcoded to testnet only (`https://testnet.binancefuture.com`) — no risk of hitting mainnet
- Credentials are read from `.env` via `python-dotenv`; `.env` is gitignored
- STOP_MARKET orders use the `/fapi/v1/algoOrder` endpoint (Binance migrated conditional orders away from `/fapi/v1/order` in late 2025 — the old endpoint returns `-4120`)
- Quantity precision is enforced by Binance per symbol. If you get a `LOT_SIZE` error, reduce decimal places on `--quantity` (e.g. `0.01` not `0.015` for BTCUSDT)
- For STOP_MARKET: stop price must be below current mark price for SELL, above for BUY — otherwise Binance returns `-2021`
- No balance or position checks before placing — intentionally kept out of scope
