# modules/clone/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from modules.i18n import t


def menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb


def payment_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(t("clone_confirm_btn", lang), callback_data="clone:confirm_payment"),
        InlineKeyboardButton(t("clone_cancel_btn", lang), callback_data="home:back"),
    )
    return kb


def no_credit_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton(t("clone_buy_credit_btn", lang), callback_data="credit:menu"),
        InlineKeyboardButton(t("back", lang), callback_data="home:back"),
    )
    return kb
