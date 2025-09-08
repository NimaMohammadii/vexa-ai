from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from ..i18n import t
from .settings import PAYMENT_PLANS, STAR_PACKAGES

def augment_with_rial(base_kb: InlineKeyboardMarkup | None = None, lang: str | None = None) -> InlineKeyboardMarkup:
    lang = (lang or "fa")[:2]
    kb = base_kb or InlineKeyboardMarkup(row_width=2)
    if lang == "fa":
        kb.add(InlineKeyboardButton(text=t("pay_rial_btn", lang), callback_data="credit:payrial"))
    return kb

def payrial_plans_kb(lang: str | None = None) -> InlineKeyboardMarkup:
    lang = (lang or "fa")[:2]
    kb = InlineKeyboardMarkup(row_width=1)
    for plan in PAYMENT_PLANS:
        kb.add(InlineKeyboardButton(text=plan.get("title", t("pay_rial_title", lang)), callback_data=f"credit:payrial:plan:{plan['amount_toman']}:{plan['credits']}"))
    kb.add(InlineKeyboardButton(text=t("pay_rial_instant", lang), callback_data="credit:payrial:instant"))
    kb.add(InlineKeyboardButton(text=t("back", lang), callback_data="credit:menu"))
    return kb

def credit_menu_kb(lang: str | None = None) -> InlineKeyboardMarkup:
    lang = (lang or "fa")[:2]
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(text=t("pay_stars_btn", lang), callback_data="credit:stars"))
    if lang == "fa":
        kb.add(InlineKeyboardButton(text=t("pay_rial_btn", lang), callback_data="credit:payrial"))
    kb.add(InlineKeyboardButton(text=t("back", lang), callback_data="home"))
    return kb

def stars_packages_kb(lang: str | None = None) -> InlineKeyboardMarkup:
    lang = (lang or "fa")[:2]
    kb = InlineKeyboardMarkup(row_width=2)
    for pkg in STAR_PACKAGES:
        kb.add(InlineKeyboardButton(text=pkg.get("title", f"{pkg.get('stars',0)} ⭐"), callback_data=f"credit:buy:{pkg['stars']}:{pkg['credits']}"))
    kb.add(InlineKeyboardButton(text=t("back", lang), callback_data="credit:menu"))
    return kb

def instant_cancel_kb(lang: str | None = None) -> InlineKeyboardMarkup:
    lang = (lang or "fa")[:2]
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(text=t("cancel", lang), callback_data="credit:cancel"))
    kb.add(InlineKeyboardButton(text=t("back", lang), callback_data="credit:menu"))
    return kb
