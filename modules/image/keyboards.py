"""Inline keyboards for the image generation module."""

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from modules.i18n import t

from .settings import DEFAULT_SIZE_KEY, IMAGE_SIZE_ORDER
from .texts import size_label


def menu_keyboard(lang: str, selected_size: str | None = None) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    current = selected_size or DEFAULT_SIZE_KEY

    for index in range(0, len(IMAGE_SIZE_ORDER), 2):
        row_keys = IMAGE_SIZE_ORDER[index : index + 2]
        buttons = []
        for key in row_keys:
            label = size_label(lang, key)
            if key == current:
                label = f"✅ {label}"
            buttons.append(
                InlineKeyboardButton(label, callback_data=f"image:size:{key}")
            )
        kb.row(*buttons)

    kb.add(InlineKeyboardButton(t("back", lang), callback_data="image:back"))
    return kb


def no_credit_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(t("btn_credit", lang), callback_data="home:credit"),
    )
    kb.row(InlineKeyboardButton(t("back", lang), callback_data="image:back"))
    return kb
