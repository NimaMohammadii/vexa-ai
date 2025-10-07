"""Inline keyboards for the Sora 2 menu."""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from modules.i18n import t


def main_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("sora2_btn_buy", lang), callback_data="sora2:buy"))
    kb.add(InlineKeyboardButton(t("home_back_to_menu", lang), callback_data="home:back"))
    return kb


def no_credit_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("btn_credit", lang), callback_data="credit:menu"))
    kb.add(InlineKeyboardButton(t("home_back_to_menu", lang), callback_data="home:back"))
    return kb
