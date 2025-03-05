from __future__ import annotations

import asyncio
import base64
import html
import textwrap
import ast

from aiogram import Router, types, F
from aiogram.filters import Command

from api.gpt.gpt_client import get_analysis, understand_user_prompt, async_generate_reply
from api.helpers.helper import async_get_crypto_price
from api.user.models import User
from bot.helper import async_request_chart, handle_unknown_coin
from bot.keyboards.keyboards import  up_down_kb
from bot.quries import add_bets_to_db, add_gen_data_to_db, get_prompt, get_my_stats, update_bet



router = Router()


@router.message(Command(commands=["start"]))
async def handle_start_command(message: types.Message) -> None:
    if message.from_user is None:
        return

    _, is_new = await User.objects.aget_or_create(
        pk=message.from_user.id,
        defaults={
            "username": message.from_user.username,
            "first_name": message.from_user.first_name or "",
            "last_name": message.from_user.last_name or "",
        },
    )


    new_text = textwrap.dedent("""\
    🎺 Welcome to MaigaXBT – the greatest trading AI, maybe ever. Some say the best!

    💡 What you can do:
    🔥 /analyse {token} – Powerful technical analysis, no fake news, just real insights.
    🔥 /xpbalance – Check your XP. Because winners track their stats.
    🔥 NEW! Ask MaigaXBT anything about technical analysis—better than some so-called “experts.”
    🔥 Predict AI signals—right or wrong? Your feedback trains MaigaXBT and earns XP!
    
    Big trades, big wins—let’s make trading great again! 🚀💰
    """)

    new_text_welcome_back = textwrap.dedent("""\
    🎺 Welcome back to MaigaXBT – the greatest trading AI, maybe ever. Some say the best!
    
    💡 What you can do:
    🔥 /analyse {token} – Powerful technical analysis, no fake news, just real insights.
    🔥 /xpbalance – Check your XP. Because winners track their stats.
    🔥 NEW! Ask MaigaXBT anything about technical analysis—better than some so-called “experts.”
    🔥 Predict AI signals—right or wrong? Your feedback trains MaigaXBT and earns XP!
    
    Big trades, big wins—let’s make trading great again! 🚀💰
    """)

    if is_new:
        await message.answer(new_text)
    else:
        await message.answer(new_text_welcome_back)




@router.message(Command(commands=["analyse"]))
async def generate_response(message: types.Message) -> None:

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Please provide a trading pair. Example: /analyse btc")
        return

    coin_symbol = args[1]


    coin_id = await handle_unknown_coin(message, coin_symbol)
    if coin_id is None:
        return

    await message.answer("Generating answer...")


    prompt = await get_prompt()

    chart_bytes, analysis_reply, token_price = await asyncio.gather(
        async_request_chart(coin_id, prompt.timeframe),
        get_analysis(symbol=coin_id, coin_name=coin_symbol.upper(), interval=prompt.timeframe, limit=120),
        async_get_crypto_price(coin_id)
    )

    bet_id =  await add_bets_to_db(user_id=message.from_user.id,
                             token=coin_id,
                             entry_price=token_price,
                             symbol=coin_symbol.upper())

    await message.reply_photo(
        photo=types.BufferedInputFile(chart_bytes, filename="chart.png"),
        reply_markup=up_down_kb(bet_id),
        caption=html.escape(analysis_reply))

    await add_gen_data_to_db(analysis_reply, message.from_user.id)



@router.callback_query()
async def bet_up_or_down(callback: types.CallbackQuery) -> None:
    up_down, bet_id = callback.data.split(":")

    msg_id = callback.message.message_id

    if up_down in ["agree", "disagree"]:
        await update_bet(bet_id=bet_id, prediction=up_down, msg_id=msg_id, result="pending")

        await callback.message.edit_reply_markup(reply_markup=None)
        await callback.message.reply(f"You {up_down} this signal, please wait for your prediction result in next hour!",
                                      reply_markup=None)


@router.message(Command(commands=["xpbalance"]))
async def handle_xpbalance_command(message: types.Message) -> None:
    if message.from_user is None:
        return

    user_profile = await get_my_stats(user_id=message.from_user.id)
    await message.answer(f"Your balance is {user_profile.xp_points} XP")


@router.message(F.text)
async def handle_other_messages(message: types.Message) -> None:
    if message.chat.type in ['group', 'supergroup']:
        if not message.text.startswith('@maigaxbt'):
            return
        text_to_process = message.text[len('@maigaxbt'):].strip()
    else:
        text_to_process = message.text.strip()

    prompt = await understand_user_prompt(text_to_process)

    dict_prompt = ast.literal_eval(prompt)
    symbol = dict_prompt["symbol"]
    timeframe = dict_prompt["timeframe"]
    user_prompt = dict_prompt["user_prompt"]

    if not symbol:
        await message.reply(dict_prompt["none_existing_token"])
        return

    coin_id = await handle_unknown_coin(message, symbol)
    if coin_id is None:
        return

    chart_bytes, analysis_reply, token_price = await asyncio.gather(
        async_request_chart(coin_id, timeframe),
        get_analysis(symbol=coin_id, coin_name=symbol.upper(), interval=timeframe, limit=120, user_prompt=user_prompt),
        async_get_crypto_price(coin_id)
    )

    bet_id = await add_bets_to_db(
        user_id=message.from_user.id,
        token=coin_id,
        entry_price=token_price,
        symbol=symbol.upper()
    )

    await message.reply_photo(
        photo=types.BufferedInputFile(chart_bytes, filename="chart.png"),
        reply_markup=up_down_kb(bet_id),
        caption=html.escape(analysis_reply)
    )

    await add_gen_data_to_db(analysis_reply, message.from_user.id)


@router.message(F.photo)
async def handle_photo(message: types.Message):

    file = await message.bot.get_file(message.photo[-1].file_id)
    file_content = await message.bot.download_file(file.file_path)

    img_base64 = base64.b64encode(file_content.read()).decode('utf-8')
    reply = await async_generate_reply(img_base64)

    await message.reply(reply)



