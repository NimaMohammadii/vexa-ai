# modules/tts/settings.py
import db
import time

# نام State برای انتظار متن
STATE_WAIT_TEXT = "tts:wait_text"

# هر کاراکتر = 0.05 کردیت
CREDIT_PER_CHAR = 1

# زبان پیش‌فرض (برای زمانی که زبان کاربر مشخص نیست)
DEFAULT_LANGUAGE = "fa"

# صداهای رایگان (فعلاً ۳ تا انتخاب دلخواه)
# برای تغییر/حذف/اضافه کردن، فقط همین لیست را ویرایش کن.
FREE_VOICE_NAMES = [
    "Austin",
    "priyanka",
    "horatius",
]

# تنظیمات اشتراک صداها
# هر پلن => چند صدای اضافی قابل باز شدن + مدت زمان اشتراک (روز)
VOICE_SUBSCRIPTION_PLANS = {
    "creator": {"unlock_limit": 4, "duration_days": 30},
    "pro": {"unlock_limit": 9, "duration_days": 30},
    "studio": {"unlock_limit": 15, "duration_days": 30},
}

VOICE_SUBSCRIPTION_SECONDS = {
    name: plan["duration_days"] * 24 * 60 * 60 for name, plan in VOICE_SUBSCRIPTION_PLANS.items()
}

# صدای پیش‌فرض برای هر زبان (وقتی هنوز چیزی ذخیره نشده)
DEFAULT_VOICE_NAME_BY_LANG = {
    "fa": FREE_VOICE_NAMES[0],
    "en": FREE_VOICE_NAMES[0],
    "ar": FREE_VOICE_NAMES[0],
    "tr": FREE_VOICE_NAMES[0],
    "ru": FREE_VOICE_NAMES[0],
    "es": FREE_VOICE_NAMES[0],
    "de": FREE_VOICE_NAMES[0],
    "fr": FREE_VOICE_NAMES[0],
}

# لیست صداها به تفکیک زبان: name -> eleven voice_id
# فعلاً برای همه زبان‌ها یکسان گذاشته شده تا بعداً خودت تغییر بدی.
VOICES_BY_LANG = {
    "fa": {
        "Austin": "Bj9UqZbhQsanLzgalpEG",
        "priyanka": "BpjGufoPiobT79j2vtj4",
        "horatius": "qXpMhyvQqiRxWQs4qSSB",
        "anika": "Sm1seazb4gs7RSlUVw7c",
        "brock": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Bradford": "NNl6r8mD7vthiJatiJt1",
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
        "Austin": "Bj9UqZbhQsanLzgalpEG",
        "priyanka": "BpjGufoPiobT79j2vtj4",
        "horatius": "qXpMhyvQqiRxWQs4qSSB",
        "anika": "Sm1seazb4gs7RSlUVw7c",
        "brock": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Bradford": "NNl6r8mD7vthiJatiJt1",
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
        "Austin": "Bj9UqZbhQsanLzgalpEG",
        "priyanka": "BpjGufoPiobT79j2vtj4",
        "horatius": "qXpMhyvQqiRxWQs4qSSB",
        "anika": "Sm1seazb4gs7RSlUVw7c",
        "brock": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Bradford": "NNl6r8mD7vthiJatiJt1",
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
        "Austin": "Bj9UqZbhQsanLzgalpEG",
        "priyanka": "BpjGufoPiobT79j2vtj4",
        "horatius": "qXpMhyvQqiRxWQs4qSSB",
        "anika": "Sm1seazb4gs7RSlUVw7c",
        "brock": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Bradford": "NNl6r8mD7vthiJatiJt1",
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
        "Austin": "Bj9UqZbhQsanLzgalpEG",
        "priyanka": "BpjGufoPiobT79j2vtj4",
        "horatius": "qXpMhyvQqiRxWQs4qSSB",
        "anika": "Sm1seazb4gs7RSlUVw7c",
        "brock": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Bradford": "NNl6r8mD7vthiJatiJt1",
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
        "Austin": "Bj9UqZbhQsanLzgalpEG",
        "priyanka": "BpjGufoPiobT79j2vtj4",
        "horatius": "qXpMhyvQqiRxWQs4qSSB",
        "anika": "Sm1seazb4gs7RSlUVw7c",
        "brock": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Bradford": "NNl6r8mD7vthiJatiJt1",
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
        "Austin": "Bj9UqZbhQsanLzgalpEG",
        "priyanka": "BpjGufoPiobT79j2vtj4",
        "horatius": "qXpMhyvQqiRxWQs4qSSB",
        "anika": "Sm1seazb4gs7RSlUVw7c",
        "brock": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Bradford": "NNl6r8mD7vthiJatiJt1",
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
        "Austin": "Bj9UqZbhQsanLzgalpEG",
        "priyanka": "BpjGufoPiobT79j2vtj4",
        "horatius": "qXpMhyvQqiRxWQs4qSSB",
        "anika": "Sm1seazb4gs7RSlUVw7c",
        "brock": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Bradford": "NNl6r8mD7vthiJatiJt1",
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

def get_active_voice_subscription(user_id: int) -> dict | None:
    sub = db.get_user_voice_subscription(user_id)
    if not sub:
        return None
    now = int(time.time())
    if sub["expires_at"] > now:
        return sub
    db.clear_user_voice_subscription(user_id)
    return None

def get_voice_unlock_limit(user_id: int) -> int:
    sub = get_active_voice_subscription(user_id)
    if not sub:
        return 0
    plan = VOICE_SUBSCRIPTION_PLANS.get(sub["plan_name"])
    return plan["unlock_limit"] if plan else 0

def list_unlocked_voices(user_id: int) -> list[str]:
    return db.list_user_voice_unlocks(user_id)

def can_access_voice(user_id: int, voice_name: str) -> bool:
    if voice_name in FREE_VOICE_NAMES:
        return True
    limit = get_voice_unlock_limit(user_id)
    if limit <= 0:
        return False
    unlocked = list_unlocked_voices(user_id)[:limit]
    return voice_name in unlocked

def try_unlock_voice(user_id: int, voice_name: str) -> str:
    if voice_name in FREE_VOICE_NAMES:
        return "free"
    limit = get_voice_unlock_limit(user_id)
    if limit <= 0:
        return "no_subscription"
    unlocked = list_unlocked_voices(user_id)
    if voice_name in unlocked:
        return "already_unlocked"
    if len(unlocked) >= limit:
        return "limit_reached"
    db.add_user_voice_unlock(user_id, voice_name)
    return "unlocked"

def get_voice_access(user_id: int, lang: str) -> dict:
    voices = get_voices(lang)
    limit = get_voice_unlock_limit(user_id)
    unlocked = list_unlocked_voices(user_id) if limit > 0 else []
    unlocked = [name for name in unlocked if name in voices]
    allowed = set(FREE_VOICE_NAMES)
    if limit > 0:
        allowed.update(unlocked[:limit])
    locked = {name for name in voices.keys() if name not in allowed}
    available_slots = max(0, limit - len(unlocked))
    return {
        "allowed": allowed,
        "locked": locked,
        "available_slots": available_slots,
        "limit": limit,
    }

def apply_voice_subscription(user_id: int, plan_name: str) -> dict | None:
    plan = VOICE_SUBSCRIPTION_PLANS.get(plan_name)
    if not plan:
        return None
    now = int(time.time())
    current = db.get_user_voice_subscription(user_id)
    base = max(now, current["expires_at"]) if current and current["expires_at"] > now else now
    expires_at = base + VOICE_SUBSCRIPTION_SECONDS[plan_name]
    db.set_user_voice_subscription(user_id, plan_name, expires_at)
    return {"plan_name": plan_name, "expires_at": expires_at}

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
