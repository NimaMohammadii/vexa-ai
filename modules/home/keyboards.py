# modules/home/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from modules.i18n import t
from config import GPT_WEBAPP_URL

def main_menu(lang: str):
    kb = InlineKeyboardMarkup()
    gpt_button = (
        InlineKeyboardButton(t("btn_gpt", lang), web_app=WebAppInfo(GPT_WEBAPP_URL))
        if GPT_WEBAPP_URL
        else InlineKeyboardButton(t("btn_gpt", lang), callback_data="home:gpt_unavailable")
    )
    kb.row(
        gpt_button,
        InlineKeyboardButton(t("btn_tts", lang), callback_data="home:tts")
    )
    kb.row(
        InlineKeyboardButton(t("btn_profile", lang), callback_data="home:profile"),
        InlineKeyboardButton(t("btn_credit", lang), callback_data="home:credit")
    )
    kb.row(
        InlineKeyboardButton(t("btn_invite", lang), callback_data="home:invite"),
        InlineKeyboardButton("ساخت صدای شخصی 🧬", callback_data="home:clone")
    )
    return kb

def _back_to_home_kb(lang: str):
    """کیبورد بازگشت به منوی اصلی برای صفحه راهنما"""
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🏠 منوی اصلی", callback_data="home:back"))
    return kb
