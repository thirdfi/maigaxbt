import ssl

import aiohttp
import certifi
import requests

from api.user.models import Bet

from api.config.application import COINGECKO_API_KEY

def get_coin_id_from_symbol(token):
    headers = {"x-cg-pro-api-key": COINGECKO_API_KEY}
    search_url = "https://pro-api.coingecko.com/api/v3/search"

    search_response = requests.get(search_url, params={"query": token}, headers=headers, verify=certifi.where())

    if search_response.status_code != 200:
        return f"⚠️ Search API failed: {search_response.status_code}"

    search_data = search_response.json()
    if search_data["coins"]:
        return search_data["coins"][0]["id"]

    return None

def check_coin_id_sync_safe(symbol):
    coin_id = get_coin_id_from_symbol(symbol)
    if isinstance(coin_id, str):
        return coin_id
    return None

def get_crypto_price(coin_id):
    url = "https://pro-api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": coin_id,
        "vs_currencies": "usd"
    }

    headers = {"x-cg-pro-api-key": COINGECKO_API_KEY}

    response = requests.get(url, params=params, verify=certifi.where(), headers=headers)
    data = response.json()

    if coin_id in data and "usd" in data[coin_id]:
        return float(data[coin_id]["usd"])
    return None

async def async_get_crypto_price(coin_id):
    url = "https://pro-api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": coin_id,
        "vs_currencies": "usd"
    }

    headers = {"x-cg-pro-api-key": COINGECKO_API_KEY}

    ssl_context = ssl.create_default_context(cafile=certifi.where())

    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, ssl=ssl_context, headers=headers) as response:
            data = await response.json()

            if coin_id in data and "usd" in data[coin_id]:
                return float(data[coin_id]["usd"])
            return None

def get_crypto_prices(coin_ids):
    url = "https://pro-api.coingecko.com/api/v3/simple/price"
    params = {
        "ids": ",".join(coin_ids),
        "vs_currencies": "usd"
    }

    headers = {"x-cg-pro-api-key": COINGECKO_API_KEY}

    response = requests.get(url, params=params, verify=certifi.where(), headers=headers)
    data = response.json()

    prices = {}
    for coin_id in coin_ids:
        if coin_id in data and "usd" in data[coin_id]:
            prices[coin_id] = float(data[coin_id]["usd"])
    return prices

def place_bet(user, token, prediction, amount, verification_time):
    entry_price = get_crypto_price(token)
    bet = Bet.objects.create(
        user=user, token=token, prediction=prediction, amount=amount, verification_time=verification_time, entry_price=entry_price
    )
    return bet

