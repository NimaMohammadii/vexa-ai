"""Text helpers for the video generation module."""

import db
from modules.i18n import t
from .settings import CREDIT_COST


def intro(lang: str) -> str:
    return t("video_intro", lang).format(cost=db.format_credit_amount(CREDIT_COST))


def processing(lang: str) -> str:
    return t("video_processing", lang)


def error(lang: str) -> str:
    return t("video_error", lang)


def no_credit(lang: str, credits: float) -> str:
    return t("video_no_credit", lang).format(
        cost=db.format_credit_amount(CREDIT_COST),
        credits=db.format_credit_amount(credits),
    )


def not_configured(lang: str) -> str:
    return t("video_not_configured", lang)


def result_caption(lang: str) -> str:
    return t("video_result_caption", lang).format(cost=db.format_credit_amount(CREDIT_COST))
