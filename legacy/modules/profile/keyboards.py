from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def back_home():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="profile:back"))
    return kb