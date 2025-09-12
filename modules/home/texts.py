# modules/home/texts.py
from modules.i18n import t

def MAIN(lang: str) -> str:
    return f"🏠 <b>{t('home_title', lang)}</b>\n\n{t('home_body', lang)}"

def HELP(lang: str) -> str:
    return t('help_text', lang)
