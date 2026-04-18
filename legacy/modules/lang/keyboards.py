# modules/lang/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from modules.i18n import t


LANGS = [
    ("English", "en"),
    ("فارسی", "fa"),
    ("العربية", "ar"),
    ("Türkçe", "tr"),
    ("Русский", "ru"),
    ("Español", "es"),
    ("Deutsch", "de"),
    ("Français", "fr"),
]


def lang_menu(current: str, lang: str, *, show_back: bool = True) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    row = []
    for label, code in LANGS:
        mark = "• " if code == current else ""
        row.append(InlineKeyboardButton(mark + label, callback_data=f"lang:set:{code}"))
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    if show_back:
        kb.add(InlineKeyboardButton(t("back", lang), callback_data="lang:back"))
    return kb

