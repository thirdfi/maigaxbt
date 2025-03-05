from __future__ import annotations

import openai

from api.config.application import GPT_API_KEY
from api.gpt.chart_data import fetch_chart_data, compute_indicators
from api.gpt.prompt_text import img_analyse_prompt, get_system_message, understand_user_message

aclient = openai.AsyncClient(api_key=GPT_API_KEY)




async def get_analysis(symbol: str, coin_name: str, interval: str, limit: int, user_prompt: str = "") -> str:
    df = await fetch_chart_data(symbol=symbol, interval=interval, limit=limit)
    if df == "Error fetching chart data from Binance API":
        return df

    df = compute_indicators(df)
    last_10 = df.tail(10)[["timestamp", "close", "rsi", "macd", "macd_signal", "bb_upper", "bb_lower"]].to_dict(
        orient="records")

    # Format market data into readable text
    rdy_prompt = f"\n\nAnalyzing coin name: **{coin_name}** on the **{interval}** timeframe:\n\n"

    for row in last_10:
        rdy_prompt += (
            f"📅 {row['timestamp']} | Close: {row['close']} | RSI: {row['rsi']} | "
            f"MACD: {row['macd']} | MACD Signal: {row['macd_signal']} | "
            f"BB Upper: {row['bb_upper']} | BB Lower: {row['bb_lower']}\n"
        )

    # Call OpenAI API
    response = await aclient.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": get_system_message(user_prompt)},
            {"role": "user", "content": rdy_prompt},
        ],
    )

    return response.choices[0].message.content



async def understand_user_prompt(user_prompt: str) -> str:
    response = await aclient.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": understand_user_message},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content




async def async_generate_reply(img_base64) -> str | None:
    img_str = f"data:image/jpeg;base64,{img_base64}"

    sentiment_response = await aclient.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": img_analyse_prompt},
                    {"type": "image_url", "image_url": {"url": img_str}}
                ],
            },
        ],
    )

    return sentiment_response.choices[0].message.content
