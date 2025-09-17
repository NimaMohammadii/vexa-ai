# modules/clone/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def menu_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="home:back"))
    return kb

def payment_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ تایید", callback_data="clone:confirm_payment"),
        InlineKeyboardButton("❌ لغو", callback_data="home:back")
    )
    return kb

def no_credit_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💳 خرید کردیت", callback_data="credit:menu"),
        InlineKeyboardButton("⬅️ بازگشت", callback_data="home:back")
    )
    return kb