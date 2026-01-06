"""Keyboards for the OpenAI TTS flow."""

from __future__ import annotations

from modules.tts.keyboards import keyboard as base_keyboard
from .settings import VOICES


def keyboard(selected_voice: str, lang: str = "fa", user_id: int | None = None):
    return base_keyboard(
        selected_voice,
        lang,
        user_id,
        voices=VOICES,
        prefix="tts_openai",
        include_custom=False,
        quality="medium",
        show_demo_button=False,
    )
