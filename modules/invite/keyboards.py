# modules/invite/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.i18n import t

def keyboard(lang: str = "fa"):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb

def back_keyboard(lang: str = "fa"):
    return keyboard(lang)