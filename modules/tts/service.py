# modules/tts/service.py
import os
import json
import requests
from io import BytesIO
from typing import Optional, List, Dict, Any

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY", "")
MODEL_ID = "eleven_v3"  # مدل ثابت

# اختیاری: اگر خواستی خروجی‌ها را به فرمت/بیت‌ریت متفاوت ترنسکُد کنی
try:
    from pydub import AudioSegment  # نیازمند ffmpeg در سیستم
except Exception:
    AudioSegment = None


def synthesize(text: str, voice_id: str, mime: str = "audio/mpeg") -> bytes:
    """
    یک بار درخواست non-stream به ElevenLabs (v3) برای تولید صدا.
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


def _mime_to_format(m: str) -> str:
    """
    نگاشت MIME به فرمت خروجی pydub/ffmpeg
    """
    m = (m or "").lower()
    if "mpeg" in m or "mp3" in m:
        return "mp3"
    if "wav" in m or "x-wav" in m:
        return "wav"
    if "ogg" in m:
        return "ogg"
    return "mp3"


def _transcode_audio(
    input_bytes: bytes,
    in_mime: str,
    out_mime: str,
    bitrate: Optional[str] = None,
) -> bytes:
    """
    ترنسکُد صدا با pydub (اختیاری). اگر pydub یا ffmpeg در دسترس نبود، همان بایت اولیه را برمی‌گرداند.
    """
    if AudioSegment is None:
        # در صورت نبود pydub/ffmpeg، همان ورودی را تحویل بده
        return input_bytes

    in_fmt = _mime_to_format(in_mime)
    out_fmt = _mime_to_format(out_mime)

    bio_in = BytesIO(input_bytes)
    audio = AudioSegment.from_file(bio_in, format=in_fmt)

    bio_out = BytesIO()
    export_args: Dict[str, Any] = {}
    if bitrate and out_fmt == "mp3":
        # تنظیم بیت‌ریت فقط وقتی mp3 است معنی دارد، مثال: "128k"
        export_args["bitrate"] = bitrate

    audio.export(bio_out, format=out_fmt, **export_args)
    return bio_out.getvalue()


def fanout_outputs(
    base_audio: bytes,
    outputs: List[Dict[str, Any]],
    in_mime: str = "audio/mpeg",
) -> List[bytes]:
    """
    از یک بار خروجی ElevenLabs چند خروجی بساز:
    - اگر MIME مقصد با ورودی یکی بود، همان بایت‌ها را تکرار می‌کنیم (بدون تماس مجدد).
    - اگر متفاوت بود و pydub/ffmpeg موجود بود، ترنسکُد می‌کنیم.
    - اگر ترنسکُد در دسترس/موفق نبود، همان ورودی را تکرار می‌کنیم.
    """
    if not outputs:
        return [base_audio]

    results: List[bytes] = []
    in_mime_lc = (in_mime or "").lower()

    for out in outputs:
        out_mime = (out.get("mime") or "audio/mpeg").lower()
        bitrate = out.get("bitrate")  # اختیاری: مثل "128k" یا "64k"

        if out_mime == in_mime_lc:
            # همان را تکرار کن
            results.append(base_audio)
            continue

        try:
            data = _transcode_audio(base_audio, in_mime, out_mime, bitrate=bitrate)
            results.append(data)
        except Exception:
            # در صورت خطا/نبود ترنسکُد، همان را تکرار کن
            results.append(base_audio)

    return results
