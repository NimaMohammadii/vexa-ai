# modules/tts/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.i18n import t
from .settings import VOICES

def _chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

def keyboard(selected_voice: str, lang: str = "fa"):
    kb = InlineKeyboardMarkup(row_width=2)
    names = list(VOICES.keys())
    for row in _chunk(names, 2):
        kb.row(*[
            InlineKeyboardButton(("✅ " if n == selected_voice else "") + n,
                                 callback_data=f"tts:voice:{n}")
            for n in row
        ])
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb