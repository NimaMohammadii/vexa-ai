# modules/tts/keyboards.py
from __future__ import annotations

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from modules.i18n import t
from .settings import VOICES
import db


def _chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def keyboard(
    selected_voice: str,
    lang: str = "fa",
    user_id: int | None = None,
    *,
    voices: dict[str, str] | list[str] | None = None,
    prefix: str = "tts",
    include_custom: bool = True,
    quality: str = "pro",
):
    kb = InlineKeyboardMarkup(row_width=3)

    voice_source = voices or VOICES
    if isinstance(voice_source, dict):
        default_names = list(voice_source.keys())
    else:
        default_names = list(voice_source)

    custom_voices = []
    allow_custom = include_custom and user_id is not None
    if allow_custom:
        try:
            custom_voices = db.list_user_voices(user_id)  # [(voice_name, voice_id), ...]
        except Exception:
            custom_voices = []
    else:
        allow_custom = False

    all_names = default_names + ([voice[0] for voice in custom_voices] if allow_custom else [])

    for row in _chunk(all_names, 3):
        kb.row(
            *[
                InlineKeyboardButton(
                    ("✔️ " if n == selected_voice else "") + n,
                    callback_data=f"{prefix}:voice:{n}",
                )
                for n in row
            ]
        )

    if allow_custom and selected_voice:
        is_custom = any(voice[0] == selected_voice for voice in custom_voices)
        if is_custom:
            kb.add(
                InlineKeyboardButton(
                    "🗑 حذف این صدا", callback_data=f"{prefix}:delete:{selected_voice}"
                )
            )

    kb.row(
        InlineKeyboardButton(
            ("✔️ " if quality == "pro" else "") + t("tts_quality_pro", lang),
            callback_data=f"{prefix}:quality:pro",
        ),
        InlineKeyboardButton(
            ("✔️ " if quality == "medium" else "") + t("tts_quality_medium", lang),
            callback_data=f"{prefix}:quality:medium",
        ),
    )

    kb.add(InlineKeyboardButton(t("btn_clone", lang), callback_data="home:clone"))
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb


def no_credit_keyboard(lang: str = "fa"):
    """کیبورد برای پیام کردیت کافی نیست"""
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton("💳 خرید کردیت", callback_data="credit:menu"))
    return kb
