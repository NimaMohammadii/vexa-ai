# modules/tts/service.py
import requests
from config import ELEVEN_API_KEY
from .settings import MODEL_ID, VOICE_SETTINGS_NATURAL

BASE = "https://api.elevenlabs.io/v1"

def synthesize(text: str, voice_id: str, mime: str):
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "accept": mime,
        "content-type": "application/json",
    }
    body = {
        "text": text,
        "model_id": MODEL_ID,                 # "eleven_v3"
        "voice_settings": VOICE_SETTINGS_NATURAL,
        "output_format": "mp3_44100_128",    # کیفیت مطمئن
    }
    url = f"{BASE}/text-to-speech/{voice_id}/stream"
    r = requests.post(url, headers=headers, json=body, timeout=120)
    if r.status_code != 200:
        try:
            err = r.json()
        except Exception:
            err = {"detail": r.text}
        raise RuntimeError(f"ElevenLabs error {r.status_code}: {err}")
    return r.content