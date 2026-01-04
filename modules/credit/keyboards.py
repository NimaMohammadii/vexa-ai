from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional

from modules.i18n import t
from .settings import PAYMENT_PLANS, STAR_PACKAGES


# =========================
# Utilities
# =========================

def augment_with_rial(
    base_kb: Optional[InlineKeyboardMarkup],
    lang: str
) -> InlineKeyboardMarkup:
    kb = base_kb or InlineKeyboardMarkup()

    if lang.startswith("fa"):
        kb.row(
            InlineKeyboardButton(
                text="💳 پرداخت ریالی",
                callback_data="credit:payrial"
            )
        )

    return kb


# =========================
# Rial payment plans
# =========================

def payrial_plans_kb(lang="fa"):
    kb = InlineKeyboardMarkup()

    row = []
    for plan in PAYMENT_PLANS:
        btn = InlineKeyboardButton(
            text=plan["title"],
            callback_data=f"credit:payrial:{plan['id']}"
        )
        row.append(btn)

        if len(row) == 2:
            kb.row(*row)
            row = []

    if row:
        kb.row(*row)

    kb.row(
        InlineKeyboardButton(
            text=t("back", lang),
            callback_data="credit:menu"
        )
    )

    return kb


# =========================
# ⭐ Stars payment (FIXED)
# =========================

def star_payment_kb(lang="fa"):
    kb = InlineKeyboardMarkup()

    # هر پکیج = دقیقاً یک ردیف
    for pack in STAR_PACKAGES:
        kb.row(
            InlineKeyboardButton(
                text=f"⭐ {pack['stars']} استار – {pack['credits']} کردیت",
                callback_data=f"credit:stars:{pack['stars']}"
            )
        )

    kb.row(
        InlineKeyboardButton(
            text=t("back", lang),
            callback_data="credit:menu"
        )
    )

    return kb


# =========================
# Instant cancel
# =========================

def instant_cancel_kb(lang="fa"):
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(
            text=t("cancel", lang),
            callback_data="credit:cancel"
        )
    )
    return kb
