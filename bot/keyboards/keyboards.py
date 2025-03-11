from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder


def up_down_kb(bet_id, user_id, username, chat_type):
    if not username: 
        username = f"user_{user_id}"

    builder = InlineKeyboardBuilder()

    builder.add(types.InlineKeyboardButton(
            text="Agree 👍",
            callback_data=f"agree:{bet_id}:{user_id}:{chat_type}:{username}"))

    builder.add(types.InlineKeyboardButton(
            text="Disagree 👎",
            callback_data=f"disagree:{bet_id}:{user_id}:{chat_type}:{username}"))
    builder.adjust(2)

    return builder.as_markup()