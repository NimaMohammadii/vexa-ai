"""Settings for the OpenAI text-to-speech flow."""

from __future__ import annotations

from modules.tts.settings import BANNED_WORDS as BASE_BANNED_WORDS


STATE_WAIT_TEXT = "tts_openai:wait_text"

# هر کاراکتر = 0.01 کردیت برای TTS اوپن‌اِی‌آی
CREDIT_PER_CHAR = 0.01

# صدای پیش‌فرض (وقتی هنوز انتخابی انجام نشده)
DEFAULT_VOICE_NAME = "Echo"

# نام صدا → مقدار موردنیاز برای API
VOICES = {
    "Echo": "echo",
    "Nova": "nova",
    "Alloy": "alloy",
    "Ash": "ash",
    "Marin": "marin",
    "Shimmer": "shimmer",
}

# خروجی‌ها (فرمت MP3)
OUTPUTS = [
    {"mime": "audio/mpeg"},
]

# همان فهرست کلمات غیرمجاز TTS اصلی
BANNED_WORDS = list(BASE_BANNED_WORDS)

