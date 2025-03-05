from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder


def up_down_kb(bet_id):
    builder = InlineKeyboardBuilder()

    builder.add(types.InlineKeyboardButton(
            text="Agree 👍",
            callback_data=f"agree:{bet_id}"))

    builder.add(types.InlineKeyboardButton(
            text="Disagree 👎",
            callback_data=f"disagree:{bet_id}"))
    builder.adjust(2)

    return builder.as_markup()