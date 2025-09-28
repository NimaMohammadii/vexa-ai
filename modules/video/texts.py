"""Text helpers for the video generation module."""

from modules.i18n import t
from .settings import CREDIT_COST


def intro(lang: str) -> str:
    return t("video_intro", lang).format(cost=CREDIT_COST)


def processing(lang: str) -> str:
    return t("video_processing", lang)


def error(lang: str) -> str:
    return t("video_error", lang)


def no_credit(lang: str, credits: int) -> str:
    return t("video_no_credit", lang).format(cost=CREDIT_COST, credits=credits)


def not_configured(lang: str) -> str:
    return t("video_not_configured", lang)


def result_caption(lang: str) -> str:
    return t("video_result_caption", lang).format(cost=CREDIT_COST)
