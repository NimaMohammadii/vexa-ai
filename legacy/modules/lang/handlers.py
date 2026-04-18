# modules/lang/handlers.py
from typing import Optional

import db
from utils import edit_or_send, check_force_sub, feature_disabled_text, is_feature_enabled, send_main_menu
from .texts import TITLE
from .keyboards import lang_menu
from modules.home.texts import MAIN
from modules.home.keyboards import main_menu
from modules.i18n import t


def _language_menu_content(
    user,
    display_lang: Optional[str] = None,
):
    stored_lang = (user or {}).get("lang") or ""
    render_lang = display_lang or stored_lang or "fa"
    return (
        TITLE(render_lang),
        lang_menu(stored_lang, render_lang, show_back=False),
        stored_lang or render_lang,
    )


def send_language_menu(
    bot,
    user,
    chat_id,
    message_id=None,
    force_new: bool = False,
    display_lang: Optional[str] = None,
):
    text, markup, _ = _language_menu_content(user, display_lang)
    if force_new or message_id is None:
        send_main_menu(bot, user["user_id"], chat_id, text, markup)
    else:
        send_main_menu(bot, user["user_id"], chat_id, text, markup, message_id=message_id)


def register(bot):
    @bot.message_handler(commands=["language"])
    def language_cmd(msg):
        user = db.get_or_create_user(msg.from_user)
        stored_lang = (user.get("lang") or "").strip()
        if stored_lang and not is_feature_enabled("FEATURE_LANG"):
            bot.reply_to(msg, feature_disabled_text("FEATURE_LANG", stored_lang))
            return
        send_language_menu(bot, user, msg.chat.id, force_new=True)

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("lang:"))
    def lang_router(cq):
        user = db.get_or_create_user(cq.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        parts = cq.data.split(":")
        action = parts[1]

        if action == "back":
            send_main_menu(
                bot,
                user["user_id"],
                cq.message.chat.id,
                MAIN(lang),
                main_menu(lang),
                message_id=cq.message.message_id,
            )
            return

        if action == "set":
            code = parts[2]
            db.set_user_lang(user["user_id"], code)
            lang = code
            user["lang"] = code
            bot.answer_callback_query(cq.id, t("lang_saved", lang))

            settings = db.get_settings()
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings, lang)
            if not ok:
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, kb)
                return

            try:
                from modules.home.handlers import _consume_pending_referral
            except ImportError:
                _consume_pending_referral = None

            try:
                from modules.home.handlers import _maybe_send_welcome_audio
            except ImportError:
                _maybe_send_welcome_audio = None

            if _maybe_send_welcome_audio:
                _maybe_send_welcome_audio(bot, user, cq.message.chat.id, lang)

            if _consume_pending_referral:
                _consume_pending_referral(bot, user, cq.message.chat.id, lang)

            send_main_menu(
                bot,
                user["user_id"],
                cq.message.chat.id,
                MAIN(lang),
                main_menu(lang),
                message_id=cq.message.message_id,
            )
            try:
                from modules.home.handlers import _trigger_onboarding
            except ImportError:
                _trigger_onboarding = None
            if _trigger_onboarding:
                _trigger_onboarding(bot, user, cq.message.chat.id)
            return


def open_language(bot, cq):
    user = db.get_or_create_user(cq.from_user)
    stored_lang = (user.get("lang") or "").strip()
    if stored_lang and not is_feature_enabled("FEATURE_LANG"):
        bot.answer_callback_query(
            cq.id,
            feature_disabled_text("FEATURE_LANG", stored_lang),
            show_alert=True,
        )
        return
    send_language_menu(bot, user, cq.message.chat.id, cq.message.message_id)


def open_language_from_message(bot, msg, menu_message_id: int | None = None):
    user = db.get_or_create_user(msg.from_user)
    stored_lang = (user.get("lang") or "").strip()
    if stored_lang and not is_feature_enabled("FEATURE_LANG"):
        bot.reply_to(msg, feature_disabled_text("FEATURE_LANG", stored_lang))
        return
    if menu_message_id:
        send_language_menu(bot, user, msg.chat.id, message_id=menu_message_id)
    else:
        send_language_menu(bot, user, msg.chat.id, force_new=True)
