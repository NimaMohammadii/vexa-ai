# modules/tts/settings.py
import db

# نام State برای انتظار متن
STATE_WAIT_TEXT = "tts:wait_text"

# هر کاراکتر = 0.05 کردیت
CREDIT_PER_CHAR = 1

# زبان پیش‌فرض (برای زمانی که زبان کاربر مشخص نیست)
DEFAULT_LANGUAGE = "fa"

# صدای پیش‌فرض برای هر زبان (وقتی هنوز چیزی ذخیره نشده)
DEFAULT_VOICE_NAME_BY_LANG = {
    "fa": "Nazy",
    "en": "Nazy",
    "ar": "Nazy",
    "tr": "Nazy",
    "ru": "Nazy",
    "es": "Nazy",
    "de": "Nazy",
    "fr": "Nazy",
}

# لیست صداها به تفکیک زبان: name -> eleven voice_id
# فعلاً برای همه زبان‌ها یکسان گذاشته شده تا بعداً خودت تغییر بدی.
VOICES_BY_LANG = {
    "fa": {
        "Liam": "TX3LPaxmHKxFdv7VOQHJ",
        "Amir": "1SM7GgM6IMuvQlz2BwM3",
        "Nazy": "tnSpp4vdxKPjI9w0GnoV",
        "Sarah": "BIvP0GN1cAtSRTxNHnWS",
        "Alex": "GFGuOkimbpNkTEOVDkqX",
        "Noushin": "NZiuR1C6kVMSWHG27sIM",
        "Paniz": "BZgkqPqms7Kj9ulSkVzn",
        "Alexandra": "kdmDKE6EkgrWrrykO9Qt",
        "Laura": "7piC4m7q8WrpEAnMj5xC",
        "Maxon": "0dPqNXnhg2bmxQv1WKDp",
        "Jessica": "cgSgspJ2msm6clMCkdW9",
    },
    "en": {
        "Liam": "TX3LPaxmHKxFdv7VOQHJ",
        "Amir": "1SM7GgM6IMuvQlz2BwM3",
        "Nazy": "tnSpp4vdxKPjI9w0GnoV",
        "Sarah": "BIvP0GN1cAtSRTxNHnWS",
        "Alex": "GFGuOkimbpNkTEOVDkqX",
        "Noushin": "NZiuR1C6kVMSWHG27sIM",
        "Paniz": "BZgkqPqms7Kj9ulSkVzn",
        "Alexandra": "kdmDKE6EkgrWrrykO9Qt",
        "Laura": "7piC4m7q8WrpEAnMj5xC",
        "Maxon": "0dPqNXnhg2bmxQv1WKDp",
        "Jessica": "cgSgspJ2msm6clMCkdW9",
    },
    "ar": {
        "Liam": "TX3LPaxmHKxFdv7VOQHJ",
        "Amir": "1SM7GgM6IMuvQlz2BwM3",
        "Nazy": "tnSpp4vdxKPjI9w0GnoV",
        "Sarah": "BIvP0GN1cAtSRTxNHnWS",
        "Alex": "GFGuOkimbpNkTEOVDkqX",
        "Noushin": "NZiuR1C6kVMSWHG27sIM",
        "Paniz": "BZgkqPqms7Kj9ulSkVzn",
        "Alexandra": "kdmDKE6EkgrWrrykO9Qt",
        "Laura": "7piC4m7q8WrpEAnMj5xC",
        "Maxon": "0dPqNXnhg2bmxQv1WKDp",
        "Jessica": "cgSgspJ2msm6clMCkdW9",
    },
    "tr": {
        "Liam": "TX3LPaxmHKxFdv7VOQHJ",
        "Amir": "1SM7GgM6IMuvQlz2BwM3",
        "Nazy": "tnSpp4vdxKPjI9w0GnoV",
        "Sarah": "BIvP0GN1cAtSRTxNHnWS",
        "Alex": "GFGuOkimbpNkTEOVDkqX",
        "Noushin": "NZiuR1C6kVMSWHG27sIM",
        "Paniz": "BZgkqPqms7Kj9ulSkVzn",
        "Alexandra": "kdmDKE6EkgrWrrykO9Qt",
        "Laura": "7piC4m7q8WrpEAnMj5xC",
        "Maxon": "0dPqNXnhg2bmxQv1WKDp",
        "Jessica": "cgSgspJ2msm6clMCkdW9",
    },
    "ru": {
        "Liam": "TX3LPaxmHKxFdv7VOQHJ",
        "Amir": "1SM7GgM6IMuvQlz2BwM3",
        "Nazy": "tnSpp4vdxKPjI9w0GnoV",
        "Sarah": "BIvP0GN1cAtSRTxNHnWS",
        "Alex": "GFGuOkimbpNkTEOVDkqX",
        "Noushin": "NZiuR1C6kVMSWHG27sIM",
        "Paniz": "BZgkqPqms7Kj9ulSkVzn",
        "Alexandra": "kdmDKE6EkgrWrrykO9Qt",
        "Laura": "7piC4m7q8WrpEAnMj5xC",
        "Maxon": "0dPqNXnhg2bmxQv1WKDp",
        "Jessica": "cgSgspJ2msm6clMCkdW9",
    },
    "es": {
        "Liam": "TX3LPaxmHKxFdv7VOQHJ",
        "Amir": "1SM7GgM6IMuvQlz2BwM3",
        "Nazy": "tnSpp4vdxKPjI9w0GnoV",
        "Sarah": "BIvP0GN1cAtSRTxNHnWS",
        "Alex": "GFGuOkimbpNkTEOVDkqX",
        "Noushin": "NZiuR1C6kVMSWHG27sIM",
        "Paniz": "BZgkqPqms7Kj9ulSkVzn",
        "Alexandra": "kdmDKE6EkgrWrrykO9Qt",
        "Laura": "7piC4m7q8WrpEAnMj5xC",
        "Maxon": "0dPqNXnhg2bmxQv1WKDp",
        "Jessica": "cgSgspJ2msm6clMCkdW9",
    },
    "de": {
        "Liam": "TX3LPaxmHKxFdv7VOQHJ",
        "Amir": "1SM7GgM6IMuvQlz2BwM3",
        "Nazy": "tnSpp4vdxKPjI9w0GnoV",
        "Sarah": "BIvP0GN1cAtSRTxNHnWS",
        "Alex": "GFGuOkimbpNkTEOVDkqX",
        "Noushin": "NZiuR1C6kVMSWHG27sIM",
        "Paniz": "BZgkqPqms7Kj9ulSkVzn",
        "Alexandra": "kdmDKE6EkgrWrrykO9Qt",
        "Laura": "7piC4m7q8WrpEAnMj5xC",
        "Maxon": "0dPqNXnhg2bmxQv1WKDp",
        "Jessica": "cgSgspJ2msm6clMCkdW9",
    },
    "fr": {
        "Liam": "TX3LPaxmHKxFdv7VOQHJ",
        "Amir": "1SM7GgM6IMuvQlz2BwM3",
        "Nazy": "tnSpp4vdxKPjI9w0GnoV",
        "Sarah": "BIvP0GN1cAtSRTxNHnWS",
        "Alex": "GFGuOkimbpNkTEOVDkqX",
        "Noushin": "NZiuR1C6kVMSWHG27sIM",
        "Paniz": "BZgkqPqms7Kj9ulSkVzn",
        "Alexandra": "kdmDKE6EkgrWrrykO9Qt",
        "Laura": "7piC4m7q8WrpEAnMj5xC",
        "Maxon": "0dPqNXnhg2bmxQv1WKDp",
        "Jessica": "cgSgspJ2msm6clMCkdW9",
    },
}

DEMO_AUDIO_BY_VOICE = {
    # "Liam": "<TELEGRAM_FILE_ID_OR_URL>",
}

def _demo_setting_key(voice_name: str, lang: str | None = None) -> str:
    if lang:
        return f"TTS_DEMO_{lang}_{voice_name}"
    return f"TTS_DEMO_{voice_name}"

def get_default_voice_name(lang: str) -> str:
    return DEFAULT_VOICE_NAME_BY_LANG.get(lang, DEFAULT_VOICE_NAME_BY_LANG[DEFAULT_LANGUAGE])

def get_voices(lang: str) -> dict[str, str]:
    return VOICES_BY_LANG.get(lang, VOICES_BY_LANG[DEFAULT_LANGUAGE])

def get_demo_audio(voice_name: str, lang: str | None = None) -> dict[str, str] | None:
    stored = None
    if lang:
        stored = db.get_setting(_demo_setting_key(voice_name, lang))
    if not stored:
        stored = db.get_setting(_demo_setting_key(voice_name))
    if stored:
        if ":" in stored:
            kind, file_id = stored.split(":", 1)
        else:
            kind, file_id = "audio", stored
        return {"file_id": file_id, "kind": kind or "audio"}
    fallback = DEMO_AUDIO_BY_VOICE.get(voice_name)
    if not fallback:
        return None
    return {"file_id": fallback, "kind": "audio"}

def set_demo_audio(voice_name: str, file_id: str, *, kind: str = "audio", lang: str | None = None) -> None:
    db.set_setting(_demo_setting_key(voice_name, lang), f"{kind}:{file_id}")

def clear_demo_audio(voice_name: str, *, lang: str | None = None) -> None:
    db.set_setting(_demo_setting_key(voice_name, lang), "")

# خروجی‌ها (هر کدوم یک فایل MP3)
OUTPUTS = [
    {"mime": "audio/mpeg"},
]

# فهرست کلمات غیرمجاز برای تبدیل متن به صدا
BANNED_WORDS = [
    "کوص",
]
