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
    "fa": "Liam",
    "en": "Ava",
    "ar": "Liam",
    "tr": "Melis",
    "ru": "Алина",
    "es": "Valeria",
    "de": "Lena",
    "fr": "Léa",
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
        "Austin": "Bj9UqZbhQsanLzgalpEG",
        "priyanka": "BpjGufoPiobT79j2vtj4",
        "horatius": "qXpMhyvQqiRxWQs4qSSB",
        "anika": "Sm1seazb4gs7RSlUVw7c",
        "brock": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Bradford": "NNl6r8mD7vthiJatiJt1",
    },
    "en": {
        "Liam": "TX3LPaxmHKxFdv7VOQHJ",
        "Noah": "1SM7GgM6IMuvQlz2BwM3",
        "Ava": "tnSpp4vdxKPjI9w0GnoV",
        "Nora": "BIvP0GN1cAtSRTxNHnWS",
        "Alex": "GFGuOkimbpNkTEOVDkqX",
        "Ella": "NZiuR1C6kVMSWHG27sIM",
        "Chloe": "BZgkqPqms7Kj9ulSkVzn",
        "Alexandra": "kdmDKE6EkgrWrrykO9Qt",
        "Laura": "7piC4m7q8WrpEAnMj5xC",
        "Maxon": "0dPqNXnhg2bmxQv1WKDp",
        "Jessica": "cgSgspJ2msm6clMCkdW9",
        "Austin": "Bj9UqZbhQsanLzgalpEG",
        "priyanka": "BpjGufoPiobT79j2vtj4",
        "horatius": "qXpMhyvQqiRxWQs4qSSB",
        "anika": "Sm1seazb4gs7RSlUVw7c",
        "brock": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Lucas": "NNl6r8mD7vthiJatiJt1",
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
        "Austin": "Bj9UqZbhQsanLzgalpEG",
        "priyanka": "BpjGufoPiobT79j2vtj4",
        "horatius": "qXpMhyvQqiRxWQs4qSSB",
        "anika": "Sm1seazb4gs7RSlUVw7c",
        "brock": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Bradford": "NNl6r8mD7vthiJatiJt1",
    },
    "tr": {
        "Arda": "TX3LPaxmHKxFdv7VOQHJ",
        "Emre": "1SM7GgM6IMuvQlz2BwM3",
        "Deniz": "tnSpp4vdxKPjI9w0GnoV",
        "Sarah": "BIvP0GN1cAtSRTxNHnWS",
        "Burak": "GFGuOkimbpNkTEOVDkqX",
        "Selin": "NZiuR1C6kVMSWHG27sIM",
        "Duru": "BZgkqPqms7Kj9ulSkVzn",
        "Elif": "kdmDKE6EkgrWrrykO9Qt",
        "İrem": "7piC4m7q8WrpEAnMj5xC",
        "Mert": "0dPqNXnhg2bmxQv1WKDp",
        "Asya": "cgSgspJ2msm6clMCkdW9",
        "Derya": "Bj9UqZbhQsanLzgalpEG",
        "priyanka": "BpjGufoPiobT79j2vtj4",
        "horatius": "qXpMhyvQqiRxWQs4qSSB",
        "anika": "Sm1seazb4gs7RSlUVw7c",
        "Ozan": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Kaan": "NNl6r8mD7vthiJatiJt1",
    },
    "ru": {
        "Илья": "TX3LPaxmHKxFdv7VOQHJ",
        "Никита": "1SM7GgM6IMuvQlz2BwM3",
        "Алина": "tnSpp4vdxKPjI9w0GnoV",
        "Милана": "BIvP0GN1cAtSRTxNHnWS",
        "Даниил": "GFGuOkimbpNkTEOVDkqX",
        "София": "NZiuR1C6kVMSWHG27sIM",
        "Ева": "BZgkqPqms7Kj9ulSkVzn",
        "Полина": "kdmDKE6EkgrWrrykO9Qt",
        "Кира": "7piC4m7q8WrpEAnMj5xC",
        "Maxon": "0dPqNXnhg2bmxQv1WKDp",
        "Дарья": "cgSgspJ2msm6clMCkdW9",
        "Austin": "Bj9UqZbhQsanLzgalpEG",
        "priyanka": "BpjGufoPiobT79j2vtj4",
        "horatius": "qXpMhyvQqiRxWQs4qSSB",
        "Вероника": "Sm1seazb4gs7RSlUVw7c",
        "brock": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Матвей": "NNl6r8mD7vthiJatiJt1",
    },
    "es": {
        "Mateo": "TX3LPaxmHKxFdv7VOQHJ",
        "Leo": "1SM7GgM6IMuvQlz2BwM3",
        "Valeria": "tnSpp4vdxKPjI9w0GnoV",
        "Sofía": "BIvP0GN1cAtSRTxNHnWS",
        "Diego": "GFGuOkimbpNkTEOVDkqX",
        "Camila": "NZiuR1C6kVMSWHG27sIM",
        "Luna": "BZgkqPqms7Kj9ulSkVzn",
        "Renata": "kdmDKE6EkgrWrrykO9Qt",
        "Martina": "7piC4m7q8WrpEAnMj5xC",
        "Bruno": "0dPqNXnhg2bmxQv1WKDp",
        "Paula": "cgSgspJ2msm6clMCkdW9",
        "Tomás": "Bj9UqZbhQsanLzgalpEG",
        "Elena": "BpjGufoPiobT79j2vtj4",
        "horatius": "qXpMhyvQqiRxWQs4qSSB",
        "Abril": "Sm1seazb4gs7RSlUVw7c",
        "brock": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Andrés": "NNl6r8mD7vthiJatiJt1",
    },
    "de": {
        "Leon": "TX3LPaxmHKxFdv7VOQHJ",
        "Luca": "1SM7GgM6IMuvQlz2BwM3",
        "Lena": "tnSpp4vdxKPjI9w0GnoV",
        "Mia": "BIvP0GN1cAtSRTxNHnWS",
        "Finn": "GFGuOkimbpNkTEOVDkqX",
        "Emma": "NZiuR1C6kVMSWHG27sIM",
        "Lea": "BZgkqPqms7Kj9ulSkVzn",
        "Hannah": "kdmDKE6EkgrWrrykO9Qt",
        "Laura": "7piC4m7q8WrpEAnMj5xC",
        "Jonas": "0dPqNXnhg2bmxQv1WKDp",
        "Nina": "cgSgspJ2msm6clMCkdW9",
        "Paul": "Bj9UqZbhQsanLzgalpEG",
        "Clara": "BpjGufoPiobT79j2vtj4",
        "Max": "qXpMhyvQqiRxWQs4qSSB",
        "Sophie": "Sm1seazb4gs7RSlUVw7c",
        "Noah": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Tim": "NNl6r8mD7vthiJatiJt1",
    },
    "fr": {
        "Hugo": "TX3LPaxmHKxFdv7VOQHJ",
        "Noah": "1SM7GgM6IMuvQlz2BwM3",
        "Léa": "tnSpp4vdxKPjI9w0GnoV",
        "Inès": "BIvP0GN1cAtSRTxNHnWS",
        "Theo": "GFGuOkimbpNkTEOVDkqX",
        "Emma": "NZiuR1C6kVMSWHG27sIM",
        "Jade": "BZgkqPqms7Kj9ulSkVzn",
        "Mila": "kdmDKE6EkgrWrrykO9Qt",
        "Louise": "7piC4m7q8WrpEAnMj5xC",
        "Jules": "0dPqNXnhg2bmxQv1WKDp",
        "Jessica": "cgSgspJ2msm6clMCkdW9",
        "Adrien": "Bj9UqZbhQsanLzgalpEG",
        "Nina": "BpjGufoPiobT79j2vtj4",
        "horatius": "qXpMhyvQqiRxWQs4qSSB",
        "Zoé": "Sm1seazb4gs7RSlUVw7c",
        "brock": "DGzg6RaUqxGRTHSBjfgF",
        "Xavier": "YOq2y2Up4RgXP2HyXjE5",
        "Paul": "NNl6r8mD7vthiJatiJt1",
    },
}

DEMO_AUDIO_BY_VOICE = {
    # "Liam": "<TELEGRAM_FILE_ID_OR_URL>",
}

DEFAULT_OUTPUT_MODE = "mp3"
OUTPUT_MODES = {"mp3", "voice"}

def _demo_setting_key(voice_name: str, lang: str | None = None) -> str:
    if lang:
        return f"TTS_DEMO_{lang}_{voice_name}"
    return f"TTS_DEMO_{voice_name}"

def _output_setting_key(user_id: int) -> str:
    return f"TTS_OUTPUT_{user_id}"

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

def get_output_mode(user_id: int, default: str = DEFAULT_OUTPUT_MODE) -> str:
    mode = db.get_setting(_output_setting_key(user_id), default) or default
    return mode if mode in OUTPUT_MODES else default

def set_output_mode(user_id: int, mode: str) -> None:
    normalized = (mode or "").strip().lower()
    if normalized not in OUTPUT_MODES:
        normalized = DEFAULT_OUTPUT_MODE
    db.set_setting(_output_setting_key(user_id), normalized)

# خروجی‌ها (هر کدوم یک فایل MP3)
OUTPUTS = [
    {"mime": "audio/mpeg"},
]

# فهرست کلمات غیرمجاز برای تبدیل متن به صدا
BANNED_WORDS = [
    "کوص",
]
