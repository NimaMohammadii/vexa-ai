from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from .texts import PAY_STARS_BTN, PAY_RIAL_BTN, PAY_RIAL_INSTANT, BACK_BTN, CANCEL_BTN
from .settings import PAYMENT_PLANS, STAR_PACKAGES

def augment_with_rial(base_kb: InlineKeyboardMarkup | None) -> InlineKeyboardMarkup:
    """
    این تابع دکمه «پرداخت ریالی» را به منوی Credit فعلی‌ات اضافه می‌کند.
    اگر منو از قبل وجود دارد، همان را می‌گیرد و یک دکمه به آن اضافه می‌کند.
    اگر None بدهی، یک منوی جدید می‌سازد.
    """
    kb = base_kb or InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton(PAY_RIAL_BTN, callback_data="credit:payrial"))
    return kb

def payrial_plans_kb() -> InlineKeyboardMarkup:
    """منوی نمایش قیمت‌ها و دکمه پرداخت فوری"""
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(PAY_RIAL_INSTANT, callback_data="credit:payrial:instant"))
    kb.add(InlineKeyboardButton(BACK_BTN, callback_data="credit:menu"))
    return kb

def credit_menu_kb() -> InlineKeyboardMarkup:
    """منوی اصلی خرید کردیت"""
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(PAY_STARS_BTN, callback_data="credit:stars"))
    kb.add(InlineKeyboardButton(PAY_RIAL_BTN, callback_data="credit:payrial"))
    kb.add(InlineKeyboardButton(BACK_BTN, callback_data="home:back"))
    return kb

def stars_packages_kb() -> InlineKeyboardMarkup:
    """منوی بسته های Telegram Stars"""
    kb = InlineKeyboardMarkup(row_width=2)
    row = []
    for i, pkg in enumerate(STAR_PACKAGES, start=1):
        row.append(
            InlineKeyboardButton(
                pkg["title"],
                callback_data=f"credit:buy:{pkg['stars']}:{pkg['credits']}"
            )
        )
        if i % 2 == 0:   # هر ۲تا دکمه یک ردیف
            kb.row(*row)
            row = []
    if row:  # اگه آخر لیست یکی موند
        kb.row(*row)

    kb.add(InlineKeyboardButton(BACK_BTN, callback_data="credit:menu"))
    return kb
