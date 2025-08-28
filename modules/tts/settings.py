# modules/tts/settings.py

# مدل
MODEL_ID = "eleven_v3"

# هزینه هر کاراکتر
CREDIT_PER_CHAR = 1

# خروجی‌ها: دو فایل MP3
OUTPUTS = [
    {"mime": "audio/mpeg"},
    {"mime": "audio/mpeg"},
]

# صداها (اسم → Voice ID)
VOICES = {
    "Liam": "TX3LPaxmHKxFdv7VOQHJ",
    "Amir": "PleK417YVMP2SUWm8Btb",
    "Nazy": "WwAjIyMBDBNl1dvId9Xe",
    "Noushin": "NZiuR1C6kVMSWHG27sIM",
    "Alexandra": "kdmDKE6EkgrWrrykO9Qt",
    "Chris": "iP95p4xoKVk53GoZ742B",
    "Laura": "FGY2WhTYpPnrIDTdsKH5",
    "Jessica": "cgSgspJ2msm6clMCkdW9",
}
DEFAULT_VOICE_NAME = "Amir"

# تنظیمات «ایمن و طبیعی» برای v3:
# - stability باید یکی از {0.0, 0.5, 1.0} باشد ⇒ 0.5 طبیعی
# - similarity_boost کمی بالا برای وضوح فارسی
# - style کم برای اغراق‌نشدن
# - speed نزدیک 1.0
VOICE_SETTINGS_NATURAL = {
    "stability": 0.5,
    "similarity_boost": 0.80,
    "style": 0.12,
    "use_speaker_boost": True,
    "speed": 1.0,
}

# state دریافت متن
STATE_WAIT_TEXT = "tts:wait_text"