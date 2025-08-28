# modules/tts/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from .settings import VOICES

def keyboard(selected_name: str, lang: str = "fa"):
    """
    دکمه انتخاب صدا (✅ روی صدای انتخاب‌شده)
    آرایش: 2تایی – 2تایی – 2تایی – 2تایی – برگشت
    """
    names = ["Liam", "Amir", "Nazy", "Noushin", "Alexandra", "Chris", "Laura", "Jessica"]
    kb = InlineKeyboardMarkup(row_width=2)

    row = []
    for i, name in enumerate(names, 1):
        label = f"{'✅ ' if name == selected_name else ''}{name}"
        row.append(InlineKeyboardButton(label, callback_data=f"tts:voice:{name}"))
        if i % 2 == 0:
            kb.row(*row); row = []
    if row:
        kb.row(*row)

    kb.add(InlineKeyboardButton("بازگشت ⬅️", callback_data="tts:back"))
    return kb