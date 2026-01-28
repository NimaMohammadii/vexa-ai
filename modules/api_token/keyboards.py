from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

from modules.i18n import t


def token_menu(lang: str) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(t("api_token_rotate", lang), callback_data="api:rotate")
    )
    return keyboard
