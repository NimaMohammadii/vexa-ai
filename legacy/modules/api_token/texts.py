from modules.i18n import t


def render_token_message(lang: str, token: str) -> str:
    body = t("api_token_body", lang).format(token=token)
    return body
