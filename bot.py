import requests
import pandas as pd
import time
import os

TOKEN = os.environ.get("TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"


# ======================
# TELEGRAM
# ======================

def send_message(text):
    url = f"{BASE_URL}/sendMessage"

    try:
        requests.post(
            url,
            data={
                "chat_id": CHAT_ID,
                "text": text
            }
        )
    except Exception as e:
        print(f"Telegram error: {e}")

# ======================
# TOP 50 USDT (MEXC)
# ======================

def get_top_300_usdt():
    url = "https://api.mexc.com/api/v3/ticker/24hr"

    min_volume = 30000

    data = requests.get(url).json()

    usdt_pairs = [
        x for x in data
        if x["symbol"].endswith("USDT")
    ]

    sorted_pairs = sorted(
        usdt_pairs,
        key=lambda x: float(x["quoteVolume"]),
        reverse=True
    )

    filtered_pairs = [
        x for x in sorted_pairs
        if float(x["quoteVolume"]) > min_volume
    ]

    return [x["symbol"] for x in filtered_pairs[:300]]


# ======================
# CANDLES
# ======================

def get_klines(symbol, interval="1d", limit=100):
    url = "https://api.mexc.com/api/v3/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    response = requests.get(url, params=params)
    data = response.json()

    # 🔥 DEBUG se API cambia formato
    if not isinstance(data, list):
        raise Exception(f"API ERROR {symbol}: {data}")

    # 🔥 prendiamo solo le prime 6 colonne utili (safe mode)
    cleaned = []
    for row in data:
        if isinstance(row, list) and len(row) >= 6:
            cleaned.append(row[:6])

    if len(cleaned) == 0:
        raise Exception(f"No valid candle data for {symbol}")

    df = pd.DataFrame(
        cleaned,
        columns=["open_time", "open", "high", "low", "close", "volume"]
    )

    df["close"] = df["close"].astype(float)

    return df


# ======================
# INDICATORS
# ======================

def calculate_ema(df, period=20):
    return df["close"].ewm(
        span=period,
        adjust=False
    ).mean()


def calculate_macd(df):
    ema12 = df["close"].ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = df["close"].ewm(
        span=26,
        adjust=False
    ).mean()

    macd = ema12 - ema26
    signal = macd.ewm(
        span=9,
        adjust=False
    ).mean()

    return macd, signal


# ======================
# SIGNAL LOGIC
# ======================

def check_signal(df):
    df["ema20"] = calculate_ema(df)

    macd, signal = calculate_macd(df)

    df["macd"] = macd
    df["signal"] = signal

    prev = df.iloc[-2]
    last = df.iloc[-1]

    ema_cross = (
        prev["close"] < prev["ema20"]
        and
        last["close"] > last["ema20"]
    )

    macd_cross = (
        prev["macd"] < prev["signal"]
        and
        last["macd"] > last["signal"]
    )

    return ema_cross and macd_cross


# ======================
# MAIN SCAN
# ======================

def run_scan():
    symbols = get_top_300_usdt()

    signals = []

    for symbol in symbols:
        try:
            df = get_klines(symbol)

            if check_signal(df):
                signals.append(symbol)

        except Exception as e:
            print(f"Error {symbol}: {e}")

    return signals


if __name__ == "__main__":
    print("Scanning market...")

    results = run_scan()

    if results:
        send_message(
            "🚨 Segnali trovati:\n" + "\n".join(results)
        )
        print(f"Signals found: {results}")
    else:
        print("No signals found - silent run")




