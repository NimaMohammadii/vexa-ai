"""Inline keyboards used by the support module."""
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from modules.i18n import t


def support_entry_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(t("support_back", lang), callback_data="home:back"),
        InlineKeyboardButton(t("support_start_chat", lang), callback_data="support:start"),
    )
    return kb


def support_chat_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("support_end_chat", lang), callback_data="support:cancel"))
    return kb
