# === BankNifty & CrudeOilM Auto-Trading Bot with Live Orders ===
# Version: Dual-Market + ATR SL + Telegram + Live Orders (Manual Crude Scrip)

import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
from ta.volatility import AverageTrueRange
from py5paisa import FivePaisaClient

# === 5paisa Credentials ===
cred = {
    "APP_NAME": "5P50343444",
    "APP_SOURCE": "18463",
    "USER_ID": "btaaKRf6JMF",
    "PASSWORD": "3FTxxolUrzI",
    "USER_KEY": "AjFXypM42L3Kaw13aAfcdBCfQP7hPJ2R",
    "ENCRYPTION_KEY": "LV2xRvG8MkRhLzSyGGgc2I0Agw2ITcSI"
}

client = FivePaisaClient(cred)

# === Telegram Settings ===
BOT_TOKEN = "7554184412:AAF3qH8ulWZKD4CfTluoVtXJsWkp9kzc330"
CHAT_ID = "588733419"
SEND_TELEGRAM = True

# === Logger ===
def log(msg):
    timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    print(f"{timestamp} {msg}")

def send_telegram(msg):
    if SEND_TELEGRAM:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": msg}
        try:
            requests.post(url, data=data)
        except Exception as e:
            print("Telegram Error:", e)

# === Instrument Config (Manual Crude ScripCode) ===
SYMBOLS = {
    "BANKNIFTY": {
        "ScripCode": 23257,
        "Exchange": "N",
        "ExchangeType": "C",
        "LotSize": 15,
        "MarketEnd": "15:30:00"
    },
    "CRUDEOILM": {
        "ScripCode": 247211,  # ✅ Update monthly with correct expiry contract
        "Exchange": "MCX",
        "ExchangeType": "D",
        "LotSize": 10,
        "MarketEnd": "23:30:00"
    }
}

# === Fetch OHLC Data ===
def fetch_candles(scrip_code, exchange, ex_type):
    try:
        to_date = datetime.now()
        from_date = to_date - timedelta(days=1)
        candles = client.historical_data(
            exchange, ex_type, scrip_code, "5m",
            from_date.strftime("%Y-%m-%d"),
            to_date.strftime("%Y-%m-%d")
        )
        if not candles or "candles" not in candles:
            log("[Error] No candle data received.")
            return pd.DataFrame()

        df = pd.DataFrame(
            candles["candles"],
            columns=["datetime", "open", "high", "low", "close", "volume"]
        )
        df["datetime"] = pd.to_datetime(df["datetime"])
        return df
    except Exception as e:
        log(f"[Error] Fetch candles failed: {e}")
        return pd.DataFrame()

# === Indicators ===
def calculate_atr(df, period=14, multiplier=1.5):
    atr = AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=period).average_true_range()
    df['atr'] = atr
    df['trail_sl'] = df['close'] - atr * multiplier
    return df

# === Live Order Placement ===
def place_order(scrip_code, qty, exchange, ex_type):
    try:
        order = client.place_order(
            OrderType="BUY",
            Exchange=exchange,
            ExchangeType=ex_type,
            ScripCode=scrip_code,
            Qty=qty,
            Price=0,
            IsIntraday=True,
            IsStopLossOrder=False,
            StopLossPrice=0,
            IsLimitOrder=False
        )
        log(f"Order Placed: {order}")
        send_telegram(f"🚀 LIVE ORDER PLACED for ScripCode: {scrip_code}\nQty: {qty}")
    except Exception as e:
        log(f"[Error] Live order failed: {e}")
        send_telegram(f"❌ Live order failed: {e}")

# === Main Bot Logic ===
def run_bot():
    now = datetime.now()

    for name, info in SYMBOLS.items():
        scrip_code = info["ScripCode"]
        lot_size = info["LotSize"]
        market_close = datetime.strptime(info["MarketEnd"], "%H:%M:%S").time()
        exchange = info["Exchange"]
        ex_type = info["ExchangeType"]

        if scrip_code == 0:
            log(f"[{name}] Skipped due to missing ScripCode")
            continue

        if now.time() > market_close:
            log(f"[{name}] Market Closed. Skipping...")
            continue

        log(f"[{name}] Bot Started")
        df = fetch_candles(scrip_code, exchange, ex_type)
        if df.empty:
            log(f"[{name}] No valid data. Skipping...")
            continue

        df = calculate_atr(df)
        latest = df.iloc[-1]
        entry = round(latest['close'], 2)
        sl = round(latest['trail_sl'], 2)

        log(f"[{name}] Entry: {entry}, SL: {sl}")
        send_telegram(f"✅ {name} SIGNAL\nEntry: {entry}\nSL: {sl} (ATR Based)")

        place_order(scrip_code, lot_size, exchange, ex_type)
        time.sleep(2)

        for i in range(2):
            sl += 3
            log(f"[{name}] Trailing SL to {sl}")
            send_telegram(f"🔄 {name} SL moved to {sl}")
            time.sleep(2)

        exit_price = sl + 5
        pnl = (exit_price - entry) * lot_size
        log(f"[{name}] Exited @ {exit_price}, PnL: ₹{round(pnl,2)}")
        send_telegram(f"💰 {name} EXIT\nExit: {exit_price}\nPnL: ₹{round(pnl,2)}")

if __name__ == "__main__":
    run_bot()
