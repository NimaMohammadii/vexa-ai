from modules.i18n import t

def INVITE_TEXT(lang: str, ref_url: str, bonus: int, user_id: int, invited_count: int) -> str:
    return f"🎁 <b>{t('invite_title', lang)}</b>\n\n" + \
           t('invite_body', lang).format(ref=ref_url, bonus=bonus, user_id=user_id, invited=invited_count)
