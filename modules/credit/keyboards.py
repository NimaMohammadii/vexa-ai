from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.i18n import t
from .settings import PAYMENT_PLANS, STAR_PACKAGES


def augment_with_rial(base_kb, lang):
    kb = base_kb or InlineKeyboardMarkup()

    if lang == "fa":
        kb.row(
            InlineKeyboardButton(
                text="💳 پرداخت ریالی",
                callback_data="credit:payrial"
            )
        )
    return kb


def payrial_plans_kb(lang="fa"):
    kb = InlineKeyboardMarkup()
    row = []

    for plan in PAYMENT_PLANS:
        row.append(
            InlineKeyboardButton(
                text=plan["title"],
                callback_data=f"credit:payrial:{plan['id']}"
            )
        )
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


# ========= فقط همین بخش تغییر کرده =========
def star_payment_kb(lang="fa"):
    kb = InlineKeyboardMarkup()

    for pack in STAR_PACKAGES:
        kb.row(
            InlineKeyboardButton(
                text=pack["title"],
                callback_data=f"credit:stars:{pack['id']}"
            )
        )

    kb.row(
        InlineKeyboardButton(
            text=t("back", lang),
            callback_data="credit:menu"
        )
    )
    return kb
# =========================================


def instant_cancel_kb(lang="fa"):
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(
            text=t("cancel", lang),
            callback_data="credit:cancel"
        )
    )
    return kb
