# modules/home/keyboards.py
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from modules.i18n import t


def main_menu(lang: str) -> ReplyKeyboardMarkup:
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(
        KeyboardButton(t("btn_profile", lang)),
        KeyboardButton(t("btn_credit", lang)),
    )
    kb.row(
        KeyboardButton(t("btn_tts", lang)),
        KeyboardButton(t("btn_gpt", lang)),
    )
    kb.row(
        KeyboardButton(t("btn_lang", lang)),
        KeyboardButton(t("btn_invite", lang)),
    )
    return kb


def _back_to_home_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("home_back_to_menu", lang), callback_data="home:back"))
    return kb
