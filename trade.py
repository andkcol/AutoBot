import requests
import pandas as pd
import time

# --- Configuration ---
API_KEY = "TXAYZZLDCPD0Q9XS"
TICKER = "AAPL"
INTERVAL = "60min"
CSV_OUTPUT = f"{TICKER}_strategy_output.csv"
AV_URL = "https://www.alphavantage.co/query"

# --- Fetch 1-Hour Data ---
def fetch_data():
    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": TICKER,
        "interval": INTERVAL,
        "outputsize": "compact",
        "apikey": API_KEY
    }

    response = requests.get(AV_URL, params=params)
    data = response.json()

    if "Time Series (60min)" not in data:
        print("API Error:", data)
        return None

    df = pd.DataFrame.from_dict(data["Time Series (60min)"], orient='index')
    df.columns = ["open", "high", "low", "close", "volume"]
    df = df.astype(float)
    df.index = pd.to_datetime(df.index)
    df.sort_index(inplace=True)
    return df

# --- Indicators ---
def add_indicators(df):
    df["EMA_5"] = df["close"].ewm(span=5).mean()
    df["EMA_20"] = df["close"].ewm(span=20).mean()

    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(window=14).mean()
    loss = -delta.clip(upper=0).rolling(window=14).mean()
    rs = gain / loss
    df["RSI"] = 100 - (100 / (1 + rs))

    return df

# --- Signal Logic ---
def generate_signals(df):
    df["Signal"] = 0
    buy = (df["EMA_5"] > df["EMA_20"]) & (df["RSI"] > 40)
    sell = (df["EMA_5"] < df["EMA_20"]) | (df["RSI"] > 70)

    df.loc[buy, "Signal"] = 1
    df.loc[sell, "Signal"] = -1
    return df

# --- Main Execution ---
def main():
    df = fetch_data()
    if df is None:
        return

    df = add_indicators(df)
    df = generate_signals(df)

    latest = df.iloc[-1]
    print(f"--- Latest Signal for {TICKER} ---")
    print(f"Time: {latest.name}")
    print(f"Close: {latest['close']:.2f}")
    print(f"EMA_5: {latest['EMA_5']:.2f}, EMA_20: {latest['EMA_20']:.2f}")
    print(f"RSI: {latest['RSI']:.2f}")
    print(f"Signal: {'BUY' if latest['Signal'] == 1 else 'SELL' if latest['Signal'] == -1 else 'HOLD'}")

    df.to_csv(CSV_OUTPUT)
    print(f"Saved output to {CSV_OUTPUT}")

if __name__ == "__main__":
    main()
