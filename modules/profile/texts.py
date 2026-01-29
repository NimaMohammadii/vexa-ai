import db
from modules.i18n import t


def PROFILE_TEXT(lang: str, uid: int, credits: float) -> str:
    return (
        f"🙋🏼‍♂️ <b>{t('profile_title', lang)}</b>\n\n"
        + t("profile_body", lang).format(
            uid=uid,
            credits=db.format_credit_amount(credits),
        )
    )


def PROFILE_ALERT_TEXT(lang: str, credits: float) -> str:
    title = t("profile_balance_alert_title", lang)
    body = t("profile_balance_alert_body", lang).format(
        credits=db.format_credit_amount(credits),
    )
    return f"{title}\n\n{body}"
