# modules/home/handlers.py
import db
from utils import edit_or_send, check_force_sub
from modules.i18n import t
from .texts import MAIN, HELP
from .keyboards import main_menu, _back_to_home_kb


def _handle_referral(bot, msg, user):
    """Apply referral bonuses when /start includes an invite code."""

    parts = (msg.text or "").split(maxsplit=1)
    if len(parts) < 2:
        return

    ref_code = parts[1].strip()
    if user.get("referred_by"):
        return

    ref_user = None
    if ref_code.isdigit():
        ref_user = db.get_user(int(ref_code))

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

    user_lang = db.get_user_lang(user["user_id"], "fa")
    free_credits = int(db.get_setting("FREE_CREDIT", "80") or 80)
    try:
        bot.send_message(msg.chat.id, t("ref_welcome", user_lang).format(credits=free_credits))
    except Exception:
        pass

    ref_lang = db.get_user_lang(ref_user["user_id"], "fa")
    try:
        bot.send_message(ref_user["user_id"], t("ref_notify", ref_lang).format(credits=bonus))
    except Exception:
        pass


def _clear_clone_context(bot, chat_id: int, user_id: int) -> None:
    """Clean up clone-related UI and temporary data when returning home."""

    try:
        if hasattr(bot, "clone_start_messages") and user_id in bot.clone_start_messages:
            clone_msg_id = bot.clone_start_messages[user_id]
            # It is safe to attempt deletion; ignore API errors.
            bot.delete_message(chat_id, clone_msg_id)
            del bot.clone_start_messages[user_id]
    except Exception:
        pass

    db.clear_state(user_id)
    if hasattr(bot, "temp_voice_bytes") and user_id in bot.temp_voice_bytes:
        del bot.temp_voice_bytes[user_id]


def register(bot):
    @bot.message_handler(commands=['start'])
    def start(msg):
        user = db.get_or_create_user(msg.from_user)
        if user.get("banned"):
            bot.reply_to(msg, "⛔️ دسترسی شما مسدود است.")
            return

        db.touch_last_seen(user["user_id"])

        settings = db.get_settings()
        mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
        if mode in ("new", "all"):
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings)
            if not ok:
                edit_or_send(bot, msg.chat.id, msg.message_id, txt, kb)
                return

        _handle_referral(bot, msg, user)

        current_state = db.get_state(user["user_id"]) or ""
        was_gpt = current_state.startswith("gpt:")
        if current_state:
            db.clear_state(user["user_id"])
        if was_gpt:
            db.clear_gpt_history(user["user_id"])

        lang = db.get_user_lang(user["user_id"], "fa")
        start_text = MAIN(lang)
        if was_gpt:
            start_text = f"{t('gpt_end', lang)}\n\n{start_text}"

        edit_or_send(bot, msg.chat.id, msg.message_id, start_text, main_menu(lang))

    @bot.message_handler(commands=['help'])
    def help_cmd(msg):
        user = db.get_or_create_user(msg.from_user)
        if user.get("banned"):
            bot.reply_to(msg, "⛔️ دسترسی شما مسدود است.")
            return

        db.touch_last_seen(user["user_id"])

        settings = db.get_settings()
        mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
        if mode in ("new", "all"):
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings)
            if not ok:
                edit_or_send(bot, msg.chat.id, msg.message_id, txt, kb)
                return

        lang = db.get_user_lang(user["user_id"], "fa")
        edit_or_send(bot, msg.chat.id, msg.message_id, HELP(lang), _back_to_home_kb(lang))

    @bot.message_handler(commands=['menu'])
    def menu_cmd(msg):
        user = db.get_or_create_user(msg.from_user)
        if user.get("banned"):
            bot.reply_to(msg, "⛔️ دسترسی شما مسدود است.")
            return

        db.touch_last_seen(user["user_id"])

        settings = db.get_settings()
        mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
        if mode in ("new", "all"):
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings)
            if not ok:
                edit_or_send(bot, msg.chat.id, msg.message_id, txt, kb)
                return

        lang = db.get_user_lang(user["user_id"], "fa")
        edit_or_send(bot, msg.chat.id, msg.message_id, MAIN(lang), main_menu(lang))

    @bot.callback_query_handler(
        func=lambda c: c.data
        and c.data.startswith("home:")
        and c.data != "home:gpt_chat"
    )
    def home_router(cq):
        user = db.get_or_create_user(cq.from_user)
        if user.get("banned"):
            bot.answer_callback_query(cq.id, "⛔️")
            return

        db.touch_last_seen(user["user_id"])
        lang = db.get_user_lang(user["user_id"], "fa")

        settings = db.get_settings()
        mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
        if mode in ("new", "all"):
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings)
            if not ok:
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, kb)
                bot.answer_callback_query(cq.id)
                return

        route = cq.data.split(":", 1)[1] if ":" in cq.data else ""

        if route in ("", "back"):
            user_state = db.get_state(user["user_id"]) or ""
            if user_state.startswith(("clone:wait_voice", "clone:wait_payment", "clone:wait_name")):
                _clear_clone_context(bot, cq.message.chat.id, user["user_id"])

            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang))
            bot.answer_callback_query(cq.id)
            return

        elif route == "tts":
            bot.answer_callback_query(cq.id)
            from modules.tts.handlers import open_tts

            open_tts(bot, cq)
            return

        elif route == "profile":
            bot.answer_callback_query(cq.id)
            from modules.profile.handlers import open_profile

            open_profile(bot, cq)
            return

        elif route == "credit":
            bot.answer_callback_query(cq.id)
            from modules.credit.handlers import open_credit

            open_credit(bot, cq)
            return

        elif route == "invite":
            bot.answer_callback_query(cq.id)
            from modules.invite.handlers import open_invite

            open_invite(bot, cq)
            return

        elif route == "lang":
            bot.answer_callback_query(cq.id)
            from modules.lang.handlers import open_language

            open_language(bot, cq)
            return

        elif route == "clone":
            bot.answer_callback_query(cq.id)
            from modules.clone.handlers import open_clone

            open_clone(bot, cq)
            return

        bot.answer_callback_query(cq.id)

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("fs:"))
    def force_sub_handler(cq):
        user = db.get_or_create_user(cq.from_user)
        if user.get("banned"):
            bot.answer_callback_query(cq.id, "⛔️")
            return

        db.touch_last_seen(user["user_id"])

        if cq.data == "fs:recheck":
            settings = db.get_settings()
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings)

            if ok:
                lang = db.get_user_lang(user["user_id"], "fa")
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang))
                bot.answer_callback_query(cq.id, "✅ عضویت تایید شد!")
            else:
                bot.answer_callback_query(cq.id, "❌ هنوز عضو نشدی!")
        else:
            bot.answer_callback_query(cq.id)

