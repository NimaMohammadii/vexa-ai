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
    Add the Rial payment button only for users with Persian (fa) language.
    The default lang is 'fa' for backward compatibility.
    """
    kb = base_kb or InlineKeyboardMarkup(row_width=2)
    if (lang or "fa").lower().startswith("fa"):
        kb.add(InlineKeyboardButton(PAY_RIAL_BTN, callback_data="credit:payrial"))
    return kb

def payrial_plans_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(PAY_RIAL_INSTANT, callback_data="credit:payrial:instant"))
    kb.add(InlineKeyboardButton(BACK_BTN, callback_data="credit:menu"))
    return kb

def credit_menu_kb(lang: str = "fa") -> InlineKeyboardMarkup:
    """
    Main credit menu. Adds Rial payment option only when lang starts with 'fa'.
    """
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(PAY_STARS_BTN, callback_data="credit:stars"))
    if (lang or "fa").lower().startswith("fa"):
        kb.add(InlineKeyboardButton(PAY_RIAL_BTN, callback_data="credit:payrial"))
    kb.add(InlineKeyboardButton(BACK_BTN, callback_data="home:back"))
    return kb

def stars_packages_kb() -> InlineKeyboardMarkup:
    """Return keyboard for Telegram Stars packages. callback_data includes both stars and credits."""
    kb = InlineKeyboardMarkup(row_width=1)
    for p in STAR_PACKAGES:
        title = p.get("title") or f"{p.get('stars')}⭐ → {p.get('credits')} کردیت"
        kb.add(InlineKeyboardButton(title, callback_data=f"credit:buy:{p.get('stars')}:{p.get('credits')}"))
    kb.add(InlineKeyboardButton(BACK_BTN, callback_data="credit:menu"))
    return kb

def instant_cancel_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton(CANCEL_BTN, callback_data="credit:cancel"))
    return kb
