# modules/tts/settings.py

# نام State برای انتظار متن
STATE_WAIT_TEXT = "tts:wait_text"

# هر کاراکتر = 0.05 کردیت
CREDIT_PER_CHAR = 0.05

# صدای پیش‌فرض (وقتی هنوز چیزی ذخیره نشده)
DEFAULT_VOICE_NAME = "Nazy"

# لیست صداها: name -> eleven voice_id
VOICES = {
    "Liam":      "TX3LPaxmHKxFdv7VOQHJ",
    "Amir":      "1SM7GgM6IMuvQlz2BwM3",
    "Nazy":      "tnSpp4vdxKPjI9w0GnoV",
    "Noushin":   "NZiuR1C6kVMSWHG27sIM",
    "Paniz":       "BZgkqPqms7Kj9ulSkVzn",
    "Alexandra": "kdmDKE6EkgrWrrykO9Qt",
    "Laura":     "7piC4m7q8WrpEAnMj5xC",
    "Maxon":     "0dPqNXnhg2bmxQv1WKDp",
    "Jessica":   "cgSgspJ2msm6clMCkdW9",
}

# خروجی‌ها (هر کدوم یک فایل MP3)
OUTPUTS = [
    {"mime": "audio/mpeg"},
]

# فهرست کلمات غیرمجاز برای تبدیل متن به صدا
BANNED_WORDS = [
    "کیر",
    "کص",
    "کیرم",
    "کصتو",
    "جنده",
    "کصکش",
    "کوص",
    "کسکش",
]
