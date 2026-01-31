import db


_DEF_KIND = "audio"


def _setting_key(lang: str) -> str:
    lang = (lang or "").strip() or "fa"
    return f"WELCOME_AUDIO_{lang}"


def get_welcome_audio(lang: str) -> dict[str, str] | None:
    raw = db.get_setting(_setting_key(lang))
    if not raw:
        return None
    raw = str(raw).strip()
    if not raw:
        return None
    kind, sep, file_id = raw.partition(":")
    if not sep:
        return None
    kind = kind.strip() or _DEF_KIND
    file_id = file_id.strip()
    if not file_id:
        return None
    return {"kind": kind, "file_id": file_id}


def set_welcome_audio(lang: str, file_id: str, *, kind: str = _DEF_KIND) -> None:
    db.set_setting(_setting_key(lang), f"{kind}:{file_id}")


def clear_welcome_audio(lang: str) -> None:
    db.set_setting(_setting_key(lang), "")
