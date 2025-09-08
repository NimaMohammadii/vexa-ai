from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.i18n import t
from .settings import PAYMENT_PLANS, STAR_PACKAGES

def augment_with_rial(base_kb: InlineKeyboardMarkup | None, lang: str) -> InlineKeyboardMarkup:
    """
    این تابع دکمه «پرداخت ریالی» را به منوی Credit فعلی‌ات اضافه می‌کند.
    اگر منو از قبل وجود دارد، همان را می‌گیرد و یک دکمه به آن اضافه می‌کند.
    اگر None بدهی، یک منوی جدید می‌سازد.
    فقط برای زبان فارسی نمایش داده می‌شود.
    """
    kb = base_kb or InlineKeyboardMarkup(row_width=2)
    if lang == "fa":  # فقط برای زبان فارسی
        kb.add(InlineKeyboardButton(t("pay_rial_btn", lang), callback_data="credit:payrial"))
    return kb

def payrial_plans_kb(lang: str) -> InlineKeyboardMarkup:
    """منوی نمایش قیمت‌ها و دکمه پرداخت فوری"""
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(t("pay_rial_instant", lang), callback_data="credit:payrial:instant"))
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="credit:menu"))
    return kb

def credit_menu_kb(lang: str) -> InlineKeyboardMarkup:
    """منوی اصلی خرید کردیت"""
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(t("pay_stars_btn", lang), callback_data="credit:stars"))
    # فقط برای زبان فارسی دکمه پرداخت تومان نمایش داده شود
    if lang == "fa":
        kb.add(InlineKeyboardButton(t("pay_rial_btn", lang), callback_data="credit:payrial"))
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb

def stars_packages_kb(lang: str) -> InlineKeyboardMarkup:
    """منوی بسته‌های Telegram Stars"""
    kb = InlineKeyboardMarkup(row_width=2)
    for pkg in STAR_PACKAGES:
        kb.add(InlineKeyboardButton(
            pkg["title"], 
            callback_data=f"credit:buy:{pkg['stars']}:{pkg['credits']}"
        ))
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="credit:menu"))
    return kb

def instant_cancel_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(t("cancel_btn", lang), callback_data="credit:cancel"))
    return kb
