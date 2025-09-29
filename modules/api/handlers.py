"""Telegram command handler exposing API usage info to end-users."""
from __future__ import annotations

import db
from config import API_CREDIT_COST, API_KEY_HEADER_NAME
from modules.i18n import t
from telebot.types import Message
from utils import check_force_sub, edit_or_send

_DOCS_PATH = "/api/docs"


def register(bot) -> None:
    @bot.message_handler(commands=["api"])
    def api_cmd(msg: Message) -> None:
        user = db.get_or_create_user(msg.from_user)
        stored_lang = (user.get("lang") or "").strip()
        lang = stored_lang or "fa"

        db.touch_last_seen(user["user_id"])

        if user.get("banned"):
            bot.reply_to(msg, t("error_banned", lang))
            return

        if not stored_lang:
            from modules.lang.handlers import send_language_menu

            send_language_menu(
                bot,
                user,
                msg.chat.id,
                msg.message_id,
                force_new=True,
                display_lang="en",
            )
            return

        settings = db.get_settings()
        mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
        if mode in ("new", "all"):
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings, lang)
            if not ok:
                edit_or_send(bot, msg.chat.id, msg.message_id, txt, kb)
                return

        try:
            api_key = db.ensure_user_api_key(user["user_id"])
        except RuntimeError:
            bot.reply_to(msg, t("api_config_missing", lang))
            return
        except Exception as exc:  # pragma: no cover - defensive guard
            print(f"[API-CMD] Failed to ensure API key for user {user['user_id']}: {exc}")
            bot.reply_to(msg, t("api_unexpected_error", lang))
            return

        text = t("api_key_message", lang).format(
            key=api_key,
            header=API_KEY_HEADER_NAME,
            cost=API_CREDIT_COST,
            docs=_DOCS_PATH,
        )

        bot.send_message(msg.chat.id, text, parse_mode="HTML", disable_web_page_preview=True)
