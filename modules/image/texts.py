"""Text helpers for the image generation module."""

from modules.i18n import t
from .settings import CREDIT_COST, DEFAULT_SIZE_KEY, IMAGE_SIZE_OPTIONS


def intro(lang: str) -> str:
    return t("image_intro", lang).format(cost=CREDIT_COST)


def processing(lang: str) -> str:
    return t("image_processing", lang)


def error(lang: str) -> str:
    return t("image_error", lang)


def no_credit(lang: str, credits: int) -> str:
    return t("image_no_credit", lang).format(cost=CREDIT_COST, credits=credits)


def not_configured(lang: str) -> str:
    return t("image_not_configured", lang)


def result_caption(lang: str) -> str:
    return t("image_result_caption", lang).format(cost=CREDIT_COST)


def need_prompt(lang: str) -> str:
    return t("image_need_prompt", lang)


def invalid_reference(lang: str) -> str:
    return t("image_invalid_reference", lang)


def reference_download_error(lang: str) -> str:
    return t("image_reference_download_error", lang)


def size_hint(lang: str) -> str:
    return t("image_size_hint", lang)


def size_invalid(lang: str) -> str:
    return t("image_size_invalid", lang)


def size_label(lang: str, size_key: str) -> str:
    option = IMAGE_SIZE_OPTIONS.get(size_key) or IMAGE_SIZE_OPTIONS[DEFAULT_SIZE_KEY]
    return t(option["label_key"], lang).format(
        ratio=option["ratio_display"],
        resolution=option["resolution_display"],
    )


def size_selected(lang: str, label: str) -> str:
    return t("image_size_selected", lang).format(size=label)
