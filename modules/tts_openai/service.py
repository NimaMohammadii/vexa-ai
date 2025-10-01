"""HTTP client for OpenAI text-to-speech."""

from __future__ import annotations

import json
from typing import Final

import requests

from modules.gpt.service import resolve_gpt_api_key

_OPENAI_TTS_URL: Final[str] = "https://api.openai.com/v1/audio/speech"
_MODEL_ID: Final[str] = "gpt-4o-mini-tts"


def synthesize(text: str, voice: str, mime: str = "audio/mpeg") -> bytes:
    api_key = resolve_gpt_api_key()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": mime,
    }
    payload = {
        "model": _MODEL_ID,
        "voice": voice,
        "input": text,
    }

    response = requests.post(
        _OPENAI_TTS_URL,
        headers=headers,
        data=json.dumps(payload),
        timeout=120,
    )
    response.raise_for_status()
    return response.content

