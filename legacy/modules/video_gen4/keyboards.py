"""Inline keyboards for the Gen-4 video module."""

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from modules.i18n import t


def menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup()


def no_credit_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton(t("btn_credit", lang), callback_data="home:credit"))
    return kb
