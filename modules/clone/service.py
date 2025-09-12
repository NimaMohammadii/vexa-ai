# modules/clone/service.py
import os, requests
import db

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY","")

def clone_voice(audio_bytes: bytes, name: str, filename: str = "audio.wav", mime: str = "audio/wav") -> str:
    if not ELEVEN_API_KEY:
        raise RuntimeError("ELEVEN_API_KEY is missing")

    url = "https://api.elevenlabs.io/v1/voices/add"
    headers = {"xi-api-key": ELEVEN_API_KEY}
    
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
        
        # فیلتر کردن صداهای کاستوم (غیر از صداهای پیش‌فرض)
        custom_voices = []
        for voice in voices:
            # صداهای پیش‌فرض معمولاً category دارن یا برچسب خاصی
            voice_category = voice.get("category", "")
            is_custom = voice_category in ["cloned", "generated", "professional"] or not voice_category
            
            if is_custom and voice.get("voice_id"):
                custom_voices.append(voice)
        
        print(f"Found {len(custom_voices)} custom voices")
        
        # اگر بیش از حد مجاز صدا داریم، قدیمی‌ترین‌ها رو حذف کن
        if len(custom_voices) >= max_voices:
            # مرتب‌سازی بر اساس تاریخ ایجاد (قدیمی‌ترین‌ها اول)
            custom_voices.sort(key=lambda x: x.get("date_unix", 0))
            
            # تعداد صداهایی که باید حذف بشن
            voices_to_delete = len(custom_voices) - max_voices + 1
            
            for i in range(voices_to_delete):
                voice_to_delete = custom_voices[i]
                voice_id = voice_to_delete.get("voice_id")
                voice_name = voice_to_delete.get("name", "Unknown")
                
                try:
                    delete_voice(voice_id)
                    print(f"Deleted old voice: {voice_name} ({voice_id})")
                    
                    # حذف از دیتابیس محلی هم
                    db.delete_user_voice_by_voice_id(voice_id)
                    
                except Exception as e:
                    print(f"Failed to delete voice {voice_name}: {e}")
                    
        return True
        
    except Exception as e:
        print(f"Cleanup failed: {e}")
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