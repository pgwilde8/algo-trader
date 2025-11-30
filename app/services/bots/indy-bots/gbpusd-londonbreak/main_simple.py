import os
import time
import json
import traceback
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# ===============================================================
# Time parsing helper for OANDA timestamps
# ===============================================================
def parse_oanda_time(ts: str) -> datetime:
    """
    OANDA can return nanosecond precision timestamps that datetime.fromisoformat
    cannot handle. This trims to microseconds and keeps the timezone.
    """
    ts = ts.replace("Z", "+00:00")

    tz = ""
    main = ts
    for idx in range(len(ts)):
        if ts[idx] in "+-" and "T" in ts[:idx]:
            main = ts[:idx]
            tz = ts[idx:]
            break

    if "." in main:
        prefix, frac_rest = main.split(".", 1)
        frac = frac_rest[:6].ljust(6, "0")
        main = f"{prefix}.{frac}"
    else:
        main = f"{main}.000000"

    return datetime.fromisoformat(f"{main}{tz}")

import requests
from oandapyV20 import API
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.positions as positions
import oandapyV20.endpoints.trades as trades

# Ensure the repo root is in the import path so we can access shared services
REPO_ROOT = "/home/myalgo/algo-trader"
if REPO_ROOT not in sys.path:
    sys.path.append(REPO_ROOT)

from gbpusd_london_breakout import (
    load_strategy_config,
    LondonBreakoutStrategy,
)

from app.utils.simple_news_avoidance import simple_news_avoidance


# ===============================================================
# Load ENV from .env.practice for practice trading
# ===============================================================
from dotenv import load_dotenv
load_dotenv("/home/myalgo/algo-trader/.env.practice", override=True)  # Load practice account

OANDA_API_KEY = os.getenv("OANDA_API_KEY") or os.getenv("OANDA_API_TOKEN")
# Use practice account 101-001-26778453-001
OANDA_ACCOUNT = os.getenv("OANDA_ACCOUNT_ID") or "101-001-26778453-001"
OANDA_ENV = "practice"  # Practice mode

api = API(
    access_token=OANDA_API_KEY,
    environment=OANDA_ENV
)


# ===============================================================
# Logger helper
# ===============================================================
def log(msg: str):
    # Convert UTC to EST for logging
    now_utc = datetime.now(ZoneInfo("UTC"))
    now_est = now_utc.astimezone(ZoneInfo("America/New_York"))
    now_str = now_est.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now_str}] {msg}", flush=True)


# ===============================================================
# Utility: Get Latest M1 Candle
# ===============================================================
def get_latest_candle(instrument: str):
    params = {
        "granularity": "M1",
        "count": 2  # last two candles
    }
    r = instruments.InstrumentsCandles(instrument=instrument, params=params)
    api.request(r)

    candles = r.response["candles"]
    c = candles[-1]

    candle = {
        "time": parse_oanda_time(c["time"]),
        "open": float(c["mid"]["o"]),
        "high": float(c["mid"]["h"]),
        "low": float(c["mid"]["l"]),
        "close": float(c["mid"]["c"]),
        "volume": c.get("volume", 0)
    }
    return candle


# ===============================================================
# Utility: Get current spread
# ===============================================================
def get_spread_pips(instrument: str):
    base_url = "https://api-fxtrade.oanda.com/v3" if OANDA_ENV == "live" else "https://api-fxpractice.oanda.com/v3"
    url = f"{base_url}/accounts/{OANDA_ACCOUNT}/pricing?instruments={instrument}"
    headers = {"Authorization": f"Bearer {OANDA_API_KEY}"}

    r = requests.get(url, headers=headers)
    data = r.json()

    bids = float(data["prices"][0]["bids"][0]["price"])
    asks = float(data["prices"][0]["asks"][0]["price"])
    spread = asks - bids

    return spread / 0.0001  # convert to pips


# ===============================================================
# Check if position exists
# ===============================================================
def has_open_position(instrument: str) -> bool:
    """Check if there's an open position for the instrument"""
    try:
        r = positions.PositionList(accountID=OANDA_ACCOUNT)
        api.request(r)
        all_positions = r.response.get("positions", [])
        for pos in all_positions:
            if pos.get("instrument") == instrument:
                long_units = pos.get("long", {}).get("units", "0")
                short_units = pos.get("short", {}).get("units", "0")
                if long_units != "0" or short_units != "0":
                    return True
        return False
    except Exception as e:
        log(f"Error checking position: {e}")
        return False


# ===============================================================
# Position handling
# ===============================================================
def close_trade(instrument: str):
    """Close trade only if position actually exists"""
    if not has_open_position(instrument):
        log("⚠️ No open position to close (position may have been closed by SL/TP)")
        return
    
    log("Closing trade...")
    try:
        r = positions.PositionClose(
            accountID=OANDA_ACCOUNT,
            instrument=instrument,
            data={"longUnits": "ALL", "shortUnits": "ALL"}
        )
        api.request(r)
        log("✅ Trade closed.")
    except Exception as e:
        # Handle the case where position doesn't exist (might have been closed between check and close)
        if "CLOSEOUT_POSITION_DOESNT_EXIST" in str(e) or "does not exist" in str(e).lower():
            log("⚠️ Position already closed (likely by SL/TP)")
        else:
            log(f"❌ Error closing trade: {e}")
            raise


# ===============================================================
# Place market order
# ===============================================================
def place_market_order(instrument, units, sl_price, tp_price):
    log(f"Placing order: units={units}, SL={sl_price:.5f}, TP={tp_price:.5f}")

    order_data = {
        "order": {
            "units": str(units),
            "instrument": instrument,
            "timeInForce": "FOK",
            "type": "MARKET",
            "positionFill": "DEFAULT",
            "stopLossOnFill": {"price": f"{sl_price:.5f}"},
            "takeProfitOnFill": {"price": f"{tp_price:.5f}"}
        }
    }

    r = orders.OrderCreate(accountID=OANDA_ACCOUNT, data=order_data)
    response = api.request(r)

    log(f"Order response: {response}")
    return response


# ===============================================================
# Position Size Calculator
# ===============================================================
def calculate_position_size(balance, entry, sl, risk_pct):
    risk = balance * (risk_pct / 100)
    sl_pips = abs(entry - sl) / 0.0001

    if sl_pips == 0:
        return 0

    dollar_per_pip = risk / sl_pips
    units = int(dollar_per_pip / 0.0001)  # pip value for GBPUSD

    return units


# ===============================================================
# Fetch account balance
# ===============================================================
def get_balance():
    from oandapyV20.endpoints.accounts import AccountDetails
    r = AccountDetails(accountID=OANDA_ACCOUNT)
    api.request(r)
    return float(r.response["account"]["balance"])


# ===============================================================
# Get open trades for an instrument
# ===============================================================
def get_open_trades(instrument: str):
    """Get all open trades for the specified instrument"""
    try:
        r = trades.OpenTrades(accountID=OANDA_ACCOUNT)
        api.request(r)
        all_trades = r.response.get("trades", [])
        # Filter by instrument
        instrument_trades = [t for t in all_trades if t.get("instrument") == instrument]
        return instrument_trades
    except Exception as e:
        log(f"Error getting open trades: {e}")
        return []


# ===============================================================
# Update stop loss for a trade
# ===============================================================
def update_stop_loss(trade_id: str, sl_price: float):
    """Update the stop loss order for a specific trade"""
    try:
        base_url = "https://api-fxtrade.oanda.com/v3" if OANDA_ENV == "live" else "https://api-fxpractice.oanda.com/v3"
        url = f"{base_url}/accounts/{OANDA_ACCOUNT}/trades/{trade_id}/orders"
        headers = {
            "Authorization": f"Bearer {OANDA_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "stopLoss": {
                "price": f"{sl_price:.5f}",
                "timeInForce": "GTC"
            }
        }
        response = requests.put(url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        log(f"✅ Stop loss updated for trade {trade_id} to {sl_price:.5f}")
        return True
    except Exception as e:
        log(f"❌ Error updating stop loss for trade {trade_id}: {e}")
        return False


# ===============================================================
# Main loop
# ===============================================================
def run_bot():
    log("=" * 70)
    if OANDA_ENV == "live":
        log("⚠️  LIVE TRADING MODE - REAL MONEY AT RISK ⚠️")
        log(f"Account: {OANDA_ACCOUNT}")
        log("Make sure you have tested on practice account first!")
        log("=" * 70)
    log(f"Starting GBPUSD London Breakout Bot... (Mode: {OANDA_ENV})")

    # Load raw config for risk_management
    with open("config.json", "r") as f:
        raw_config = json.load(f)
    
    cfg = load_strategy_config("config.json")
    strat = LondonBreakoutStrategy(cfg, logger=None, news_avoidance=simple_news_avoidance)

    instrument = cfg.asset_pair

    while True:
        try:
            candle = get_latest_candle(instrument)
            spread_pips = get_spread_pips(instrument)

            action = strat.on_candle(candle, spread_pips)

            if action:
                if action["action"] == "ENTER":
                    balance = get_balance()
                    # Safely get risk percentage from config
                    risk_pct = raw_config.get("risk_management", {}).get("risk_percentage", 0.5)
                    units = calculate_position_size(
                        balance,
                        action["entry_price"],
                        action["sl_price"],
                        risk_pct
                    )

                    if units < 100:
                        log("UNITS TOO SMALL, SKIPPING TRADE.")
                        continue

                    response = place_market_order(
                        instrument,
                        units if action["direction"] == "long" else -units,
                        action["sl_price"],
                        action["tp_price"]
                    )
                    
                    # Save real trade IDs from OANDA response
                    if response and "orderFillTransaction" in response:
                        order_fill = response["orderFillTransaction"]
                        if "tradesOpened" in order_fill:
                            trade_ids = [t["tradeID"] for t in order_fill["tradesOpened"]]
                            strat.position.trade_ids = trade_ids
                            log(f"✅ Saved trade IDs: {trade_ids}")
                        else:
                            log("⚠️ No tradesOpened in response, trade IDs not saved")

                elif action["action"] == "EXIT":
                    close_trade(instrument)

                elif action["action"] == "UPDATE_SL":
                    # Update stop loss for all trade IDs saved in position state
                    if strat.position.trade_ids:
                        for trade_id in strat.position.trade_ids:
                            update_stop_loss(trade_id, action["sl_price"])
                    else:
                        # Fallback: Get open trades if trade_ids not available
                        open_trades = get_open_trades(instrument)
                        if open_trades:
                            # Update stop loss for all open trades
                            for trade in open_trades:
                                update_stop_loss(trade["id"], action["sl_price"])
                            # Also save the trade IDs for future updates
                            strat.position.trade_ids = [t["id"] for t in open_trades]
                        else:
                            log("⚠️ No open trades found to update stop loss")

        except Exception:
            log("ERROR:")
            log(traceback.format_exc())

        time.sleep(15)  # check every 15 seconds


if __name__ == "__main__":
    run_bot()
