from modules.i18n import t

def PROFILE_TEXT(lang: str, uid: int, credits: int) -> str:
    return f"🙋🏼‍♂️ <b>{t('profile_title', lang)}</b>\n\n" + \
           t('profile_body', lang).format(uid=uid, credits=credits)