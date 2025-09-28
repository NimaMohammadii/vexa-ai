"""Text helpers for the image generation module."""

from modules.i18n import t
from .settings import CREDIT_COST


def intro(lang: str) -> str:
    return t("image_intro", lang).format(cost=CREDIT_COST)


def processing(lang: str) -> str:
    return t("image_processing", lang)


def processing_edit(lang: str) -> str:
    return t("image_processing_edit", lang)


def processing_blend(lang: str) -> str:
    return t("image_processing_blend", lang)


def error(lang: str) -> str:
    return t("image_error", lang)


def no_credit(lang: str, credits: int) -> str:
    return t("image_no_credit", lang).format(cost=CREDIT_COST, credits=credits)


def not_configured(lang: str) -> str:
    return t("image_not_configured", lang)


def result_caption(lang: str) -> str:
    return t("image_result_caption", lang).format(cost=CREDIT_COST)


def first_photo_received(lang: str) -> str:
    return t("image_first_photo_received", lang)


def need_edit_prompt(lang: str) -> str:
    return t("image_need_edit_prompt", lang)


def need_blend_prompt(lang: str) -> str:
    return t("image_need_blend_prompt", lang)
