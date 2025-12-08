# modules/clone/service.py
import os
from io import BytesIO
from pathlib import Path

import requests

import db

PASS_THROUGH_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/aac",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
}

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY", "")


def _guess_audio_format(filename: str, mime: str | None) -> str | None:
    """Infer the audio format for pydub based on file metadata."""

    if mime:
        lowered = mime.lower()
        # Handle complex mime types like "audio/ogg; codecs=opus"
        if ";" in lowered:
            lowered = lowered.split(";")[0].strip()
        
        if "/" in lowered:
            format_hint = lowered.split("/")[-1]
            # Map opus to ogg since ffmpeg doesn't recognize 'opus' as input format
            # Opus audio is typically in OGG container
            if format_hint == "opus":
                return "ogg"
            return format_hint

    suffix = Path(filename or "").suffix.lower()
    if suffix.startswith("."):
        ext = suffix[1:]
        # Map opus extension to ogg format
        if ext == "opus":
            return "ogg"
        return ext

    return None


def _prepare_audio_payload(audio_bytes: bytes, filename: str, mime: str) -> tuple[bytes, str, str]:
    """Ensure the uploaded audio is in a format accepted by ElevenLabs.

    Telegram voice messages are usually `audio/ogg` (Opus) which ElevenLabs
    rejects. We convert unsupported formats to a 16-bit mono WAV to keep the
    cloning endpoint happy.
    """

    filename = filename or "audio.wav"
    mime = (mime or "audio/wav").lower()

    # همیشه فایل‌های Opus و OGG رو تبدیل کن
    if mime in PASS_THROUGH_MIME_TYPES and "ogg" not in mime and "opus" not in mime:
        return audio_bytes, filename, mime

    try:
        from pydub import AudioSegment  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "برای تبدیل فرمت صوتی، لطفاً pydub را نصب کنید: pip install pydub"
        ) from exc

    format_hint = _guess_audio_format(filename, mime)
    print(f"🎵 Converting audio: format={format_hint}, mime={mime}, size={len(audio_bytes)} bytes")

    try:
        audio = AudioSegment.from_file(BytesIO(audio_bytes), format=format_hint)
        print(f"✅ Audio loaded: duration={len(audio)}ms, channels={audio.channels}")
    except Exception as exc:
        print(f"❌ Audio conversion error: {exc}")
        raise RuntimeError(f"فرمت صوتی پشتیبانی نمی‌شود یا فایل خراب است: {exc}") from exc

    # تبدیل به 16-bit mono WAV با sample rate مناسب
    audio = audio.set_channels(1).set_frame_rate(44100).set_sample_width(2)
    buf = BytesIO()
    audio.export(buf, format="wav")

    safe_name = Path(filename).stem or "audio"
    converted_size = len(buf.getvalue())
    print(f"✅ Audio converted: {converted_size} bytes, format=wav")
    return buf.getvalue(), f"{safe_name}.wav", "audio/wav"


def clone_voice(audio_bytes: bytes, name: str, filename: str = "audio.wav", mime: str = "audio/wav") -> str:
    if not ELEVEN_API_KEY:
        raise RuntimeError("ELEVEN_API_KEY is missing")

    url = "https://api.elevenlabs.io/v1/voices/add"
    headers = {"xi-api-key": ELEVEN_API_KEY}

    audio_bytes, filename, mime = _prepare_audio_payload(audio_bytes, filename, mime)

    # ElevenLabs API requires specific parameters
    files = {"files": (filename, audio_bytes, mime)}
    data = {
        "name": name,
        "description": f"Custom voice created from {filename}",
        "labels": "{}"  # Empty JSON object as string
    }
    
    try:
        r = requests.post(url, headers=headers, files=files, data=data, timeout=120)
        
        # Get detailed error info if request fails
        if r.status_code != 200:
            error_detail = "Unknown error"
            try:
                error_json = r.json()
                error_detail = error_json.get("detail", {})
                if isinstance(error_detail, dict):
                    error_detail = error_detail.get("message", str(error_detail))
                elif isinstance(error_detail, list) and error_detail:
                    error_detail = str(error_detail[0])
            except:
                error_detail = r.text[:200]
            
            raise RuntimeError(f"ElevenLabs API Error {r.status_code}: {error_detail}")
        
        j = r.json()
        voice_id = j.get("voice_id") or (j.get("voice") or {}).get("voice_id")
        
        if not voice_id:
            raise RuntimeError(f"No voice_id returned from API: {j}")
            
        return voice_id
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Network error calling ElevenLabs API: {str(e)}")

def list_voices():
    """دریافت لیست همه صداهای الون لبز"""
    if not ELEVEN_API_KEY:
        raise RuntimeError("ELEVEN_API_KEY is missing")
    
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {"xi-api-key": ELEVEN_API_KEY}
    
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json().get("voices", [])
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to list voices: {str(e)}")

def delete_voice(voice_id: str):
    """حذف صدا از الون لبز"""
    if not ELEVEN_API_KEY:
        raise RuntimeError("ELEVEN_API_KEY is missing")
    
    url = f"https://api.elevenlabs.io/v1/voices/{voice_id}"
    headers = {"xi-api-key": ELEVEN_API_KEY}
    
    try:
        r = requests.delete(url, headers=headers, timeout=30)
        r.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to delete voice {voice_id}: {str(e)}")

def cleanup_old_voices(max_voices=25):
    """حذف خودکار صداهای قدیمی وقتی به حد مجاز نزدیک میشیم"""
    try:
        # دریافت تمام صداها از الون لبز
        voices = list_voices()
        print(f"📋 Total voices in ElevenLabs: {len(voices)}")
        
        # فیلتر کردن صداهای کاستوم (فقط cloned)
        custom_voices = []
        for voice in voices:
            voice_category = voice.get("category", "").lower()
            
            # فقط صداهای cloned رو در نظر بگیر
            # صداهای premade و generated رو نگه دار
            if voice_category == "cloned" and voice.get("voice_id"):
                custom_voices.append(voice)
                print(f"  - Cloned voice: {voice.get('name')} (ID: {voice.get('voice_id')[:8]}...)")
        
        print(f"🎤 Found {len(custom_voices)} cloned voices")
        
        # اگر بیش از حد مجاز صدا داریم، قدیمی‌ترین‌ها رو حذف کن
        if len(custom_voices) >= max_voices:
            # مرتب‌سازی بر اساس تاریخ ایجاد (قدیمی‌ترین‌ها اول)
            custom_voices.sort(key=lambda x: x.get("date_unix", 0))
            
            # تعداد صداهایی که باید حذف بشن (حداقل 3 صدا پاک کن تا فضا باز بشه)
            voices_to_delete = max(3, len(custom_voices) - max_voices + 5)
            
            print(f"🗑️ Deleting {voices_to_delete} old voices...")
            deleted_count = 0
            
            for i in range(min(voices_to_delete, len(custom_voices))):
                voice_to_delete = custom_voices[i]
                voice_id = voice_to_delete.get("voice_id")
                voice_name = voice_to_delete.get("name", "Unknown")
                
                try:
                    delete_voice(voice_id)
                    deleted_count += 1
                    print(f"  ✅ Deleted: {voice_name} ({voice_id[:8]}...)")
                    
                    # حذف از دیتابیس محلی هم
                    db.delete_user_voice_by_voice_id(voice_id)
                    
                except Exception as e:
                    print(f"  ❌ Failed to delete {voice_name}: {e}")
            
            print(f"✅ Cleanup complete: {deleted_count}/{voices_to_delete} voices deleted")
            return deleted_count > 0
                    
        print("✅ No cleanup needed")
        return True
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def clone_voice_with_cleanup(audio_bytes: bytes, name: str, filename: str = "audio.wav", mime: str = "audio/wav") -> str:
    """ساخت صدا با مدیریت خودکار صداهای قدیمی"""
    try:
        # ابتدا سعی کن صدا رو مستقیم بسازی
        return clone_voice(audio_bytes, name, filename, mime)
        
    except RuntimeError as e:
        error_str = str(e).lower()
        
        # اگر خطا مربوط به محدودیت تعداد صدا بود
        if "maximum amount" in error_str or "voice limit" in error_str:
            print("Voice limit reached, cleaning up old voices...")
            
            # پاک‌سازی صداهای قدیمی
            if cleanup_old_voices():
                print("Cleanup successful, trying to create voice again...")
                # دوباره تلاش کن
                return clone_voice(audio_bytes, name, filename, mime)
            else:
                raise RuntimeError("Failed to cleanup old voices. Please manually delete some voices or upgrade your plan.")
        else:
            # خطای دیگه‌ای بود، همون رو بفرست
            raise e
