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

def menu_actions(lang: str) -> dict[str, str]:
    return {
        t("btn_profile", lang): "profile",
        t("btn_credit", lang): "credit",
        t("btn_tts", lang): "tts",
        t("btn_gpt", lang): "gpt",
        t("btn_lang", lang): "lang",
        t("btn_invite", lang): "invite",
    }


def _back_to_home_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    return kb
