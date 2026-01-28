# modules/home/handlers.py
from __future__ import annotations

import threading
import time

import db
from telebot.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from utils import (
    check_force_sub,
    edit_or_send,
    ensure_force_sub,
    feature_disabled_text,
    is_feature_enabled,
    send_main_menu,
)
from modules.i18n import t
from .texts import MAIN, HELP
from .keyboards import main_menu, menu_actions, _back_to_home_kb


ONBOARDING_DAILY_BONUS_DELAY = 15.0
ONBOARDING_DAILY_BONUS_UNLOCK_DELAY = 10 * 60
DAILY_REWARD_INTERVAL = 24 * 60 * 60
LOW_CREDIT_DELAY = 15.0
LOW_CREDIT_THRESHOLD = 15


def _daily_bonus_ready_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("onboarding_bonus_button", lang), callback_data="onboarding:daily_reward"))
    return kb


def _daily_bonus_unlocked_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("onboarding_bonus_button", lang), callback_data="onboarding:invite"))
    return kb


def _low_credit_keyboard(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(t("low_credit_button", lang), callback_data="credit:menu"))
    return kb


def _send_low_credit_warning(bot, user_id: int, chat_id: int) -> None:
    user = db.get_user(user_id)
    if not user or user.get("banned"):
        return
    credits = db.normalize_credit_amount(user.get("credits", 0))
    if credits >= LOW_CREDIT_THRESHOLD:
        if db.get_low_credit_prompted_at(user_id) > 0:
            db.set_low_credit_prompted_at(user_id, 0)
        return
    if db.get_low_credit_prompted_at(user_id) > 0:
        return
    lang = db.get_user_lang(user_id, "fa")
    try:
        bot.send_message(
            chat_id,
            t("low_credit_warning", lang),
            reply_markup=_low_credit_keyboard(lang),
        )
    except Exception:
        return
    db.set_low_credit_prompted_at(user_id, int(time.time()))


def _schedule_low_credit_warning(bot, user, chat_id: int, delay: float) -> None:
    user_id = user["user_id"]
    credits = db.normalize_credit_amount(user.get("credits", 0))
    if credits >= LOW_CREDIT_THRESHOLD:
        if db.get_low_credit_prompted_at(user_id) > 0:
            db.set_low_credit_prompted_at(user_id, 0)
        return
    if db.get_low_credit_prompted_at(user_id) > 0:
        return
    timer = threading.Timer(delay, _send_low_credit_warning, args=(bot, user_id, chat_id))
    timer.daemon = True
    timer.start()


def _handle_feature_disabled(bot, cq: CallbackQuery, lang: str, feature_key: str) -> None:
    bot.answer_callback_query(
        cq.id,
        feature_disabled_text(feature_key, lang),
        show_alert=True,
    )


def _send_daily_bonus_unlocked(bot, user_id: int, chat_id: int) -> None:
    user = db.get_user(user_id)
    if not user or user.get("banned"):
        return
    if db.get_daily_bonus_unlocked_at(user_id) > 0:
        return
    lang = db.get_user_lang(user_id, "fa")
    try:
        bot.send_message(
            chat_id,
            t("onboarding_daily_bonus_unlocked", lang),
            reply_markup=_daily_bonus_unlocked_keyboard(lang),
        )
    except Exception:
        return
    db.set_daily_bonus_unlocked_at(user_id, int(time.time()))
    _schedule_daily_bonus_reminder(bot, user_id, chat_id)


def _schedule_daily_bonus_unlocked(bot, user_id: int, chat_id: int, delay: float) -> None:
    timer = threading.Timer(delay, _send_daily_bonus_unlocked, args=(bot, user_id, chat_id))
    timer.daemon = True
    timer.start()


def _seconds_until_daily_reward(user_id: int, now: int | None = None) -> int:
    now = now or int(time.time())
    last_claim = db.get_last_daily_reward(user_id)
    if not last_claim:
        return 0
    return max(0, DAILY_REWARD_INTERVAL - (now - int(last_claim)))


def _send_daily_bonus_reminder(bot, user_id: int, chat_id: int) -> None:
    user = db.get_user(user_id)
    if not user or user.get("banned"):
        return
    if db.get_daily_bonus_reminded_at(user_id) > 0:
        return
    remaining = _seconds_until_daily_reward(user_id)
    if remaining > 0:
        return
    lang = db.get_user_lang(user_id, "fa")
    try:
        bot.send_message(
            chat_id,
            t("onboarding_daily_bonus_reminder", lang),
            reply_markup=_daily_bonus_ready_keyboard(lang),
        )
    except Exception:
        return
    db.set_daily_bonus_reminded_at(user_id, int(time.time()))


def _schedule_daily_bonus_reminder(
    bot,
    user_id: int,
    chat_id: int,
    delay: float | None = None,
) -> None:
    if delay is None:
        delay = _seconds_until_daily_reward(user_id)
        if delay <= 0:
            _send_daily_bonus_reminder(bot, user_id, chat_id)
            return
    timer = threading.Timer(delay, _send_daily_bonus_reminder, args=(bot, user_id, chat_id))
    timer.daemon = True
    timer.start()


def _send_daily_bonus_ready(bot, user_id: int, chat_id: int) -> None:
    user = db.get_user(user_id)
    if not user or user.get("banned"):
        return
    if db.get_daily_bonus_prompted_at(user_id) > 0:
        return
    lang = db.get_user_lang(user_id, "fa")
    try:
        bot.send_message(
            chat_id,
            t("onboarding_daily_bonus_ready", lang),
            reply_markup=_daily_bonus_ready_keyboard(lang),
        )
    except Exception:
        return
    prompted_at = int(time.time())
    db.set_daily_bonus_prompted_at(user_id, prompted_at)
    _schedule_daily_bonus_unlocked(
        bot,
        user_id,
        chat_id,
        ONBOARDING_DAILY_BONUS_UNLOCK_DELAY,
    )


def _maybe_send_pending_daily_bonus_unlock(bot, user_id: int, chat_id: int) -> None:
    prompted_at = db.get_daily_bonus_prompted_at(user_id)
    if not prompted_at:
        return
    if db.get_daily_bonus_unlocked_at(user_id) > 0:
        _maybe_send_pending_daily_bonus_reminder(bot, user_id, chat_id)
        return
    elapsed = int(time.time()) - int(prompted_at)
    if elapsed >= ONBOARDING_DAILY_BONUS_UNLOCK_DELAY:
        _send_daily_bonus_unlocked(bot, user_id, chat_id)


def _maybe_send_pending_daily_bonus_reminder(bot, user_id: int, chat_id: int) -> None:
    unlocked_at = db.get_daily_bonus_unlocked_at(user_id)
    if not unlocked_at:
        return
    _schedule_daily_bonus_reminder(bot, user_id, chat_id)


def _trigger_onboarding(bot, user, chat_id: int) -> None:
    user_id = user["user_id"]
    if user.get("banned"):
        return
    if not user.get("onboarding_pending"):
        _maybe_send_pending_daily_bonus_unlock(bot, user_id, chat_id)
        return
    if db.get_welcome_sent_at(user_id) > 0:
        db.set_onboarding_pending(user_id, False)
        _maybe_send_pending_daily_bonus_unlock(bot, user_id, chat_id)
        return
    lang = db.get_user_lang(user_id, "fa")
    try:
        bot.send_message(chat_id, t("onboarding_welcome", lang))
    except Exception:
        return
    db.set_welcome_sent_at(user_id, int(time.time()))
    db.set_onboarding_pending(user_id, False)
    timer = threading.Timer(ONBOARDING_DAILY_BONUS_DELAY, _send_daily_bonus_ready, args=(bot, user_id, chat_id))
    timer.daemon = True
    timer.start()


def _apply_referral(bot, user, ref_code: str, chat_id: int, user_lang: str) -> None:
    ref_code = (ref_code or "").strip()
    if not ref_code:
        return

    if user.get("referred_by"):
        return

    ref_user = db.get_user(int(ref_code)) if ref_code.isdigit() else None
    if not ref_user or ref_user["user_id"] == user["user_id"]:
        return

    try:
        db.set_referred_by(user["user_id"], ref_user["user_id"])
    except Exception:
        pass

    bonus = int(db.get_setting("BONUS_REFERRAL", "30") or 30)
    try:
        db.add_credits(ref_user["user_id"], bonus)
    except Exception:
        pass

    ref_lang = db.get_user_lang(ref_user["user_id"], "fa")
    free_credits = int(db.get_setting("FREE_CREDIT", "80") or 80)
    try:
        bot.send_message(chat_id, t("ref_welcome", user_lang).format(credits=free_credits))
    except Exception:
        pass
    try:
        bot.send_message(ref_user["user_id"], t("ref_notify", ref_lang).format(credits=bonus))
    except Exception:
        pass


def _handle_referral(bot, msg: Message, user, lang: str) -> None:
    """Award referral bonus if /start contains a valid ref code."""
    parts = (msg.text or "").split(maxsplit=1)
    if len(parts) < 2:
        return

    ref_code = parts[1].strip()
    _apply_referral(bot, user, ref_code, msg.chat.id, lang)


def _consume_pending_referral(bot, user, chat_id: int, lang: str) -> None:
    state = db.get_state(user["user_id"]) or ""
    if not state.startswith("ref:"):
        return

    ref_code = state.split(":", 1)[1] if ":" in state else ""
    db.clear_state(user["user_id"])
    _apply_referral(bot, user, ref_code, chat_id, lang)


def _ensure_force_sub(bot, user_id: int, chat_id: int, message_id: int | None, lang: str) -> bool:
    return ensure_force_sub(bot, user_id, chat_id, message_id, lang)


def register(bot):
    @bot.message_handler(commands=["start"])
    def start(msg: Message):
        user = db.get_or_create_user(msg.from_user)
        db.touch_last_seen(user["user_id"])
        stored_lang = (user.get("lang") or "").strip()
        lang = stored_lang or "fa"

        parts = (msg.text or "").split(maxsplit=1)
        start_param = parts[1].strip() if len(parts) == 2 else ""

        if user.get("banned"):
            bot.reply_to(msg, t("error_banned", lang))
            return

        if not stored_lang:
            if start_param:
                db.set_state(user["user_id"], f"ref:{start_param}")

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

        if not _ensure_force_sub(bot, user["user_id"], msg.chat.id, msg.message_id, lang):
            return

        _handle_referral(bot, msg, user, lang)
        _consume_pending_referral(bot, user, msg.chat.id, lang)
        send_main_menu(
            bot,
            user["user_id"],
            msg.chat.id,
            MAIN(lang),
            main_menu(lang),
            message_id=msg.message_id,
        )
        _trigger_onboarding(bot, user, msg.chat.id)
        _schedule_low_credit_warning(bot, user, msg.chat.id, LOW_CREDIT_DELAY)

    @bot.message_handler(commands=["help"])
    def help_cmd(msg: Message):
        user = db.get_or_create_user(msg.from_user)
        stored_lang = (user.get("lang") or "").strip()
        lang = stored_lang or "fa"

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

        if not _ensure_force_sub(bot, user["user_id"], msg.chat.id, msg.message_id, lang):
            return

        edit_or_send(bot, msg.chat.id, msg.message_id, HELP(lang), _back_to_home_kb(lang))

    @bot.message_handler(commands=["menu"])
    def menu_cmd(msg: Message):
        user = db.get_or_create_user(msg.from_user)
        stored_lang = (user.get("lang") or "").strip()
        lang = stored_lang or "fa"

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

        if not _ensure_force_sub(bot, user["user_id"], msg.chat.id, msg.message_id, lang):
            return

        send_main_menu(
            bot,
            user["user_id"],
            msg.chat.id,
            MAIN(lang),
            main_menu(lang),
            message_id=msg.message_id,
        )
        _schedule_low_credit_warning(bot, user, msg.chat.id, LOW_CREDIT_DELAY)

    @bot.message_handler(func=lambda m: bool(m.text))
    def menu_text_router(msg: Message):
        user = db.get_or_create_user(msg.from_user)
        stored_lang = (user.get("lang") or "").strip()
        lang = stored_lang or "fa"

        action = menu_actions(lang).get((msg.text or "").strip())
        if not action:
            return

        current_state = db.get_state(msg.from_user.id) or ""
        if current_state.startswith(("tts:wait_text", "tts_openai:wait_text")):
            try:
                parts = current_state.split(":")
                if len(parts) >= 3 and parts[2].isdigit():
                    bot.delete_message(msg.chat.id, int(parts[2]))
            except Exception:
                pass
            db.clear_state(msg.from_user.id)

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

        if not _ensure_force_sub(bot, user["user_id"], msg.chat.id, msg.message_id, lang):
            return

        try:
            bot.delete_message(msg.chat.id, msg.message_id)
        except Exception:
            pass

        menu_message_id = db.get_last_main_menu_id(user["user_id"]) or None

        if action == "profile":
            if not is_feature_enabled("FEATURE_PROFILE"):
                return
            return

        if action == "credit":
            if not is_feature_enabled("FEATURE_CREDIT"):
                bot.reply_to(msg, feature_disabled_text("FEATURE_CREDIT", lang))
                return
            from modules.credit.handlers import open_credit_from_message

            open_credit_from_message(bot, msg, menu_message_id=menu_message_id)
            return

        if action == "tts":
            from modules.tts.handlers import open_tts_from_message

            open_tts_from_message(bot, msg, menu_message_id=menu_message_id)
            return

        if action == "gpt":
            from modules.gpt.handlers import open_gpt_from_message

            open_gpt_from_message(bot, msg, menu_message_id=menu_message_id)
            return

        if action == "lang":
            if not is_feature_enabled("FEATURE_LANG"):
                bot.reply_to(msg, feature_disabled_text("FEATURE_LANG", lang))
                return
            from modules.lang.handlers import open_language_from_message

            open_language_from_message(bot, msg, menu_message_id=menu_message_id)
            return

        if action == "invite":
            if not is_feature_enabled("FEATURE_INVITE"):
                bot.reply_to(msg, feature_disabled_text("FEATURE_INVITE", lang))
                return
            from modules.invite.handlers import open_invite_from_message

            open_invite_from_message(bot, msg, menu_message_id=menu_message_id)
            return

    @bot.callback_query_handler(
        func=lambda c: (
            c.data
            and c.data.startswith("home:")
            and c.data
            not in {
                "home:gpt_chat",
                "home:api_token",
                "home:anon_chat",
                "home:vexa_assistant",
            }
        )
    )
    def home_router(cq: CallbackQuery):
        user = db.get_or_create_user(cq.from_user)
        db.touch_last_seen(user["user_id"])
        stored_lang = (user.get("lang") or "").strip()
        lang = stored_lang or "fa"

        if not stored_lang:
            from modules.lang.handlers import send_language_menu

            send_language_menu(
                bot,
                user,
                cq.message.chat.id,
                cq.message.message_id,
                force_new=True,
                display_lang="en",
            )
            bot.answer_callback_query(cq.id)
            return

        if not _ensure_force_sub(bot, user["user_id"], cq.message.chat.id, cq.message.message_id, lang):
            bot.answer_callback_query(cq.id)
            return

        route = cq.data.split(":", 1)[1] if ":" in cq.data else ""
        _schedule_low_credit_warning(bot, user, cq.message.chat.id, LOW_CREDIT_DELAY)

        if route in ("", "back"):
            send_main_menu(
                bot,
                user["user_id"],
                cq.message.chat.id,
                MAIN(lang),
                main_menu(lang),
                message_id=cq.message.message_id,
            )
            bot.answer_callback_query(cq.id)
            return

        if route == "image":
            if not is_feature_enabled("FEATURE_IMAGE"):
                _handle_feature_disabled(bot, cq, lang, "FEATURE_IMAGE")
                return
            bot.answer_callback_query(cq.id)
            from modules.image.handlers import open_image

            open_image(bot, cq)
            return

        if route == "video":
            if not is_feature_enabled("FEATURE_VIDEO"):
                _handle_feature_disabled(bot, cq, lang, "FEATURE_VIDEO")
                return
            bot.answer_callback_query(cq.id)
            from modules.video_gen4.handlers import open_video

            open_video(bot, cq)
            return

        if route == "tts":
            if not is_feature_enabled("FEATURE_TTS"):
                _handle_feature_disabled(bot, cq, lang, "FEATURE_TTS")
                return
            bot.answer_callback_query(cq.id)
            from modules.tts.handlers import open_tts

            open_tts(bot, cq)
            return
        if route == "profile":
            if not is_feature_enabled("FEATURE_PROFILE"):
                bot.answer_callback_query(
                    cq.id,
                    feature_disabled_text("FEATURE_PROFILE", lang),
                    show_alert=True,
                )
                return
            from modules.profile.handlers import build_balance_alert

            title, body = build_balance_alert(lang, user["user_id"], user["credits"])
            bot.answer_callback_query(cq.id, f"{title}\n\n{body}", show_alert=True)
            return

        if route == "credit":
            if not is_feature_enabled("FEATURE_CREDIT"):
                _handle_feature_disabled(bot, cq, lang, "FEATURE_CREDIT")
                return
            bot.answer_callback_query(cq.id)
            from modules.credit.handlers import open_credit

            open_credit(bot, cq)
            return

        if route == "sora2":
            if not is_feature_enabled("FEATURE_SORA2"):
                _handle_feature_disabled(bot, cq, lang, "FEATURE_SORA2")
                return
            bot.answer_callback_query(cq.id)
            from modules.sora2.handlers import open_sora2_menu

            open_sora2_menu(bot, cq)
            return

        if route == "invite":
            if not is_feature_enabled("FEATURE_INVITE"):
                _handle_feature_disabled(bot, cq, lang, "FEATURE_INVITE")
                return
            bot.answer_callback_query(cq.id)
            from modules.invite.handlers import open_invite

            open_invite(bot, cq)
            return

        if route == "lang":
            if not is_feature_enabled("FEATURE_LANG"):
                _handle_feature_disabled(bot, cq, lang, "FEATURE_LANG")
                return
            bot.answer_callback_query(cq.id)
            from modules.lang.handlers import open_language

            open_language(bot, cq)
            return

        if route == "clone":
            if not is_feature_enabled("FEATURE_CLONE"):
                _handle_feature_disabled(bot, cq, lang, "FEATURE_CLONE")
                return
            bot.answer_callback_query(cq.id)
            from modules.clone.handlers import open_clone

            open_clone(bot, cq)
            return

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("fs:"))
    def force_sub_handler(cq: CallbackQuery):
        user = db.get_or_create_user(cq.from_user)
        db.touch_last_seen(user["user_id"])
        lang = db.get_user_lang(user["user_id"], "fa")

        if cq.data == "fs:recheck":
            settings = db.get_settings()
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings, lang)
            if ok:
                send_main_menu(
                    bot,
                    user["user_id"],
                    cq.message.chat.id,
                    MAIN(lang),
                    main_menu(lang),
                    message_id=cq.message.message_id,
                )
                _consume_pending_referral(bot, user, cq.message.chat.id, lang)
                bot.answer_callback_query(cq.id, t("force_sub_confirmed", lang))
            else:
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, kb)
                bot.answer_callback_query(cq.id, t("force_sub_not_joined", lang))
            return

        bot.answer_callback_query(cq.id)
