# modules/clone/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def menu_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="home:back"))
    return kb