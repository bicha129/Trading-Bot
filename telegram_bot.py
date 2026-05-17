import yfinance as yf
import pandas as pd
import requests
import time
import os

# =====================================
# TELEGRAM SETTINGS
# =====================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# =====================================
# ASSET LISTS
# =====================================

forex_pairs = [
    "GBPUSD=X",
    "EURUSD=X",
    "JPY=X",
    "AUDUSD=X",
    "USDCAD=X"
]

stocks = [
    "AAPL",
    "TSLA",
    "NVDA",
    "MSFT",
    "AMZN"
]

indices = [
    "^GSPC",
    "^NDX",
    "^DJI"
]

symbols = forex_pairs + stocks + indices

# =====================================
# SETTINGS
# =====================================

lower_timeframe = "15m"
higher_timeframe = "4h"

hma_length = 55
atr_length = 14
risk_reward = 3

# =====================================
# SIGNAL MEMORY
# =====================================

last_signals = {}

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

        for symbol in symbols:

            print(f"Checking {symbol}...")

            # =====================================
            # HIGHER TIMEFRAME DATA
            # =====================================

            htf_data = yf.download(
                symbol,
                interval=higher_timeframe,
                period="30d",
                progress=False
            )

            htf = htf_data.copy()

            if htf.empty:
                print(f"No HTF data for {symbol}")
                continue

            htf.columns = htf.columns.get_level_values(0)

            # =====================================
            # LOWER TIMEFRAME DATA
            # =====================================

            data = yf.download(
                symbol,
                interval=lower_timeframe,
                period="5d",
                progress=False
            )

            df = data.copy()

            if df.empty:
                print(f"No LTF data for {symbol}")
                continue

            df.columns = df.columns.get_level_values(0)

            # =====================================
            # INDICATORS
            # =====================================

            df['HMA'] = HMA(df['Close'], hma_length)
            htf['HMA'] = HMA(htf['Close'], hma_length)

            df['ATR'] = ATR(df, atr_length)

            # =====================================
            # TREND DIRECTION
            # =====================================

            df['Bullish'] = df['HMA'] > df['HMA'].shift(1)
            htf['Bullish'] = htf['HMA'] > htf['HMA'].shift(1)

            # =====================================
            # SIGNAL GENERATION
            # =====================================

            df['BuySignal'] = (
                (df['Bullish'] == True) &
                (df['Bullish'].shift(1) == False)
            )

            df['SellSignal'] = (
                (df['Bullish'] == False) &
                (df['Bullish'].shift(1) == True)
            )

            latest = df.iloc[-1].to_dict()
            htf_latest = htf.iloc[-1].to_dict()

            message = None
            current_signal = None

            # =====================================
            # BUY SIGNAL
            # =====================================

            if latest['BuySignal'] and htf_latest['Bullish']:

                current_signal = 'BUY'

                entry = latest['Close']
                sl = entry - latest['ATR']

                risk = entry - sl

                tp = entry + (risk * risk_reward)

                message = f"""
BUY SIGNAL ✅

Asset: {symbol}
Timeframe: {lower_timeframe}
Higher Trend: Bullish

Entry: {round(entry, 5)}
Stop Loss: {round(sl, 5)}
Take Profit: {round(tp, 5)}

Risk Reward: 1:{risk_reward}
HMA Length: {hma_length}
"""

            # =====================================
            # SELL SIGNAL
            # =====================================

            if latest['SellSignal'] and not htf_latest['Bullish']:

                current_signal = 'SELL'

                entry = latest['Close']
                sl = entry + latest['ATR']

                risk = sl - entry

                tp = entry - (risk * risk_reward)

                message = f"""
SELL SIGNAL 🔻

Asset: {symbol}
Timeframe: {lower_timeframe}
Higher Trend: Bearish

Entry: {round(entry, 5)}
Stop Loss: {round(sl, 5)}
Take Profit: {round(tp, 5)}

Risk Reward: 1:{risk_reward}
HMA Length: {hma_length}
"""

            # =====================================
            # TELEGRAM ALERT
            # =====================================

            if message and last_signals.get(symbol) != current_signal:

                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

                payload = {
                    "chat_id": CHAT_ID,
                    "text": message
                }

                response = requests.post(url, data=payload)

                print(message)

                last_signals[symbol] = current_signal

            else:

                print(f"No new signal for {symbol}")

    except Exception as e:

        print("Error:", e)

    # =====================================
    # WAIT BEFORE NEXT SCAN
    # =====================================

    print("Waiting 60 seconds...")

    time.sleep(60)