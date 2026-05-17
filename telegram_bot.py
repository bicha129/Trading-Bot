import yfinance as yf
import pandas as pd
import requests
import time

# =====================================
# TELEGRAM SETTINGS
# =====================================

import os

BOT_TOKEN = os.getenv("8781841318:AAFB8-k5C9KerLcb7q3XX2BsSGZ_C_ueO_4")
CHAT_ID = os.getenv("8613300513")

# =====================================
# SETTINGS
# =====================================

symbol = "GBPUSD=X"
timeframe = "15m"
hma_length = 55
atr_length = 14
risk_reward = 3

# =====================================
# MEMORY
# =====================================

last_signal = None

# =====================================
# WMA FUNCTION
# =====================================

def WMA(series, period):

    weights = range(1, period + 1)

    return series.rolling(period).apply(
        lambda prices: sum(prices * weights) / sum(weights),
        raw=True
    )

# =====================================
# HMA FUNCTION
# =====================================

def HMA(series, period):

    half_length = int(period / 2)
    sqrt_length = int(period ** 0.5)

    wma1 = WMA(series, half_length)
    wma2 = WMA(series, period)

    raw_hma = 2 * wma1 - wma2

    return WMA(raw_hma, sqrt_length)

# =====================================
# ATR FUNCTION
# =====================================

def ATR(df, period):

    high_low = df['High'] - df['Low']
    high_close = abs(df['High'] - df['Close'].shift())
    low_close = abs(df['Low'] - df['Close'].shift())

    ranges = pd.concat([
        high_low,
        high_close,
        low_close
    ], axis=1)

    true_range = ranges.max(axis=1)

    atr = true_range.rolling(period).mean()

    return atr

# =====================================
# MAIN LOOP
# =====================================

while True:

    try:

        # DOWNLOAD DATA

        data = yf.download(
            symbol,
            interval=timeframe,
            period="5d",
            progress=False
        )

        df = data.copy()

        # FIX MULTI INDEX

        df.columns = df.columns.get_level_values(0)

        # =====================================
        # INDICATORS
        # =====================================

        df['HMA'] = HMA(df['Close'], hma_length)
        df['ATR'] = ATR(df, atr_length)

        # =====================================
        # SIGNALS
        # =====================================

        df['Bullish'] = df['HMA'] > df['HMA'].shift(1)

        df['BuySignal'] = (
            (df['Bullish'] == True) &
            (df['Bullish'].shift(1) == False)
        )

        df['SellSignal'] = (
            (df['Bullish'] == False) &
            (df['Bullish'].shift(1) == True)
        )

        latest = df.iloc[-1].to_dict()

        message = None
        current_signal = None

        # =====================================
        # BUY SIGNAL
        # =====================================

        if latest['BuySignal']:

            current_signal = 'BUY'

            entry = latest['Close']
            sl = entry - latest['ATR']
            risk = entry - sl
            tp = entry + (risk * risk_reward)

            message = f"""
BUY SIGNAL ✅

Pair: GBP/USD
Timeframe: 15m

Entry: {round(entry, 5)}
Stop Loss: {round(sl, 5)}
Take Profit: {round(tp, 5)}

Risk Reward: 1:{risk_reward}
Trend: Bullish
HMA Length: {hma_length}
"""

        # =====================================
        # SELL SIGNAL
        # =====================================

        if latest['SellSignal']:

            current_signal = 'SELL'

            entry = latest['Close']
            sl = entry + latest['ATR']
            risk = sl - entry
            tp = entry - (risk * risk_reward)

            message = f"""
SELL SIGNAL 🔻

Pair: GBP/USD
Timeframe: 15m

Entry: {round(entry, 5)}
Stop Loss: {round(sl, 5)}
Take Profit: {round(tp, 5)}

Risk Reward: 1:{risk_reward}
Trend: Bearish
HMA Length: {hma_length}
"""

        # =====================================
        # SEND TELEGRAM ALERT
        # =====================================

        if message and current_signal != last_signal:

            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

            payload = {
                "chat_id": CHAT_ID,
                "text": message
            }

            response = requests.post(url, data=payload)

            print(message)

            last_signal = current_signal

        else:

            print("No new signal.")

    except Exception as e:

        print("Error:", e)

    # WAIT 60 SECONDS

    time.sleep(60)
    
