# modules/tts/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.i18n import t
from .settings import VOICES
import db

def _chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i+n]

def keyboard(selected_voice: str, lang: str = "fa", user_id: int = None):
    kb = InlineKeyboardMarkup(row_width=3)
    
    # صداهای پیش‌فرض
    default_names = list(VOICES.keys())
    
    # صداهای کاستوم کاربر
    custom_voices = []
    if user_id:
        try:
            custom_voices = db.list_user_voices(user_id)  # [(voice_name, voice_id), ...]
        except:
            pass
    
    # ترکیب صداهای پیش‌فرض و کاستوم
    all_names = default_names + [voice[0] for voice in custom_voices]
    
    for row in _chunk(all_names, 3):
        kb.row(*[
            InlineKeyboardButton(("✔️ " if n == selected_voice else "") + n,
                                 callback_data=f"tts:voice:{n}")
            for n in row
        ])

    # اگر صدای انتخابی کاستوم هست، دکمه حذف اضافه کن
    if user_id and selected_voice:
        is_custom = any(voice[0] == selected_voice for voice in custom_voices)
        if is_custom:
            kb.add(InlineKeyboardButton("🗑 حذف این صدا", callback_data=f"tts:delete:{selected_voice}"))

    # دکمه ساخت صدای شخصی همیشه قبل از بازگشت باشد
    kb.add(InlineKeyboardButton(t("btn_clone", lang), callback_data="home:clone"))

    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb

def no_credit_keyboard(lang: str = "fa"):
    """کیبورد برای پیام کردیت کافی نیست"""
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("💳 خرید کردیت", callback_data="credit:menu"))
    return kb
