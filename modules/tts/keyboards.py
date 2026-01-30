# modules/tts/keyboards.py
from __future__ import annotations

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from modules.i18n import t
from .settings import get_voices
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
    show_demo_button: bool = True,
    output_mode: str = "mp3",
    page: int = 0,
):
    kb = InlineKeyboardMarkup(row_width=2)

    voice_source = voices or get_voices(lang)
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

    buttons_per_row = 2
    page_capacity = 9
    use_pagination = len(all_names) > page_capacity
    voice_capacity = page_capacity
    total_pages = max(1, (len(all_names) + voice_capacity - 1) // voice_capacity)
    current_page = max(0, min(page, total_pages - 1))
    start = current_page * voice_capacity
    page_names = all_names[start : start + voice_capacity]

    has_next = use_pagination and current_page < total_pages - 1
    has_prev = use_pagination and current_page > 0

    for row in _chunk(page_names, buttons_per_row):
        kb.row(
            *[
                InlineKeyboardButton(
                    ("✔️ " if n == selected_voice else "") + n,
                    callback_data=f"{prefix}:voice:{n}",
                )
                for n in row
            ]
        )

    if use_pagination and (has_prev or has_next):
        nav_buttons = []
        if has_prev:
            nav_buttons.append(
                InlineKeyboardButton(t("tts_prev", lang), callback_data=f"{prefix}:page:prev")
            )
        if has_next:
            nav_buttons.append(
                InlineKeyboardButton(t("tts_next", lang), callback_data=f"{prefix}:page:next")
            )
        kb.row(*nav_buttons)

    if allow_custom and selected_voice:
        is_custom = any(voice[0] == selected_voice for voice in custom_voices)
        if is_custom:
            kb.add(
                InlineKeyboardButton(
                    t("tts_delete_voice", lang),
                    callback_data=f"{prefix}:delete:{selected_voice}",
                )
            )

    if show_demo_button and selected_voice:
        kb.row(
            InlineKeyboardButton(
                t("tts_demo", lang),
                callback_data=f"{prefix}:demo:{selected_voice}",
            ),
        )
        kb.row(
            InlineKeyboardButton(
                ("✔️ " if output_mode == "mp3" else "") + t("tts_output_mp3", lang),
                callback_data=f"{prefix}:output:mp3",
            ),
            InlineKeyboardButton(
                ("✔️ " if output_mode == "voice" else "") + t("tts_output_voice", lang),
                callback_data=f"{prefix}:output:voice",
            ),
        )

    kb.add(InlineKeyboardButton(t("btn_clone", lang), callback_data="home:clone"))
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb


def no_credit_keyboard(lang: str = "fa"):
    """کیبورد برای پیام کردیت کافی نیست"""
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(t("btn_credit", lang), callback_data="credit:menu"))
    return kb
