# modules/tts/service.py
import os
import json
import requests
from typing import List, Dict, Any

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY", "")
MODEL_ID = "eleven_v3"  # مدل ثابت


def synthesize(text: str, voice_id: str, mime: str = "audio/mpeg") -> bytes:
    """
    ارسال یک درخواست non-stream (stable quality) به ElevenLabs برای تولید صدا.
    فقط یک بار برای هر متن صدا زده میشود.
    """
    if not ELEVEN_API_KEY:
        raise RuntimeError("ELEVEN_API_KEY is missing")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "accept": mime,
        "content-type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": MODEL_ID,
    }

    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
    r.raise_for_status()
    return r.content


def fanout_outputs(base_audio: bytes, outputs: List[Dict[str, Any]]) -> List[bytes]:
    """
    بدون هیچ ترنسکُدی، همان بایتهای دریافتی از ElevenLabs را به تعداد خروجیهای خواستهشده تکثیر میکند.
    این کار تضمین میکند که مصرف API فقط یکبار باشد و هیچ وابستگی خارجی (ffmpeg/pydub) لازم نباشد.
    """
    if not outputs:
        return [base_audio]
    return [base_audio for _ in outputs]
