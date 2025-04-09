from __future__ import annotations

import asyncio
import base64
import html
import textwrap
import ast

from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from api.gpt.gpt_client import get_analysis, understand_user_prompt, async_generate_reply
from api.helpers.helper import async_get_crypto_price
from api.user.models import User, UserProfile
from api.wallet.mint_service import mint_xp_token
from bot.helper import async_request_chart, handle_unknown_coin
from bot.keyboards.keyboards import  up_down_kb
from bot.quries import add_bets_to_db, add_gen_data_to_db, add_xp_async, get_or_create_wallet, get_prompt, get_my_stats, get_wallet_if_exist, update_bet
import json
import logging


router = Router()
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

@router.message(Command(commands=["start"]))
async def handle_start_command(message: types.Message) -> None:
    if message.from_user is None:
        return
    user_id = message.from_user.id
    _, is_new = await User.objects.aget_or_create(
        pk=message.from_user.id,
        defaults={
            "username": message.from_user.username or f"user_{user_id}",
            "first_name": message.from_user.first_name or "",
            "last_name": message.from_user.last_name or "",
        },
    )
    
    if message.chat.type in ['group', 'supergroup']:
        new_text = textwrap.dedent("""\
            🎺 Welcome to MaigaXBT – the greatest trading AI, maybe ever. Some say the best!

            💡 What you can do:
            🔥 /analyse {token} – Powerful technical analysis, no fake news, just real insights.
            🔥 /xpbalance – Check your XP. Because winners track their stats.
            🔥 NEW! Ask MaigaXBT anything about technical analysis—better than some so-called “experts.”
            🔥 Bet with MaigaXBT—Earn XP from your moves!

            Big trades, big wins—let’s make trading great again! 🚀💰
        """)

        new_text_welcome_back = textwrap.dedent("""\
            🎺 Welcome back to MaigaXBT – the greatest trading AI, maybe ever. Some say the best!
            
            💡 What you can do:
            🔥 /analyse {token} – Powerful technical analysis, no fake news, just real insights.
            🔥 /xpbalance – Check your XP. Because winners track their stats.
            🔥 NEW! Ask MaigaXBT anything about technical analysis—better than some so-called “experts.”
            🔥 Bet with MaigaXBT—Earn XP from your moves!

            Big trades, big wins—let’s make trading great again! 🚀💰
        """)

        if is_new:
            await message.answer(new_text)
        else:
            await message.answer(new_text_welcome_back)
        return

    inline_wallet_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🪙 Create Wallet", callback_data="create_wallet")]
    ])

    new_text = textwrap.dedent("""\
        🎺 Welcome to MaigaXBT – the greatest trading AI, maybe ever. Some say the best!

        💡 What you can do:
        🔥 /analyse {token} – Powerful technical analysis, no fake news, just real insights.
        🔥 /xpbalance – Check your XP. Because winners track their stats.
        🔥 /createwallet – Create your Web3 wallet and instantly receive 1 XP token!
        🔥 NEW! Ask MaigaXBT anything about technical analysis—better than some so-called “experts.”
        🔥 Bet with MaigaXBT—Earn XP from your moves!

        Big trades, big wins—let’s make trading great again! 🚀💰
    """)

    new_text_welcome_back = textwrap.dedent("""\
        🎺 Welcome back to MaigaXBT – the greatest trading AI, maybe ever. Some say the best!

        💡 What you can do:
        🔥 /analyse {token} – Powerful technical analysis, no fake news, just real insights.
        🔥 /xpbalance – Check your XP. Because winners track their stats.
        🔥 /createwallet – Create your Web3 wallet and instantly receive 1 XP token!
        🔥 NEW! Ask MaigaXBT anything about technical analysis—better than some so-called “experts.”
        🔥 Bet with MaigaXBT—Earn XP from your moves!

        Big trades, big wins—let’s make trading great again! 🚀💰
    """)

    if is_new:
        await message.answer(new_text, reply_markup=inline_wallet_kb)
    else:
        await message.answer(new_text_welcome_back, reply_markup=inline_wallet_kb)

@router.callback_query(F.data == "create_wallet")
async def handle_wallet_button(callback: types.CallbackQuery):
    if callback.message.chat.type in ['group', 'supergroup']:
        await callback.message.answer(
            "❌ Wallet can only be created in private chat.\n\n👉 [Click to PM me](https://t.me/maigaxbt_bot)",
            parse_mode="Markdown"
        )
        await callback.answer()
        return

    await process_create_wallet(callback.from_user.id, callback.message)
    await callback.answer()
    
@router.message(Command(commands=["createwallet"]))
async def handle_createwallet_command(message: types.Message) -> None:
    if message.from_user is None:
        return

    if message.chat.type in ['group', 'supergroup']:
        await message.reply(
            "❌ Creating a wallet can only be done in private chat.\n\n👉 [Click to PM me](https://t.me/maigaxbt_bot)",
            parse_mode="Markdown"
        )
        return

    await process_create_wallet(message.from_user.id, message)
    
async def process_create_wallet(user_id: int, message: types.Message):
    await message.answer("⏳ Checking your wallet status...")

    wallet, created = await get_or_create_wallet(user_id)

    if not created:
        await message.answer(
            f"💳 You already have a wallet:\n\n`{wallet.wallet_address}`",
            parse_mode="Markdown"
        )
        return

    await message.answer("⏳ Creating your wallet... Please wait...")

    profile = await UserProfile.objects.select_related('user').aget(user__id=user_id)

    try:

        tx_hash = await mint_xp_token(wallet.wallet_address, profile, 1)
        if tx_hash:
            await add_xp_async(profile, 1)
            tx_url = f"https://opbnb-testnet.bscscan.com/tx/{tx_hash}"
            await message.answer(
            f"🎉 Your wallet has been successfully created!\n\n"
            f"💳 Wallet Address:\n`{wallet.wallet_address}`\n\n"
            f"🪙 You have received *1 XP token* as a welcome gift!\n"
            f"🔗 [View Transaction on BscScan]({tx_url})",
            parse_mode="Markdown"
            )

    except Exception as e:
        await message.answer(f"Wallet created but XP token minting failed.\n\nError: {e}")


@router.message(Command(commands=["analyse"]))
async def generate_response(message: types.Message) -> None:
    wallet = await get_wallet_if_exist(message.from_user.id)
    if not wallet:
        await message.reply("❌ You haven't created a wallet yet.\nPlease use /createwallet first.")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply("Please provide a trading pair. Example: /analyse btc")
        return

    coin_symbol = args[1]
    
    coin_id = await handle_unknown_coin(message, coin_symbol)
    if coin_id is None:
        return

    await message.reply("⏳ Generating answer, please wait...")

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

    username = message.from_user.username or f"user_{message.from_user.id}"
    
    await message.reply_photo(
        photo=types.BufferedInputFile(chart_bytes, filename="chart.png"),
        reply_markup=up_down_kb(bet_id, message.from_user.id, username, message.chat.type),
        caption=html.escape(analysis_reply))

    await add_gen_data_to_db(analysis_reply, message.from_user.id)



@router.callback_query()
async def bet_up_or_down(callback: types.CallbackQuery) -> None:
    try:
        data_parts = callback.data.split(":")
        if len(data_parts) != 5:
            await callback.answer("Invalid callback data format.", show_alert=True)
            return

        up_down, bet_id, original_user_id, chat_type, username = data_parts
        original_user_id = int(original_user_id)

    except ValueError:
        await callback.answer("Error processing your request.", show_alert=True)
        return

    if chat_type in ["group", "supergroup"] and callback.from_user.id != original_user_id:
        await callback.answer("You are not allowed to vote on this prediction!", show_alert=True)
        return

    msg_id = callback.message.message_id
    if chat_type in ["group", "supergroup"]:
        chat_id = callback.message.chat.id
    else:
        chat_id = callback.from_user.id  

    if up_down in ["agree", "disagree"]:
        await update_bet(bet_id=bet_id, prediction=up_down, msg_id=msg_id, result="pending", chat_type=chat_type, chat_id=chat_id)

        await callback.message.edit_reply_markup(reply_markup=None)
        if chat_type in ["group", "supergroup"]:
            response_text = f"@{username} {up_down} this signal, @{username} please wait for your prediction result in the next hour!"
        else:
            response_text = f"You {up_down} this signal, please wait for your prediction result in the next hour!"


        await callback.message.reply(response_text, reply_markup=None)

@router.message(Command(commands=["xpbalance"]))
async def handle_xpbalance_command(message: types.Message) -> None:
    if message.from_user is None:
        return

    user_profile = await get_my_stats(user_id=message.from_user.id)
    await message.answer(f"Your balance is {user_profile.xp_points} XP")


@router.message(F.text)
async def handle_other_messages(message: types.Message) -> None:
    wallet = await get_wallet_if_exist(message.from_user.id)
    if not wallet:
        await message.reply("❌ You haven't created a wallet yet.\nPlease use /createwallet first.")
        return
    
    logging.debug(f"message: {repr(message.text)}")
    if message.chat.type in ['group', 'supergroup']:
        if not message.text.startswith('@maigaxbt'):
            return
        text_to_process = message.text[len('@maigaxbt'):].strip()
    else:
        text_to_process = message.text.strip()

    await message.reply("⏳ Generating answer, please wait...")
    
    prompt = await understand_user_prompt(text_to_process)
    logging.debug(f"prompt: ->{prompt}<-")
    try:
        dict_prompt = json.loads(prompt)
    except json.JSONDecodeError:
        await message.reply("⚠️ parsing failed，please check the input format")
        return
    
    symbol = dict_prompt.get("symbol", "").lstrip("$") 
    timeframe = dict_prompt["timeframe"]
    user_prompt = dict_prompt["user_prompt"]

    if not symbol:
        await message.reply(dict_prompt["none_existing_token"])
        return

    coin_id = await handle_unknown_coin(message, symbol)
    if coin_id is None:
        await message.reply(dict_prompt["none_existing_token"])
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"
    chart_bytes, analysis_reply, token_price = await asyncio.gather(
        async_request_chart(coin_id, timeframe),
        get_analysis(symbol=coin_id, coin_name=symbol.upper(), interval=timeframe, limit=120, user_prompt=user_prompt),
        async_get_crypto_price(coin_id)
    )
    bet_id = await add_bets_to_db(
        user_id=user_id,
        token=coin_id,
        entry_price=token_price,
        symbol=symbol.upper()
    )
    
    if not chart_bytes:
        await message.reply(
            text=html.escape(analysis_reply),
            reply_markup=up_down_kb(bet_id, user_id, username, message.chat.type)
        )
    else:
        await message.reply_photo(
            photo=types.BufferedInputFile(chart_bytes, filename="chart.png"),
            reply_markup=up_down_kb(bet_id, user_id, username, message.chat.type),
            caption=html.escape(analysis_reply)
        )
        
    await add_gen_data_to_db(analysis_reply, message.from_user.id)


@router.message(F.photo)
async def handle_photo(message: types.Message):
    await message.reply("⏳ Generating answer, please wait...")
    file = await message.bot.get_file(message.photo[-1].file_id)
    file_content = await message.bot.download_file(file.file_path)

    img_base64 = base64.b64encode(file_content.read()).decode('utf-8')
    reply = await async_generate_reply(img_base64)

    await message.reply(reply)
