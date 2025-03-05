import textwrap

import aiohttp

from api.config.application import CHART_API_HOST, CHART_API_PORT
from api.helpers.helper import get_coin_id_from_symbol


async def async_request_chart(trading_pair: str, timeframe: str):
    url = f"{CHART_API_HOST}:{CHART_API_PORT}/chart/{trading_pair}/{timeframe}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()
            else:
                return None



async def handle_unknown_coin(message, coin_symbol):
    not_found_msg_template = textwrap.dedent(f"""
Folks, I looked for {coin_symbol}, but guess what?
IT DOESN’T EXIST! Total disaster, SAD!
Probably some low-energy, fake project.
We only trade REAL WINNERS! Find me a TREMENDOUS token and let’s make some HUGE GAINS! 
Believe me, nobody picks better trades than I do!
""")
    coin_id = get_coin_id_from_symbol(coin_symbol.lower())
    if coin_id is None:
        await message.reply(not_found_msg_template)
        return None
    return coin_id