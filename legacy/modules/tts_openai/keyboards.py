"""Keyboards for the OpenAI TTS flow."""

from __future__ import annotations

from modules.tts.keyboards import keyboard as base_keyboard
from modules.tts.settings import get_output_mode
from .settings import VOICES


def keyboard(selected_voice: str, lang: str = "fa", user_id: int | None = None):
    output_mode = get_output_mode(user_id) if user_id is not None else "mp3"
    return base_keyboard(
        selected_voice,
        lang,
        user_id,
        voices=VOICES,
        prefix="tts_openai",
        include_custom=False,
        quality="medium",
        show_demo_button=False,
        output_mode=output_mode,
        voice_filter_lang="openai",
    )
