# modules/lang/texts.py
from modules.i18n import t

def TITLE(lang: str) -> str:
    return f"🌐 <b>{t('lang_title', lang)}</b>\n\n"