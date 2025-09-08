from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from .texts import PAY_STARS_BTN, PAY_RIAL_BTN, PAY_RIAL_INSTANT, BACK_BTN, CANCEL_BTN
from .settings import PAYMENT_PLANS, STAR_PACKAGES

def credit_menu_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    # Stars button is always visible
    kb.add(InlineKeyboardButton(PAY_STARS_BTN(lang), callback_data="credit:stars"))
    # Rial button only for Persian UI
    if lang == "fa":
        kb.add(InlineKeyboardButton(PAY_RIAL_BTN(lang), callback_data="credit:payrial"))
    kb.add(InlineKeyboardButton(BACK_BTN(lang), callback_data="credit:back"))
    return kb

def payrial_plans_kb(lang: str) -> InlineKeyboardMarkup:
    """منوی نمایش قیمت‌ها و دکمه پرداخت فوری"""
    kb = InlineKeyboardMarkup(row_width=1)
    for p in PAYMENT_PLANS:
        kb.add(InlineKeyboardButton(p["title"], callback_data=f"credit:plan:{p['id']}"))
    kb.add(InlineKeyboardButton(PAY_RIAL_INSTANT(lang), callback_data="credit:instant"))
    kb.add(InlineKeyboardButton(BACK_BTN(lang), callback_data="credit:menu"))
    return kb

def stars_packages_kb(lang: str) -> InlineKeyboardMarkup:
    """منوی بسته‌های Telegram Stars"""
    kb = InlineKeyboardMarkup(row_width=2)
    for pkg in STAR_PACKAGES:
        kb.add(InlineKeyboardButton(
            pkg["title"],
            callback_data=f"credit:buy:{pkg['stars']}:{pkg['credits']}"
        ))
    kb.add(InlineKeyboardButton(BACK_BTN(lang), callback_data="credit:menu"))
    return kb

def instant_cancel_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(CANCEL_BTN(lang), callback_data="credit:cancel"))
    return kb
