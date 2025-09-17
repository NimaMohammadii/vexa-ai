# modules/clone/texts.py

def MENU(lang="fa"):
    return "🎙 <b>ساخت صدای شخصی</b>\n\nیک ویس کوتاه (۱۵-۳۰ ثانیه) ارسال کنید."

def PAYMENT_CONFIRM(lang="fa", cost=6800):
    return f"💰 <b>پرداخت کردیت</b>\n\nبرای ساخت صدای شخصی باید <b>{cost:,} کردیت</b> پرداخت کنید.\n\nآیا تایید می‌کنید؟"

def NO_CREDIT_CLONE(lang="fa", balance=0, cost=6800):
    return f"❌ <b>کردیت ناکافی</b>\n\nموجودی شما: <b>{balance:,} کردیت</b>\nمورد نیاز: <b>{cost:,} کردیت</b>\n\nلطفاً ابتدا کردیت خریداری کنید."

ASK_NAME = "➕ </b>حالا یک اسم برای صدای جدیدت بفرست<b>"
SUCCESS = "✅ صدای شخصی با موفقیت ساخته شد و به لیست صداهای شما اضافه شد."
PAYMENT_SUCCESS = "✅ با موفقیت کردیت پرداخت شد!"
ERROR = "❌ خطا در ساخت صدا. دوباره تلاش کنید."