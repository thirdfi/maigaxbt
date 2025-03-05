import io
import re
import ssl

import aiohttp
import certifi
import mplfinance as mpf
import pandas as pd
import ta
import matplotlib.pyplot as plt
from api.config.application import COINGECKO_API_KEY

ssl_context = ssl.create_default_context(cafile=certifi.where())


async def async_fetch_data(symbol, timeframe="1h", limit=80):
    match = re.match(r"(\d+)([mhd])", timeframe.lower())
    if not match:
        return f"Invalid timeframe format: {timeframe}"
    unit = match.group(2)

    # Map the timeframe to the 'days' parameter for CoinGecko:
    # Note: CoinGecko's OHLC endpoint accepts fixed day values.
    # For minute-based resolutions, we use 1 day (returns ~5m data).
    # For hour-based resolutions, we use 7 days.
    # For day-based resolutions, we use 30 days.
    if unit == 'm':
        days = 1
    elif unit == 'h':
        days = 7
    elif unit == 'd':
        days = 30
    else:
        days = 7  # Default fallback

    # Build the URL; note 'symbol' should be the CoinGecko coin id (e.g., "bitcoin")
    url = f"https://pro-api.coingecko.com/api/v3/coins/{symbol}/ohlc?vs_currency=usd&days={days}"
    headers = {"x-cg-pro-api-key": COINGECKO_API_KEY}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, ssl=ssl_context, headers=headers) as response:
            if response.status != 200:
                return f"Error fetching chart data from CoinGecko API: {response.status}"
            data = await response.json()

    # Create DataFrame from the returned data
    df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)

    if len(df) > limit:
        df = df.tail(limit)

    return df

async def async_compute_indicators(df):
    # Compute moving averages
    df["SMA50"] = df["close"].rolling(window=50).mean()
    df["MA10"] = df["close"].rolling(window=10).mean()
    df["MA20"] = df["close"].rolling(window=20).mean()

    # Compute Bollinger Bands
    bb = ta.volatility.BollingerBands(close=df["close"], window=20, window_dev=2)
    df["BB_High"] = bb.bollinger_hband()
    df["BB_Mid"] = bb.bollinger_mavg()
    df["BB_Low"] = bb.bollinger_lband()

    # Compute RSI
    rsi_indicator = ta.momentum.RSIIndicator(close=df["close"], window=14)
    df["RSI"] = rsi_indicator.rsi()

    # Compute MACD
    macd_indicator = ta.trend.MACD(close=df["close"], window_slow=26, window_fast=12, window_sign=9)
    df["MACD"] = macd_indicator.macd()
    df["MACD_Signal"] = macd_indicator.macd_signal()
    df["MACD_Hist"] = macd_indicator.macd_diff()

    return df


def plot_data_on_axes(df, symbol, ax_main, ax_rsi, ax_macd, timeframe):
    # Prepare addplots for moving averages and Bollinger Bands
    add_plots = [
        mpf.make_addplot(df["SMA50"], color="#ef6c00", width=1.0, ax=ax_main),
        mpf.make_addplot(df["MA10"], color="#26a69a", width=1.0, ax=ax_main),
        mpf.make_addplot(df["MA20"], color="#5c6bc0", width=1.0, ax=ax_main),
        mpf.make_addplot(df["BB_High"], color="#bdbdbd", width=1.0, linestyle="dotted", ax=ax_main),
        mpf.make_addplot(df["BB_Mid"], color="#bdbdbd", width=1.0, linestyle="dotted", ax=ax_main),
        mpf.make_addplot(df["BB_Low"], color="#bdbdbd", width=1.0, linestyle="dotted", ax=ax_main),
    ]

    # Plot candlestick chart on the main axis
    mpf.plot(
        df,
        type="candle",
        ax=ax_main,
        addplot=add_plots,
        volume=False,
        style="default",
        returnfig=False
    )

    # Plot RSI indicator on its dedicated axis
    ax_rsi.plot(df.index, df["RSI"], color="purple")
    ax_rsi.set_ylabel("RSI")
    ax_rsi.set_ylim(0, 100)

    # Plot MACD indicators on its dedicated axis
    ax_macd.plot(df.index, df["MACD"], color="#d81b60", label="MACD")
    ax_macd.plot(df.index, df["MACD_Signal"], color="#ffa726", label="Signal")
    ax_macd.bar(df.index, df["MACD_Hist"], color="#7e57c2", alpha=0.5, label="Hist")
    ax_macd.set_ylabel("MACD")

    # Update title and legends
    ax_main.set_title(f"{symbol}/USDT - {timeframe} Data")
    ax_main.legend(["SMA50", "MA10", "MA20", "BB High", "BB Mid", "BB Low"])
    ax_macd.legend()

    plt.tight_layout()


async def async_create_chart(symbol_id, timeframe="1h", limit=80):

    df = await async_fetch_data(symbol_id, timeframe, limit)
    df = await async_compute_indicators(df)

    # Create a new figure and axes for each chart instance
    fig, (ax_main, ax_rsi, ax_macd) = plt.subplots(
        nrows=3, ncols=1,
        gridspec_kw={"height_ratios": [3, 1, 1]},
        figsize=(16, 8)
    )

    plot_data_on_axes(df, symbol_id, ax_main, ax_rsi, ax_macd, timeframe)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)

    plt.close(fig)

    return buf
