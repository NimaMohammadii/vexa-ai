"""User-facing texts for the support module."""
from modules.i18n import t


def SUPPORT_INTRO(lang: str) -> str:
    return t("support_intro", lang)


def SUPPORT_PROMPT(lang: str) -> str:
    return t("support_prompt", lang)
