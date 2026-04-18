# modules/clone/texts.py
import db
from modules.i18n import t


def MENU(lang: str = "fa") -> str:
    return t("clone_menu", lang)


def PAYMENT_CONFIRM(lang: str = "fa", cost: int = 200) -> str:
    return t("clone_payment_confirm", lang).format(cost=db.format_credit_amount(cost))


def NO_CREDIT_CLONE(lang: str = "fa", balance: float = 0, cost: int = 200) -> str:
    return t("clone_insufficient_credit", lang).format(
        balance=db.format_credit_amount(balance),
        cost=db.format_credit_amount(cost),
    )


def ASK_NAME(lang: str = "fa") -> str:
    return t("clone_ask_name", lang)


def SUCCESS(lang: str = "fa") -> str:
    return t("clone_success", lang)


def PAYMENT_SUCCESS(lang: str = "fa") -> str:
    return t("clone_payment_success", lang)


def ERROR(lang: str = "fa") -> str:
    return t("clone_error", lang)
