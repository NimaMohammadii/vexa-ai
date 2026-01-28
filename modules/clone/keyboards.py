# modules/clone/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from modules.i18n import t


def menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup()


def payment_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(t("clone_confirm_btn", lang), callback_data="clone:confirm_payment"),
    )
    return kb


def no_credit_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(t("clone_buy_credit_btn", lang), callback_data="credit:menu"),
    )
    return kb
