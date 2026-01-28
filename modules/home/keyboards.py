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
        InlineKeyboardButton(t("btn_gpt", lang), callback_data="home:gpt_chat"),
        InlineKeyboardButton(t("btn_anonymous_chat", lang), callback_data="home:anon_chat"),
    )
    kb.row(
        InlineKeyboardButton(t("btn_image", lang), callback_data="home:image"),
        InlineKeyboardButton(t("btn_video", lang), callback_data="home:video"),
    )
    kb.row(
        InlineKeyboardButton(t("btn_tts", lang), callback_data="home:tts"),
        InlineKeyboardButton(t("btn_clone", lang), callback_data="home:clone"),
    )
    kb.row(
        InlineKeyboardButton(t("btn_sora2", lang), callback_data="home:sora2"),
        InlineKeyboardButton(t("btn_api_token", lang), callback_data="home:api_token"),
    )
    kb.row(
        InlineKeyboardButton(t("btn_lang", lang), callback_data="home:lang"),
        InlineKeyboardButton(t("btn_invite", lang), callback_data="home:invite"),
    )
    return kb


def _back_to_home_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("home_back_to_menu", lang), callback_data="home:back"))
    return kb
