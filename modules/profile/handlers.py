# modules/profile/handlers.py
import math
import time

import db
from modules.i18n import t
from utils import edit_or_send, feature_disabled_text, is_feature_enabled, send_main_menu
from .texts import PROFILE_TEXT
from modules.home.keyboards import main_menu

_PLAN_LABEL_KEYS = {
    "creator": "plan_creator",
    "pro": "plan_pro",
    "studio": "plan_studio",
}

def _resolve_plan_name(plan_name: str | None, lang: str) -> str:
    if not plan_name:
        return t("plan_free", lang)
    label_key = _PLAN_LABEL_KEYS.get(plan_name)
    return t(label_key, lang) if label_key else plan_name

def build_balance_alert(lang: str, user_id: int, credits: float) -> tuple[str, str]:
    subscription = db.get_user_voice_subscription(user_id)
    plan_name = _resolve_plan_name(subscription["plan_name"], lang) if subscription else t("plan_free", lang)
    expires_at = subscription["expires_at"] if subscription else 0
    remaining_seconds = max(0, expires_at - int(time.time()))
    days_left = math.ceil(remaining_seconds / 86400) if remaining_seconds else 0
    title = t("balance_alert_title", lang)
    body = t("balance_alert_body", lang).format(
        credits=credits,
        plan_name=plan_name,
        days_left=days_left,
    )
    return title, body

def register(bot):
    pass

def open_profile(bot, cq):
    user = db.get_or_create_user(cq.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")
    if not is_feature_enabled("FEATURE_PROFILE"):
        edit_or_send(
            bot,
            cq.message.chat.id,
            cq.message.message_id,
            feature_disabled_text("FEATURE_PROFILE", lang),
            main_menu(lang),
        )
        return
    txt = PROFILE_TEXT(lang, user["user_id"], user["credits"])
    edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, main_menu(lang))


def open_profile_from_message(bot, msg, menu_message_id: int | None = None):
    user = db.get_or_create_user(msg.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")
    if not is_feature_enabled("FEATURE_PROFILE"):
        if menu_message_id:
            send_main_menu(
                bot,
                user["user_id"],
                msg.chat.id,
                feature_disabled_text("FEATURE_PROFILE", lang),
                main_menu(lang),
                message_id=menu_message_id,
            )
        else:
            send_main_menu(
                bot,
                user["user_id"],
                msg.chat.id,
                feature_disabled_text("FEATURE_PROFILE", lang),
                main_menu(lang),
            )
        return
    txt = PROFILE_TEXT(lang, user["user_id"], user["credits"])
    if menu_message_id:
        send_main_menu(
            bot,
            user["user_id"],
            msg.chat.id,
            txt,
            main_menu(lang),
            message_id=menu_message_id,
        )
    else:
        send_main_menu(bot, user["user_id"], msg.chat.id, txt, main_menu(lang))
