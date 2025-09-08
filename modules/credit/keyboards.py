from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from .texts import (
    PAY_STARS_BTN,
    PAY_RIAL_BTN,
    PAY_RIAL_INSTANT,
    BACK_BTN,
    CANCEL_BTN,
)
from .settings import PAYMENT_PLANS, STAR_PACKAGES

def augment_with_rial(base_kb: InlineKeyboardMarkup | None, lang: str = "fa") -> InlineKeyboardMarkup:
    """
    این تابع دکمه «پرداخت ریالی» را به منوی Credit فعلی اضافه می‌کند.
    اما اگر زبان کاربر فارسی نباشد، دکمه اضافه نخواهد شد.
    (پیش‌فرض lang='fa' برای سازگاری رو به عقب)
    """
    kb = base_kb or InlineKeyboardMarkup(row_width=2)
    if (lang or "fa").lower().startswith("fa"):
        kb.add(InlineKeyboardButton(PAY_RIAL_BTN, callback_data="credit:payrial"))
    return kb

def payrial_plans_kb() -> InlineKeyboardMarkup:
    """منوی نمایش قیمت‌ها و دکمه پرداخت فوری (این منو عملاً فقط برای کاربران فارسی کاربرد دارد)"""
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(PAY_RIAL_INSTANT, callback_data="credit:payrial:instant"))
    kb.add(InlineKeyboardButton(BACK_BTN, callback_data="credit:menu"))
    return kb

def credit_menu_kb(lang: str = "fa") -> InlineKeyboardMarkup:
    """
    منوی اصلی خرید کردیت.
    اگر lang فارسی نباشد، دکمهٔ پرداخت به تومان نمایش داده نمیشود.
    (پارامتر lang پیش‌فرض 'fa' است تا سایر فراخوانی‌ها که بدون آرگومان فراخوانی می‌کنند، آسیب نبینند)
    """
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(PAY_STARS_BTN, callback_data="credit:stars"))
    # فقط برای فارسی، گزینهٔ ریالی را اضافه می‌کنیم
    if (lang or "fa").lower().startswith("fa"):
        kb.add(InlineKeyboardButton(PAY_RIAL_BTN, callback_data="credit:payrial"))
    kb.add(InlineKeyboardButton(BACK_BTN, callback_data="home:back"))
    return kb

def stars_packages_kb() -> InlineKeyboardMarkup:
    """منوی بسته‌های Telegram Stars"""
    kb = InlineKeyboardMarkup(row_width=1)
    for p in STAR_PACKAGES:
        title = p.get("title") or f"{p.get('stars')}⭐ → {p.get('credits')} کردیت"
        kb.add(InlineKeyboardButton(title, callback_data=f"credit:buy:{p.get('stars')}"))
    kb.add(InlineKeyboardButton(BACK_BTN, callback_data="credit:menu"))
    return kb

def instant_cancel_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton(CANCEL_BTN, callback_data="credit:cancel"))
    return kb
