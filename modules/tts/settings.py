# modules/tts/settings.py

# نام State برای انتظار متن
STATE_WAIT_TEXT = "tts:wait_text"

# هر کاراکتر = 1 کردیت
CREDIT_PER_CHAR = 1

# صدای پیش‌فرض (وقتی هنوز چیزی ذخیره نشده)
DEFAULT_VOICE_NAME = "Nazy"

# لیست صداها: name -> eleven voice_id
VOICES = {
    "Liam":      "TX3LPaxmHKxFdv7VOQHJ",
    "Amir":      "scOwDtmlUjD3prqpp97I",
    "Nazy":      "tnSpp4vdxKPjI9w0GnoV",
    "Noushin":   "NZiuR1C6kVMSWHG27sIM",
    "Paniz":       "BZgkqPqms7Kj9ulSkVzn",
    "Alexandra": "kdmDKE6EkgrWrrykO9Qt",
    "Nima":     "BognUUMX6W1qmZKB2TOw",
    "Laura":     "7piC4m7q8WrpEAnMj5xC",
    "Maxon":     "TPH31dCvEQ2aybIZHorF",
    "Jessica":   "cgSgspJ2msm6clMCkdW9",
}

# خروجی‌ها (هر کدوم یک فایل MP3)
OUTPUTS = [
    {"mime": "audio/mpeg"},
    {"mime": "audio/mpeg"},
]
