"""Text helpers for the Gen-4 video module."""

from modules.i18n import t

from .settings import CREDIT_COST


def intro(lang: str) -> str:
    return t("video_gen4_intro", lang).format(cost=CREDIT_COST)


def processing(lang: str) -> str:
    return t("video_gen4_processing", lang)


def error(lang: str) -> str:
    return t("video_gen4_error", lang)


def no_credit(lang: str, credits: int) -> str:
    return t("video_gen4_no_credit", lang).format(cost=CREDIT_COST, credits=credits)


def not_configured(lang: str) -> str:
    return t("video_gen4_not_configured", lang)


def need_image(lang: str) -> str:
    return t("video_gen4_need_image", lang)


def download_error(lang: str) -> str:
    return t("video_gen4_download_error", lang)


def invalid_file(lang: str) -> str:
    return t("video_gen4_invalid_file", lang)


def result_caption(lang: str) -> str:
    return t("video_gen4_result_caption", lang).format(cost=CREDIT_COST)
