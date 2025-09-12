# modules/home/texts.py
from modules.i18n import t

def MAIN(lang: str) -> str:
    return f"🏠 <b>{t('home_title', lang)}</b>\n\n{t('home_body', lang)}"

def help_text(lang: str) -> str:
    return f"{t('help_title', lang)}\n\n{t('help_body', lang)}"
