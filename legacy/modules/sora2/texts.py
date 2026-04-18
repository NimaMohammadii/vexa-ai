"""Text helpers for the Sora 2 menu."""

from modules.i18n import t


def intro(lang: str, *, cost: str) -> str:
    return t("sora2_intro", lang).format(cost=cost)


def purchase_success(lang: str, *, cost: str, position: int) -> str:
    return t("sora2_purchase_success", lang).format(cost=cost, position=position)


def no_credit(lang: str, *, cost: str, credits: str) -> str:
    return t("sora2_no_credit", lang).format(cost=cost, credits=credits)


def no_credit_alert(lang: str) -> str:
    return t("sora2_no_credit_alert", lang)


def admin_notification(*, user_id: int, username: str, first_name: str, credits: str, position: int) -> str:
    username_display = f"@{username}" if username else "-"
    return t("sora2_admin_notification", "fa").format(
        user_id=user_id,
        username=username_display,
        first_name=first_name or "-",
        credits=credits,
        position=position,
    )
