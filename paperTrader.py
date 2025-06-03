import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import os
import json

# === Config ===
API_KEY = "TXAYZZLDCPD0Q9XS"
TICKER = "AAPL"
INTERVAL = "60min"
CASH_FILE = "paper_cash.json"
TRADE_LOG = "trade_log.csv"

# === NYSE Trading Hours ===
def is_market_open():
    ny_time = datetime.now(pytz.timezone("America/New_York"))
    if ny_time.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return False
    market_open = ny_time.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = ny_time.replace(hour=16, minute=0, microsecond=0)
    return market_open <= ny_time <= market_close

# === Get historical data ===
def fetch_data(ticker):
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={ticker}&interval={INTERVAL}&apikey={API_KEY}&outputsize=compact"
    r = requests.get(url)
    data = r.json()

    if "Time Series" not in data and "Time Series (60min)" not in data:
        raise ValueError("Invalid response from API or API limit reached")

    series = data["Time Series (60min)"]
    df = pd.DataFrame.from_dict(series, orient='index').sort_index()
    df.index = pd.to_datetime(df.index)
    df.columns = ["Open", "High", "Low", "Close", "Volume"]
    df = df.astype(float)
    return df

# === Simple strategy: SMA cross ===
def generate_signals(df):
    df["SMA20"] = df["Close"].rolling(window=20).mean()
    df["SMA50"] = df["Close"].rolling(window=50).mean()
    df["Signal"] = 0
    df.loc[df["SMA20"] > df["SMA50"], "Signal"] = 1  # Buy
    df.loc[df["SMA20"] < df["SMA50"], "Signal"] = -1  # Sell
    return df

# === Load/save portfolio ===
def load_portfolio():
    if os.path.exists(CASH_FILE):
        with open(CASH_FILE, "r") as f:
            return json.load(f)
    else:
        return {"cash": 10000.0, "shares": 0}

def save_portfolio(portfolio):
    with open(CASH_FILE, "w") as f:
        json.dump(portfolio, f)

# === Log trades ===
def log_trade(action, price, timestamp):
    row = {"Time": timestamp, "Action": action, "Price": price}
    if not os.path.exists(TRADE_LOG):
        pd.DataFrame([row]).to_csv(TRADE_LOG, index=False)
    else:
        pd.DataFrame([row]).to_csv(TRADE_LOG, mode='a', header=False, index=False)

# === Paper trading execution ===
def paper_trade(signal, price, portfolio):
    if signal == 1 and portfolio["cash"] >= price:
        shares_to_buy = int(portfolio["cash"] // price)
        portfolio["cash"] -= shares_to_buy * price
        portfolio["shares"] += shares_to_buy
        log_trade("BUY", price, datetime.now().isoformat())
        print(f"[TRADE] BUY {shares_to_buy} shares at ${price:.2f}")
    elif signal == -1 and portfolio["shares"] > 0:
        proceeds = portfolio["shares"] * price
        portfolio["cash"] += proceeds
        log_trade("SELL", price, datetime.now().isoformat())
        print(f"[TRADE] SELL {portfolio['shares']} shares at ${price:.2f}")
        portfolio["shares"] = 0
    else:
        print("[INFO] No trade executed.")
    return portfolio

# === Main loop ===
def main():
    if not is_market_open():
        print("[INFO] Market is closed. Skipping this run.")
        return

    try:
        df = fetch_data(TICKER)
        df = generate_signals(df)
        latest = df.iloc[-1]
        price = latest["Close"]
        signal = latest["Signal"]

        print(f"[{datetime.now()}] Price: ${price:.2f} | Signal: {'BUY' if signal == 1 else 'SELL' if signal == -1 else 'HOLD'}")

        portfolio = load_portfolio()
        portfolio = paper_trade(signal, price, portfolio)
        save_portfolio(portfolio)

        total_value = portfolio["cash"] + portfolio["shares"] * price
        print(f"[INFO] Cash: ${portfolio['cash']:.2f}, Shares: {portfolio['shares']}, Total Value: ${total_value:.2f}")
    except Exception as e:
        print(f"[ERROR] {e}")

if __name__ == "__main__":
    main()
