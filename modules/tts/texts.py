# modules/tts/texts.py
# نسخه‌ی ساده فقط فارسی؛ امضاها (پارامتر lang) حفظ شده تا کدهای دیگه نشکنه.

def ask_text(lang: str, voice_name: str) -> str:
    return (
        "🎧 <b>تبدیل متن به صدا</b>\n\n"
        f"🔊 صدای انتخابی: <b>{voice_name}</b>\n"
        "✍️ متن رو بفرست (هر کاراکتر = 1 کردیت).\n"
        "👇 بعد از تبدیل، دو فایل MP3 برات می‌فرستم."
    )

def PROCESSING(lang: str) -> str:
    return "⏳ در حال تبدیل..."

def NO_CREDIT(lang: str) -> str:
    return "❌ موجودی کردیت شما کافی نیست."

def ERROR(lang: str) -> str:
    return "⚠️ خطا در تبدیل. دوباره تلاش کن."