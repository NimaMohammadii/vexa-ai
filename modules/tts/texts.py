import db
from modules.i18n import t
from .settings import CREDIT_PER_CHAR as PRO_CREDIT_PER_CHAR

def TITLE(lang: str) -> str:
    return f"🎧 <b>{t('tts_title', lang)}</b>"

def ask_text(
    lang: str,
    voice_name: str,
    *,
    credit_per_char: float | int | str | None = None,
    show_demo_link: bool = True,
) -> str:
    credit_value = credit_per_char if credit_per_char is not None else PRO_CREDIT_PER_CHAR
    credit_text = db.format_credit_amount(credit_value)
    prompt = t("tts_prompt", lang).format(credit=credit_text)

    if not show_demo_link and lang == "fa":
        prompt = prompt.replace("\n<b><a href='https://t.me/VexaOrder/6'>دموی صداها</a></b>", "")

    prompt = prompt.strip()
    return f"{TITLE(lang)}\n\n{prompt}\n\n🎙 <b>{voice_name}</b>"

def PROCESSING(lang: str) -> str:
    return t('tts_processing', lang)

def NO_CREDIT(lang: str, credits: float | None = None, required_credits: float | None = None) -> str:
    """
    پیام کردیت کافی نیست با فرمت مشخص
    """
    current_credits = db.format_credit_amount(credits if credits is not None else 0)
    required = db.format_credit_amount(required_credits if required_credits is not None else 0)

    return t("tts_no_credit", lang).format(credits=current_credits, required=required)

def ERROR(lang: str) -> str:
    return t('tts_error', lang)

def BANNED(lang: str) -> str:
    return t('tts_banned_words', lang)
