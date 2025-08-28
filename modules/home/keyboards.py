# modules/home/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu(lang: str = "fa"):
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("تبدیل متن به صدا 🎧", callback_data="home:tts"),
        InlineKeyboardButton("پروفایل 🙋🏼‍♂️", callback_data="home:profile"),
        InlineKeyboardButton("خرید Credit 🛒", callback_data="home:credit"),
        InlineKeyboardButton("دعوت دوستان 🎁", callback_data="home:invite"),
    )
    return kb