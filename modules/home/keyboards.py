# modules/home/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from modules.i18n import t


def main_menu(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(t("btn_profile", lang), callback_data="home:profile"),
        InlineKeyboardButton(t("btn_credit", lang), callback_data="home:credit"),
    )
    kb.row(
        InlineKeyboardButton(t("btn_tts", lang), callback_data="home:tts"),
        InlineKeyboardButton(t("btn_gpt", lang), callback_data="home:gpt"),
    )
    kb.row(
        InlineKeyboardButton(t("btn_lang", lang), callback_data="home:lang"),
        InlineKeyboardButton(t("btn_invite", lang), callback_data="home:invite"),
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
