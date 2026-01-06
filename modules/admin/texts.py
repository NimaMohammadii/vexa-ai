# modules/admin/texts.py

# ——— عنوان‌ها و متن‌های ثابت
TITLE = "🛠 پنل ادمین"
MENU  = (
    "از دکمه‌های زیر استفاده کنید:\n"
    "• آمار، کاربران، پیام‌رسانی\n"
    "• افزایش/کسر کردیت\n"
    "• تنظیمات و خروجی‌ها"
)

DENY = "⛔️ شما دسترسی به پنل ادمین ندارید."
DONE = "✅ انجام شد."

# ——— آمار و کاربران
ASK_UID_LOOKUP  = "🔎 آیدی عددی یا یوزرنیم کاربر را بفرستید (مثل @user یا 123456789)."
STATE_USER_LOOKUP = "ADMIN:USER_LOOKUP"

# ——— افزایش کردیت
ASK_UID_ADD   = "➕ آیدی عددی یا یوزرنیم کاربر برای «افزایش کردیت» را بفرستید."
STATE_ADD_UID = "ADMIN:ADD:UID"
ASK_AMT_ADD   = "➕ مقدار کردیتی که باید اضافه شود را بفرستید (فقط عدد)."
STATE_ADD_AMT = "ADMIN:ADD:AMT"

# ——— کسر کردیت
ASK_UID_SUB   = "➖ آیدی عددی یا یوزرنیم کاربر برای «کسر کردیت» را بفرستید."
STATE_SUB_UID = "ADMIN:SUB:UID"
ASK_AMT_SUB   = "➖ مقدار کردیتی که باید کم شود را بفرستید (فقط عدد)."
STATE_SUB_AMT = "ADMIN:SUB:AMT"

# ——— ریست/آن‌سابسکرایب کاربر
ASK_UID_RESET   = "♻️ آیدی عددی یا یوزرنیم کاربری که باید ریست شود را بفرستید."
STATE_RESET_UID = "ADMIN:RESET:UID"

# ——— پیام تکی
ASK_UID_MSG   = "✉️ آیدی عددی یا یوزرنیم کاربری که باید پیام تکی بگیرد را بفرستید."
STATE_MSG_UID = "ADMIN:DM:UID"
ASK_TXT_MSG   = "✍️ متن پیام تکی را بفرستید."
STATE_MSG_TXT = "ADMIN:DM:TXT"

# ——— پیام همگانی
ASK_LANG_CAST = "🌐 زبان پیام همگانی را انتخاب کنید."
ASK_TXT_CAST  = "📣 متن پیام همگانی را بفرستید."
STATE_CAST_LANG = "ADMIN:CAST:LANG"
STATE_CAST_TXT = "ADMIN:CAST:TXT"

# ——— به‌روزرسانی همگانی کردیت با فرمول
ASK_FORMULA     = (
    "🧮 فرمول محاسبه کردیت جدید را بفرستید.\n"
    "می‌توانید از متغیر <code>old</code> (کردیت فعلی) استفاده کنید، مثلا: <code>old * 0.045</code>."
)
STATE_FORMULA   = "ADMIN:CREDITS:FORMULA"

# ——— تنظیمات: بونوس رفرال
ASK_BONUS      = "🎁 مقدار بونوس رفرال را بفرستید (عدد)."
STATE_SET_BONUS = "ADMIN:SET:BONUS"

# ——— تنظیمات: کردیت شروع
ASK_FREE        = "🎉 مقدار «کردیت شروع برای ورود اول» را بفرستید (عدد)."
STATE_SET_FREE  = "ADMIN:SET:FREE"

# ——— تنظیمات: کانال تلگرام
ASK_TG         = "📢 لینک/یوزرنیم کانال تلگرام (برای عضویت اجباری) را بفرستید."
STATE_SET_TG   = "ADMIN:SET:TG"

# ——— تنظیمات: اینستاگرام
ASK_IG         = "📷 لینک پیج اینستاگرام (برای عضویت اجباری) را بفرستید."
STATE_SET_IG   = "ADMIN:SET:IG"

# ——— تنظیمات: کانال تلگرام بر اساس زبان
ASK_TG_LANG       = "📢 یوزرنیم/لینک کانال تلگرام را برای این زبان بفرستید."
STATE_SET_TG_LANG = "ADMIN:SET:TG_LANG"

# ——— تنظیمات: دموهای صدا
ASK_DEMO_VOICE = "🎧 یک صدا را برای ثبت دمو انتخاب کنید."
ASK_DEMO_AUDIO = "🎧 فایل صوتی دمو را ارسال کنید (audio/voice/document)."
STATE_DEMO_AUDIO = "ADMIN:DEMO:AUDIO"
