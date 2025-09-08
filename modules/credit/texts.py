# modules/credit/texts.py
from modules.i18n import t

def CREDIT_TITLE(lang: str) -> str:
    return t("credit_title", lang)

def CREDIT_HEADER(lang: str) -> str:
    return t("credit_header", lang)

def PAY_STARS_BTN(lang: str) -> str:
    return t("credit_pay_stars_btn", lang)

def PAY_RIAL_BTN(lang: str) -> str:
    return t("credit_pay_rial_btn", lang)

def PAY_RIAL_TITLE(lang: str) -> str:
    return t("credit_pay_rial_title", lang)

def PAY_RIAL_PLANS_HEADER(lang: str) -> str:
    return t("credit_pay_rial_plans_header", lang)

def PAY_RIAL_INSTANT(lang: str) -> str:
    return t("credit_pay_rial_instant", lang)

def BACK_BTN(lang: str) -> str:
    return t("back", lang)

def CANCEL_BTN(lang: str) -> str:
    return t("cancel", lang)

def INSTANT_PAY_INSTRUCT(lang: str, card: str) -> str:
    return t("credit_instant_pay_instruct", lang).format(card=card)

def WAITING_CONFIRM(lang: str) -> str:
    return t("credit_waiting_confirm", lang)
