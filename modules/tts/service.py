# modules/tts/service.py
import os, json, requests

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY", "")
MODEL_ID = "eleven_v3"  # مدل ثابت

def synthesize(text: str, voice_id: str, mime: str = "audio/mpeg") -> bytes:
    """
    v3 با کیفیت پایدار (non-stream). فقط text + model_id.
    """
    if not ELEVEN_API_KEY:
        raise RuntimeError("ELEVEN_API_KEY is missing")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"  # ← non-stream
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "accept": mime,
        "content-type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": MODEL_ID,   # ← داخل بدنه
        # عمداً هیچ voice_settings یا پارامتر اضافه‌ای نمی‌فرستیم
    }

    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
    r.raise_for_status()
    return r.content