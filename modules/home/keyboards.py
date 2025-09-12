# modules/home/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.i18n import t

def main_menu(lang: str):
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(t("btn_tts", lang), callback_data="home:tts"),
        InlineKeyboardButton(t("btn_profile", lang), callback_data="home:profile")
    )
    kb.row(
        InlineKeyboardButton(t("btn_credit", lang), callback_data="home:credit"),
        InlineKeyboardButton(t("btn_invite", lang), callback_data="home:invite")
    )
    kb.row(InlineKeyboardButton("ساخت صدای شخصی 🧬", callback_data="home:clone"))
    return kb

def _back_to_home_kb(lang: str):
    """کیبورد بازگشت به منوی اصلی برای صفحه راهنما"""
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🏠 منوی اصلی", callback_data="home:back"))
    return kb
