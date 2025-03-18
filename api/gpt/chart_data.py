import re

import certifi
import httpx
import pandas as pd
import ta
from api.config.application import COINGECKO_API_KEY



async def fetch_chart_data(symbol, interval, limit):
    match = re.match(r"(\d+)([mhd])", interval.lower())
    if not match:
        return f"Invalid interval format: {interval}"
    num = int(match.group(1))
    unit = match.group(2)

    # Determine the number of days to request and the Pandas frequency alias
    if unit == "m":
        days = 1  # For minute-based intervals, request 1 day (raw ~5m resolution)
        freq = f"{num}min"  # Use 'min' instead of 'T'
    elif unit == "h":
        days = 7  # For hour-based intervals, request 7 days (raw resolution is hourly)
        freq = f"{num}h"  # "H" is for hours
    elif unit == "d":
        days = 100  # For day-based intervals, request 100 days to get daily resolution
        freq = f"{num}D"  # "D" is for days
    else:
        days = 7
        freq = interval

    # Construct the URL and parameters; note 'symbol' should be the CoinGecko coin id (e.g. "bitcoin")
    url = f"https://pro-api.coingecko.com/api/v3/coins/{symbol}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": days
    }

    headers = {"x-cg-pro-api-key": COINGECKO_API_KEY}

    async with httpx.AsyncClient(verify=certifi.where(), headers=headers) as client:
        response = await client.get(url, params=params)

    if response.status_code != 200:
        return f"Error fetching chart data from CoinGecko API: {response.status_code}"

    data = response.json()
    prices = data.get("prices", [])
    volumes = data.get("total_volumes", [])
    if not prices:
        return "No price data available"

    # Create DataFrame for price data
    df_prices = pd.DataFrame(prices, columns=["timestamp", "price"])
    df_prices["timestamp"] = pd.to_datetime(df_prices["timestamp"], unit="ms")

    # Create DataFrame for volume data (if available) and merge with prices
    if volumes:
        df_volumes = pd.DataFrame(volumes, columns=["timestamp", "volume"])
        df_volumes["timestamp"] = pd.to_datetime(df_volumes["timestamp"], unit="ms")
        df = pd.merge_asof(df_prices.sort_values("timestamp"),
                           df_volumes.sort_values("timestamp"),
                           on="timestamp")
    else:
        df = df_prices.copy()
        df["volume"] = None

    # Set timestamp as index for resampling
    df.set_index("timestamp", inplace=True)

    # Resample the data to the desired interval and compute OHLC for price; sum volumes if available
    ohlc = df["price"].resample(freq).ohlc()
    if df["volume"].notna().all():
        ohlc["volume"] = df["volume"].resample(freq).sum()
    else:
        ohlc["volume"] = None

    # Reset index and format timestamp for output
    ohlc = ohlc.reset_index()
    ohlc["timestamp"] = ohlc["timestamp"].dt.strftime('%Y-%m-%d %H:%M:%S')

    # Limit the result to the last 'limit' rows if needed
    if limit and len(ohlc) > limit:
        ohlc = ohlc.tail(limit)

    return ohlc.to_dict(orient="records")

def compute_indicators(df):
    if isinstance(df, list):
        df = pd.DataFrame(df)

    df["close"] = df["close"].astype(float)
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()

    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
    df["bb_upper"] = bb.bollinger_hband()
    df["bb_lower"] = bb.bollinger_lband()

    return df.dropna()

