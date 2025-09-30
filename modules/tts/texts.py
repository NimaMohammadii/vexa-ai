import db
from modules.i18n import t

def TITLE(lang: str) -> str:
    return f"🎧 <b>{t('tts_title', lang)}</b>"

def ask_text(lang: str, voice_name: str) -> str:
    return f"{TITLE(lang)}\n\n{t('tts_prompt', lang)}\n\n🎙 <b>{voice_name}</b>"

def PROCESSING(lang: str) -> str:
    return t('tts_processing', lang)

def NO_CREDIT(lang: str, credits: float | None = None, required_credits: float | None = None) -> str:
    """
    پیام کردیت کافی نیست با فرمت مشخص
    """
    current_credits = db.format_credit_amount(credits if credits is not None else 0)
    required = db.format_credit_amount(required_credits if required_credits is not None else 0)

    return f"""⚠️ <b>کردیت کافی نیست</b>
موجـودی شما : <b>{current_credits} Credit</b>
➕ کردیـت لازم : <b>{required}</b>
میتونـی کردیت بخری یا متن رو کوتاه‌تر کنی<b> /help</b>"""

def ERROR(lang: str) -> str:
    return t('tts_error', lang)

def BANNED(lang: str) -> str:
    return t('tts_banned_words', lang)
