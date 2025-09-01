# modules/credit/texts.py
from modules.i18n import t

def INTRO(lang: str) -> str:
    # متن اصلی بدون "یا پرداخت ریالی"
    txt = f"🛒 <b>{t('Credit', lang)}</b>\n\n{t('credit_intro', lang)}"
    # فقط برای فارسی خط ریالی اضافه شود
    if lang == "fa":
        txt += "\n\n<b>برای پرداخت به صورت ریـالی به ادمین ربات پیام بدید ( لیـنک در بیـو ) ⚠️</b>"
    return txt

def INVOICE_TITLE(lang: str) -> str:
    return t("credit_invoice_title", lang)

def INVOICE_DESC(lang: str) -> str:
    return t("credit_invoice_desc", lang)

def PAY_SUCCESS(lang: str, stars: int, credits: int, balance: int) -> str:
    return t("credit_pay_success", lang).format(stars=stars, credits=credits, balance=balance)
