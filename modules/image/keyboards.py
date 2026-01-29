"""Inline keyboards for the image generation module."""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from modules.i18n import t


def menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="image:back"))
    return kb


def no_credit_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(t("btn_credit", lang), callback_data="home:credit"),
    )
    kb.row(InlineKeyboardButton(t("back", lang), callback_data="image:back"))
    return kb
