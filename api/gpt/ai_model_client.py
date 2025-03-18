from __future__ import annotations
import re
import aiohttp
import pandas as pd
from api.config.application import IO_API_KEY
from api.gpt.chart_data import fetch_chart_data, compute_indicators
from api.gpt.prompt_text import img_analyse_prompt, get_system_message, understand_user_message

BASE_URL = "https://api.intelligence.io.solutions/api/v1"
HEADERS = {"Authorization": f"Bearer {IO_API_KEY}"}

async def get_analysis(symbol: str, coin_name: str, interval: str, limit: int, user_prompt: str = "") -> str:
    df = await fetch_chart_data(symbol=symbol, interval=interval, limit=limit)
    if df == "Error fetching chart data from Binance API":
        return df

    df = compute_indicators(df)
    last_10 = df.tail(10)[["timestamp", "close", "rsi", "macd", "macd_signal", "bb_upper", "bb_lower"]].to_dict(
        orient="records")

    rdy_prompt = f"\n\nAnalyzing coin name: **{coin_name}** on the **{interval}** timeframe:\n\n"
    for row in last_10:
        rdy_prompt += (
            f"📅 {row['timestamp']} | Close: {row['close']} | RSI: {row['rsi']} | "
            f"MACD: {row['macd']} | MACD Signal: {row['macd_signal']} | "
            f"BB Upper: {row['bb_upper']} | BB Lower: {row['bb_lower']}\n"
        )

    async with aiohttp.ClientSession() as session:
        payload = {
            "model": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",  
            "messages": [
                {"role": "system", "content": get_system_message(user_prompt)},
                {"role": "user", "content": rdy_prompt},
            ],
        }

        async with session.post(f"{BASE_URL}/chat/completions", headers=HEADERS, json=payload) as response:
            response_text = await response.text()
            if response.status != 200:
                return f"API Error: {response.status} - {response_text}"

            try:
                result = await response.json()            
                response_content = result.get('choices', [{}])[0].get('message', {}).get('content', "No content returned")      
                print("response_content: ", response_content)          
                cleaned_content = remove_think_tags(response_content)
                return cleaned_content
            except Exception as e:
                return f"Error parsing response: {e}"

async def understand_user_prompt(user_prompt: str) -> str:
    async with aiohttp.ClientSession() as session:
        payload = {
            "model": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",  
            "messages": [
                {"role": "system", "content": understand_user_message},
                {"role": "user", "content": user_prompt},
            ],
        }

        async with session.post(f"{BASE_URL}/chat/completions", headers=HEADERS, json=payload) as response:
            response_text = await response.text()

            if response.status != 200:
                return f"API Error: {response.status} - {response_text}"

            try:
                result = await response.json()
                return result.get('choices', [{}])[0].get('message', {}).get('content', "No content returned")
            except Exception as e:
                return f"Error parsing response: {e}"

async def async_generate_reply(img_base64) -> str | None:
    img_str = f"data:image/jpeg;base64,{img_base64}"

    async with aiohttp.ClientSession() as session:
        payload = {
            "model": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B", 
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": img_analyse_prompt},
                        {"type": "image_url", "image_url": {"url": img_str}}
                    ],
                },
            ],
        }

        async with session.post(f"{BASE_URL}/chat/completions", headers=HEADERS, json=payload) as response:
            response_text = await response.text()

            if response.status != 200:
                return f"API Error: {response.status} - {response_text}"

            try:
                result = await response.json()
                return result.get('choices', [{}])[0].get('message', {}).get('content', "No content returned")
            except Exception as e:
                return f"Error parsing response: {e}"
            

def remove_think_tags(text):
    while '<think>' in text:
        text = re.sub(r'<think>[^<>]*</think>', '', text)
        text = re.sub(r'<think>.*</think>', '', text, flags=re.DOTALL)
    return text.strip()              