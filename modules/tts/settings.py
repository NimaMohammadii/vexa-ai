# modules/tts/settings.py

# نام State برای انتظار متن
STATE_WAIT_TEXT = "tts:wait_text"

# هر کاراکتر = 1 کردیت
CREDIT_PER_CHAR = 1

# صدای پیش‌فرض (وقتی هنوز چیزی ذخیره نشده)
DEFAULT_VOICE_NAME = "Amir"

# لیست صداها: name -> eleven voice_id
VOICES = {
    "Liam":      "TX3LPaxmHKxFdv7VOQHJ",
    "Amir":      "PleK417YVMP2SUWm8Btb",
    "Nazy":      "WwAjIyMBDBNl1dvId9Xe",
    "Noushin":   "NZiuR1C6kVMSWHG27sIM",
    "Alexandra": "kdmDKE6EkgrWrrykO9Qt",
    "Chris":     "iP95p4xoKVk53GoZ742B",
    "Laura":     "FGY2WhTYpPnrIDTdsKH5",
    "Jessica":   "cgSgspJ2msm6clMCkdW9",
}

# خروجی‌ها (هر کدوم یک فایل MP3)
OUTPUTS = [
    {"mime": "audio/mpeg"},
    {"mime": "audio/mpeg"},
]
