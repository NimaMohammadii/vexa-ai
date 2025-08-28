from modules.i18n import t

def TITLE(lang: str) -> str:
    return f"🎧 <b>{t('tts_title', lang)}</b>"

def ask_text(lang: str, voice_name: str) -> str:
    return f"{TITLE(lang)}\n\n{t('tts_prompt', lang)}\n\n🎙 <b>{voice_name}</b>"

def PROCESSING(lang: str) -> str:
    return t('tts_processing', lang)

def NO_CREDIT(lang: str) -> str:
    return t('tts_no_credit', lang)

def ERROR(lang: str) -> str:
    return t('tts_error', lang)