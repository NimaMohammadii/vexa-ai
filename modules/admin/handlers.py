# modules/admin/handlers.py
from html import escape
from io import BytesIO
import datetime

from telebot import types

from utils import edit_or_send, parse_int, send_main_menu
from config import BOT_OWNER_ID
import db
import traceback
import os
import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from .texts import (
    TITLE, MENU, DENY, DONE,
    ASK_UID_ADD, ASK_AMT_ADD, STATE_ADD_UID, STATE_ADD_AMT,
    ASK_UID_SUB, ASK_AMT_SUB, STATE_SUB_UID, STATE_SUB_AMT,
    ASK_UID_RESET, STATE_RESET_UID,
    ASK_UID_MSG, ASK_TXT_MSG, STATE_MSG_UID, STATE_MSG_TXT,
    ASK_LANG_CAST, ASK_TXT_CAST, STATE_CAST_LANG, STATE_CAST_TXT,
    ASK_UID_LOOKUP, STATE_USER_LOOKUP,
    ASK_CLONE_TTS, STATE_CLONE_TTS,
    ASK_BONUS, STATE_SET_BONUS,
    ASK_FREE,  STATE_SET_FREE,
    ASK_TG,    STATE_SET_TG,
    ASK_IG,    STATE_SET_IG,
    ASK_FORMULA, STATE_FORMULA,
    ASK_TG_LANG, STATE_SET_TG_LANG,
    ASK_DEMO_LANG, ASK_DEMO_VOICE, ASK_DEMO_AUDIO, STATE_DEMO_AUDIO,
    ASK_WELCOME_AUDIO_LANG, ASK_WELCOME_AUDIO, STATE_WELCOME_AUDIO,
)
from .keyboards import (
    admin_menu,
    settings_menu,
    feature_access_menu,
    users_menu,
    user_actions,
    exports_menu,
    image_users_menu,
    gpt_users_menu,
    daily_reward_users_menu,
    force_sub_lang_list,
    force_sub_lang_menu,
    cast_lang_menu,
    demo_languages_menu,
    demo_voices_menu,
    demo_voice_actions_menu,
    welcome_audio_languages_menu,
    welcome_audio_actions_menu,
    voice_clone_menu,
    voice_clone_actions_menu,
    user_voice_languages_menu,
    user_voice_list_menu,
)
from modules.lang.keyboards import LANGS
from modules.i18n import t
from modules.tts.service import synthesize
from modules.tts.settings import set_demo_audio, clear_demo_audio
from modules.welcome_audio import set_welcome_audio, clear_welcome_audio

LANG_LABELS = {code: label for label, code in LANGS}
MENU_LABELS = {
    "home": "🏠 خانه",
    "profile": "👤 پروفایل",
    "credit": "💳 خرید کردیت",
    "tts": "🎧 متن به گفتار",
    "lang": "🌐 انتخاب زبان",
    "invite": "🎁 دعوت",
    "image": "🖼️ تصویر",
    "video": "🎬 ویدیو",
    "clone": "🧩 کلون صدا",
    "sora2": "🧪 سورا ۲",
}

# ---------- Helpers ----------
def _is_owner(u) -> bool:
    try:
        return int(u.id) == int(BOT_OWNER_ID)
    except Exception:
        return False

def _resolve_user_id(text: str):
    t = (text or "").strip()
    try:
        return parse_int(t)
    except Exception:
        pass
    u = db.get_user_by_username(t)
    return (u and u.get("user_id")) or None


def _format_username_line(user) -> str:
    username = (user or {}).get("username") or ""
    uname = username.strip().lstrip("@")
    if uname:
        return f"🔗 @{escape(uname)}"
    return "🔗 -"


def _format_menu_usage(user_id: int) -> str:
    usage = db.get_user_menu_usage(user_id)
    if not usage:
        return "📊 استفاده از منوها: <b>0</b>"
    total = sum(item.get("count", 0) or 0 for item in usage)
    lines = [f"📊 استفاده از منوها: <b>{total}</b>"]
    for item in usage:
        key = item.get("menu_key") or ""
        label = MENU_LABELS.get(key, key or "—")
        lines.append(f"• {label}: <b>{item.get('count', 0) or 0}</b>")
    return "\n".join(lines)


def _format_user_details(user_id: int, user: dict) -> str:
    lang_code = (user.get("lang") or "fa").strip() or "fa"
    lang_label = LANG_LABELS.get(lang_code, lang_code)
    username = escape((user.get("username") or "-").strip())
    status = "🚫 بن" if user.get("banned") else "✅ مجاز"
    return (
        f"👤 <b>{user_id}</b>\n"
        f"@{username or '-'} | 💳 {db.format_credit_amount(user.get('credits', 0))} | {status}\n"
        f"🌐 زبان: <b>{lang_label}</b>\n"
        f"{_format_menu_usage(user_id)}"
    )

def _send_content_to_user(bot, uid: int, msg: types.Message, reply_markup=None):
    """
    Try to send the admin's message (text/photo/document/audio/voice/video/sticker/...) to `uid`.
    Returns (True, None) on success.
    Returns (False, error_message) on failure. error_message is a short description for debugging.
    The function attempts specific send_* methods first, then copy_message, then forward_message as fallbacks.
    """
    last_err = None
    c = getattr(msg, "content_type", "text")
    try:
        # TEXT
        if c == "text":
            bot.send_message(uid, msg.text or "", reply_markup=reply_markup)
            db.log_message(uid, "out", msg.text or "")
            return True, None

        # PHOTO (use largest size)
        if c == "photo" and getattr(msg, "photo", None):
            file_id = msg.photo[-1].file_id
            try:
                bot.send_photo(uid, file_id, caption=(msg.caption or ""), reply_markup=reply_markup)
                db.log_message(uid, "out", msg.caption or "<photo>")
                return True, None
            except Exception as e:
                last_err = e

        # DOCUMENT
        if c == "document" and getattr(msg, "document", None):
            file_id = msg.document.file_id
            caption = msg.caption or ""
            try:
                bot.send_document(uid, file_id, caption=caption, reply_markup=reply_markup)
                fn = getattr(msg.document, "file_name", "")
                db.log_message(uid, "out", caption or f"<document:{fn}>")
                return True, None
            except Exception as e:
                last_err = e

        # AUDIO (music)
        if c == "audio" and getattr(msg, "audio", None):
            file_id = msg.audio.file_id
            try:
                bot.send_audio(uid, file_id, caption=(msg.caption or ""), reply_markup=reply_markup)
                db.log_message(uid, "out", msg.caption or "<audio>")
                return True, None
            except Exception as e:
                last_err = e

        # VOICE (voice note)
        if c == "voice" and getattr(msg, "voice", None):
            file_id = msg.voice.file_id
            try:
                bot.send_voice(uid, file_id, caption=(msg.caption or ""), reply_markup=reply_markup)
                db.log_message(uid, "out", msg.caption or "<voice>")
                return True, None
            except Exception as e:
                last_err = e

        # VIDEO
        if c == "video" and getattr(msg, "video", None):
            file_id = msg.video.file_id
            try:
                bot.send_video(uid, file_id, caption=(msg.caption or ""), reply_markup=reply_markup)
                db.log_message(uid, "out", msg.caption or "<video>")
                return True, None
            except Exception as e:
                last_err = e

        # STICKER
        if c == "sticker" and getattr(msg, "sticker", None):
            file_id = msg.sticker.file_id
            try:
                bot.send_sticker(uid, file_id, reply_markup=reply_markup)
                db.log_message(uid, "out", "<sticker>")
                return True, None
            except Exception as e:
                last_err = e

        # If specific attempts failed or type not handled above, try copy_message (preferred over forward)
        try:
            # copy_message does not require the bot to be able to access the original chat as a member in the same way forward does,
            # and it preserves media without reuploading whenever possible.
            bot.copy_message(uid, msg.chat.id, msg.message_id, reply_markup=reply_markup)
            db.log_message(uid, "out", f"<copied:{c}>")
            return True, None
        except Exception as e:
            last_err = e

        # Final fallback: try forwarding original message (requires bot to be able to forward)
        try:
            bot.forward_message(uid, msg.chat.id, msg.message_id)
            db.log_message(uid, "out", f"<forwarded:{c}>")
            return True, None
        except Exception as e:
            last_err = e

    except Exception as e:
        last_err = e

    # If we get here, everything failed. Return False and a short error string.
    # Include traceback in stdout for debugging.
    tb = traceback.format_exc()
    print("Error sending admin content to user:", tb)
    err_msg = str(last_err) if last_err else "unknown error"
    return False, err_msg

def _round_half_up(value):
    try:
        dec = Decimal(str(value))
        return int(dec.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("نتیجهٔ فرمول باید عددی باشد.")

def _eval_credit_formula(expr: str, old: int) -> int:
    if not expr:
        raise ValueError("فرمول خالی است.")
    allowed = {name: getattr(math, name) for name in dir(math) if not name.startswith("_")}
    allowed.update({
        "abs": abs,
        "min": min,
        "max": max,
        "round": round,
        "int": int,
        "float": float,
        "pow": pow,
    })
    ctx = dict(allowed)
    ctx.update({
        "old": old,
        "credits": old,
        "x": old,
    })
    try:
        result = eval(expr, {"__builtins__": {}}, ctx)
    except Exception as e:
        raise ValueError(f"خطا در فرمول: {e}")
    return _round_half_up(result)

def _compute_formula_updates(expr: str):
    rows = db.get_all_user_credits()
    updates = []
    preview = []
    for idx, (uid, old) in enumerate(rows):
        try:
            new_value = _eval_credit_formula(expr, old)
        except ValueError as e:
            raise ValueError(f"کاربر {uid}: {e}")
        updates.append((new_value, uid))
        if idx < 20:
            preview.append(f"{uid}: {old} → {new_value}")
    return updates, preview

# ---------- Register ----------
def register(bot):
    @bot.message_handler(commands=['admin'])
    def admin_cmd(msg: types.Message):
        if not _is_owner(msg.from_user):
            bot.reply_to(msg, DENY); return
        db.clear_state(msg.from_user.id)
        edit_or_send(bot, msg.chat.id, msg.message_id, f"{TITLE}\n\n{MENU}", admin_menu())

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("admin:"))
    def router(cq: types.CallbackQuery):
        if not _is_owner(cq.from_user):
            bot.answer_callback_query(cq.id, "⛔️"); return

        p = cq.data.split(":")
        action = p[1]

        # بازگشت به منوی اصلی ربات
        if action == "back":
            from modules.home.texts import MAIN
            from modules.home.keyboards import main_menu
            db.clear_state(cq.from_user.id)
            lang = db.get_user_lang(cq.from_user.id, "fa")
            send_main_menu(
                bot,
                cq.from_user.id,
                cq.message.chat.id,
                MAIN(lang),
                main_menu(lang),
                message_id=cq.message.message_id,
            )
            return

        # منوی ادمین
        if action == "menu":
            db.clear_state(cq.from_user.id)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, f"{TITLE}\n\n{MENU}", admin_menu())
            return

        # آمار
        if action == "stats":
            total = db.count_users()
            try:
                active24 = db.count_active_users(24)
            except TypeError:
                active24 = db.count_active_users()
            try:
                image_users = db.count_users_with_images()
            except AttributeError:
                image_users = 0
            try:
                gpt_users = db.count_users_with_gpt()
            except AttributeError:
                gpt_users = 0
            try:
                daily_reward_users = db.count_daily_reward_users()
                daily_reward_users_24h = db.count_daily_reward_users_since(hours=24)
                daily_reward_users_7d = db.count_daily_reward_users_since(days=7)
            except AttributeError:
                daily_reward_users = 0
                daily_reward_users_24h = 0
                daily_reward_users_7d = 0
            try:
                clone_users = db.count_voice_clone_users()
                clone_total = db.count_voice_clones()
            except AttributeError:
                clone_users = 0
                clone_total = 0
            txt = (f"📊 <b>آمار</b>\n\n"
                   f"👥 کل کاربران: <b>{total}</b>\n"
                   f"⚡️ فعال ۲۴ساعت: <b>{active24}</b>\n"
                   f"🖼️ کاربران تولید تصویر: <b>{image_users}</b>\n"
                   f"🤖 کاربران GPT: <b>{gpt_users}</b>\n"
                   f"🧬 کاربران Voice Clone: <b>{clone_users}</b>\n"
                   f"🎙 تعداد صداهای کلون: <b>{clone_total}</b>\n"
                   f"🎁 پاداش روزانه (کل): <b>{daily_reward_users}</b>\n"
                   f"   ├ ۲۴ ساعت گذشته: <b>{daily_reward_users_24h}</b>\n"
                   f"   └ ۷ روز گذشته: <b>{daily_reward_users_7d}</b>")
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, admin_menu())
            return

        # لیست کاربران
        if action == "users":
            if len(p) >= 4 and p[2] in ("prev", "next"):
                page = int(p[3])
                page = max(0, page - 1) if p[2] == "prev" else page + 1
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, "👥 لیست کاربران:", users_menu(page))
            else:
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, "👥 لیست کاربران:", users_menu())
            return

        if action == "clone":
            if len(p) >= 4 and p[2] in ("prev", "next"):
                page = int(p[3])
                page = max(0, page - 1) if p[2] == "prev" else page + 1
                clone_users = db.count_voice_clone_users()
                clone_total = db.count_voice_clones()
                txt = (
                    "🧬 <b>Voice Clone</b>\n\n"
                    f"👥 کاربران دارای Voice Clone: <b>{clone_users}</b>\n"
                    f"🎙 تعداد صداها: <b>{clone_total}</b>\n\n"
                    "برای مشاهده جزئیات هر صدا روی آن بزنید."
                )
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, voice_clone_menu(page))
                return
            if len(p) >= 4 and p[2] == "voice":
                voice_id = p[3]
                info = db.get_voice_clone_by_id(voice_id)
                if not info:
                    bot.answer_callback_query(cq.id, "صدا یافت نشد.")
                    return
                username = info.get("username") or ""
                first_name = info.get("first_name") or "-"
                created_at = info.get("created_at") or 0
                created_text = "-"
                if created_at:
                    created_text = datetime.datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M")
                username_line = f"@{escape(username)}" if username else "-"
                txt = (
                    "🧬 <b>جزئیات Voice Clone</b>\n\n"
                    f"🎙 صدا: <b>{escape(info.get('voice_name') or '-')}</b>\n"
                    f"👤 کاربر: <b>{info.get('user_id')}</b>\n"
                    f"🔗 یوزرنیم: {username_line}\n"
                    f"🧾 نام: {escape(first_name)}\n"
                    f"🕒 زمان ثبت: <b>{created_text}</b>\n"
                    f"🆔 Voice ID: <code>{escape(info.get('voice_id') or '')}</code>"
                )
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    txt,
                    voice_clone_actions_menu(info["voice_id"], info["user_id"]),
                )
                return
            if len(p) >= 4 and p[2] == "use":
                voice_id = p[3]
                info = db.get_voice_clone_by_id(voice_id)
                if not info:
                    bot.answer_callback_query(cq.id, "صدا یافت نشد.")
                    return
                db.clear_state(cq.from_user.id)
                db.set_state(cq.from_user.id, f"{STATE_CLONE_TTS}:{voice_id}")
                txt = f"{ASK_CLONE_TTS}\n\n🎙 صدا: <b>{escape(info.get('voice_name') or '-') }</b>"
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    txt,
                    voice_clone_actions_menu(info["voice_id"], info["user_id"]),
                )
                return
            clone_users = db.count_voice_clone_users()
            clone_total = db.count_voice_clones()
            txt = (
                "🧬 <b>Voice Clone</b>\n\n"
                f"👥 کاربران دارای Voice Clone: <b>{clone_users}</b>\n"
                f"🎙 تعداد صداها: <b>{clone_total}</b>\n\n"
                "برای مشاهده جزئیات هر صدا روی آن بزنید."
            )
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, voice_clone_menu())
            return

        if action == "lang_users":
            stats = db.count_users_by_lang()
            total = sum(count for _, count in stats)
            lines = ["🌐 <b>کاربران بر اساس زبان</b>", ""]

            if not total:
                lines.append("هنوز کاربری ثبت نشده است.")
            else:
                for code, count in stats:
                    label = LANG_LABELS.get(code)
                    if not label:
                        label = code or "نامشخص"
                    if code not in LANG_LABELS and code:
                        label = f"{label} ({code})"
                    if total:
                        percent = (count / total) * 100
                        lines.append(f"• {label}: <b>{count}</b> ({percent:.1f}٪)")
                    else:
                        lines.append(f"• {label}: <b>{count}</b>")

            txt = "\n".join(lines)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, admin_menu())
            return

        # لیست کاربران تولید تصویر
        if action == "image_users":
            if len(p) >= 4 and p[2] in ("prev", "next"):
                page = int(p[3])
                page = max(0, page - 1) if p[2] == "prev" else page + 1
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    "🖼️ کاربران تولید تصویر:",
                    image_users_menu(page),
                )
            else:
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    "🖼️ کاربران تولید تصویر:",
                    image_users_menu(),
                )
            return

        if action == "gpt_users":
            if len(p) >= 4 and p[2] in ("prev", "next"):
                page = int(p[3])
                page = max(0, page - 1) if p[2] == "prev" else page + 1
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    "🤖 کاربران GPT:",
                    gpt_users_menu(page),
                )
            else:
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    "🤖 کاربران GPT:",
                    gpt_users_menu(),
                )
            return

        if action == "daily_reward_users":
            if len(p) >= 4 and p[2] in ("prev", "next"):
                page = int(p[3])
                page = max(0, page - 1) if p[2] == "prev" else page + 1
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    "🎁 کاربران پاداش روزانه:",
                    daily_reward_users_menu(page),
                )
            else:
                count = 0
                try:
                    count = db.count_daily_reward_users()
                except AttributeError:
                    count = 0
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    f"🎁 کاربران پاداش روزانه: <b>{count}</b>",
                    daily_reward_users_menu(),
                )
            return

        # پروفایل یک کاربر / lookup
        if action == "user":
            if len(p) >= 3 and p[2] == "lookup":
                db.clear_state(cq.from_user.id)
                db.set_state(cq.from_user.id, STATE_USER_LOOKUP)
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, ASK_UID_LOOKUP, users_menu())
                return
            uid = int(p[2])
            u = db.get_user(uid)
            if not u:
                bot.answer_callback_query(cq.id, "کاربر یافت نشد."); return
            txt = _format_user_details(uid, u)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, user_actions(uid))
            return

        if action == "user_voices":
            if len(p) >= 4 and p[2] == "lang":
                uid = int(p[3])
                lang_code = p[4] if len(p) >= 5 else "fa"
                label = LANG_LABELS.get(lang_code, lang_code)
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    f"🎙 مدیریت صداهای کاربر ({label})",
                    user_voice_list_menu(uid, lang_code),
                )
                return
            if len(p) >= 4 and p[2] in ("custom", "openai"):
                uid = int(p[3])
                lang_code = p[2]
                label = "صداهای شخصی" if lang_code == "custom" else "صداهای OpenAI"
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    f"🎙 مدیریت {label}",
                    user_voice_list_menu(uid, lang_code),
                )
                return
            if len(p) >= 5 and p[2] == "toggle":
                uid = int(p[3])
                lang_code = p[4]
                voice_name = ":".join(p[5:]).strip()
                if not voice_name:
                    bot.answer_callback_query(cq.id, "❌ نامعتبر")
                    return
                disabled = db.list_disabled_voices(uid, lang_code)
                if voice_name in disabled:
                    db.enable_user_voice(uid, lang_code, voice_name)
                    bot.answer_callback_query(cq.id, "✅ فعال شد.")
                else:
                    db.disable_user_voice(uid, lang_code, voice_name)
                    bot.answer_callback_query(cq.id, "🚫 غیرفعال شد.")
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    "🎙 مدیریت صداهای کاربر",
                    user_voice_list_menu(uid, lang_code),
                )
                return
            if len(p) >= 5 and p[2] == "page":
                uid = int(p[3])
                lang_code = p[4]
                page = int(p[5]) if len(p) >= 6 and p[5].isdigit() else 0
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    "🎙 مدیریت صداهای کاربر",
                    user_voice_list_menu(uid, lang_code, page=page),
                )
                return

            uid = int(p[2]) if len(p) >= 3 and p[2].isdigit() else None
            if uid is None:
                bot.answer_callback_query(cq.id, "❌ آی‌دی نامعتبر")
                return
            edit_or_send(
                bot,
                cq.message.chat.id,
                cq.message.message_id,
                "🎙 زبان صدا را انتخاب کنید:",
                user_voice_languages_menu(uid),
            )
            return

        # بن/آن‌بن
        if action == "ban":
            uid = int(p[2]); db.set_ban(uid, True)
            u = db.get_user(uid)
            txt = _format_user_details(uid, u)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, user_actions(uid))
            bot.answer_callback_query(cq.id, "کاربر بن شد."); return

        if action == "unban":
            uid = int(p[2]); db.set_ban(uid, False)
            u = db.get_user(uid)
            txt = _format_user_details(uid, u)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, user_actions(uid))
            bot.answer_callback_query(cq.id, "کاربر آن‌بن شد."); return

        # افزایش/کسر (مرحله اول: گرفتن UID)
        if action == "add":
            db.clear_state(cq.from_user.id)
            db.set_state(cq.from_user.id, STATE_ADD_UID)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, ASK_UID_ADD, admin_menu())
            return

        if action == "sub":
            db.clear_state(cq.from_user.id)
            db.set_state(cq.from_user.id, STATE_SUB_UID)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, ASK_UID_SUB, admin_menu())
            return

        if action == "bulk_credit":
            db.clear_state(cq.from_user.id)
            db.set_state(cq.from_user.id, STATE_FORMULA)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, ASK_FORMULA, admin_menu())
            return

        if action == "reset":
            db.clear_state(cq.from_user.id)
            db.set_state(cq.from_user.id, STATE_RESET_UID)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, ASK_UID_RESET, admin_menu())
            return

        # از صفحه کاربر—رفتن مستقیم به مقدار
        if action == "uadd":
            uid = int(p[2])
            db.set_state(cq.from_user.id, f"{STATE_ADD_AMT}:{uid}")
            bot.answer_callback_query(cq.id, "مقدار را بفرست."); return

        if action == "usub":
            uid = int(p[2])
            db.set_state(cq.from_user.id, f"{STATE_SUB_AMT}:{uid}")
            bot.answer_callback_query(cq.id, "مقدار را بفرست."); return

        # پیام‌رسانی
        if action == "dm":
            db.clear_state(cq.from_user.id)
            db.set_state(cq.from_user.id, STATE_MSG_UID)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, ASK_UID_MSG, admin_menu())
            return

        if action == "cast":
            db.clear_state(cq.from_user.id)
            db.set_state(cq.from_user.id, STATE_CAST_LANG)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, ASK_LANG_CAST, cast_lang_menu())
            return

        if action == "cast_lang":
            lang_code = p[2] if len(p) >= 3 else "all"
            db.clear_state(cq.from_user.id)
            db.set_state(cq.from_user.id, f"{STATE_CAST_TXT}:{lang_code}")
            label = "همه زبان‌ها" if lang_code == "all" else LANG_LABELS.get(lang_code, lang_code)
            edit_or_send(
                bot,
                cq.message.chat.id,
                cq.message.message_id,
                f"{ASK_TXT_CAST}\n\nزبان انتخاب‌شده: {label}",
                admin_menu(),
            )
            return

        # تنظیمات و خروجی‌ها
        if action == "settings":
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, "⚙️ تنظیمات ربات:", settings_menu())
            return

        if action == "demo":
            if len(p) >= 4 and p[2] == "lang":
                lang_code = p[3]
                db.clear_state(cq.from_user.id)
                label = LANG_LABELS.get(lang_code, lang_code)
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    f"{ASK_DEMO_VOICE}\n\nزبان: <b>{label}</b>",
                    demo_voices_menu(lang_code),
                )
                return
            if len(p) >= 5 and p[2] == "voice":
                lang_code = p[3]
                voice_name = p[4]
                db.clear_state(cq.from_user.id)
                db.set_state(cq.from_user.id, f"{STATE_DEMO_AUDIO}:{lang_code}:{voice_name}")
                label = LANG_LABELS.get(lang_code, lang_code)
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    f"{ASK_DEMO_AUDIO}\n\nزبان: <b>{label}</b>\nصدا: <b>{voice_name}</b>",
                    demo_voice_actions_menu(lang_code, voice_name),
                )
                return
            if len(p) >= 5 and p[2] == "delete":
                lang_code = p[3]
                voice_name = p[4]
                clear_demo_audio(voice_name, lang=lang_code)
                db.clear_state(cq.from_user.id)
                bot.answer_callback_query(cq.id, "🗑 دمو حذف شد.")
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    ASK_DEMO_VOICE,
                    demo_voices_menu(lang_code),
                )
                return
            db.clear_state(cq.from_user.id)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, ASK_DEMO_LANG, demo_languages_menu())
            return

        if action == "welcome_audio":
            if len(p) >= 4 and p[2] == "lang":
                lang_code = p[3]
                db.clear_state(cq.from_user.id)
                db.set_state(cq.from_user.id, f"{STATE_WELCOME_AUDIO}:{lang_code}")
                label = LANG_LABELS.get(lang_code, lang_code)
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    f"{ASK_WELCOME_AUDIO}\n\nزبان: <b>{label}</b>",
                    welcome_audio_actions_menu(lang_code),
                )
                return
            if len(p) >= 4 and p[2] == "delete":
                lang_code = p[3]
                clear_welcome_audio(lang_code)
                db.clear_state(cq.from_user.id)
                bot.answer_callback_query(cq.id, "🗑 پیام خوش‌آمد حذف شد.")
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    ASK_WELCOME_AUDIO_LANG,
                    welcome_audio_languages_menu(),
                )
                return
            db.clear_state(cq.from_user.id)
            edit_or_send(
                bot,
                cq.message.chat.id,
                cq.message.message_id,
                ASK_WELCOME_AUDIO_LANG,
                welcome_audio_languages_menu(),
            )
            return

        if action == "features":
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, "🧩 مدیریت دسترسی بخش‌ها:", feature_access_menu())
            return

        if action == "feature" and len(p) >= 4 and p[2] == "toggle":
            key = p[3]
            cur = (db.get_setting(key, "1") or "1").strip().lower()
            enabled = cur in ("1", "true", "yes", "on", "enabled")
            db.set_setting(key, "0" if enabled else "1")
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, "✅ اعمال شد.", feature_access_menu())
            return

        if action == "fs_lang":
            subaction = p[2] if len(p) > 2 else "list"
            if subaction == "list":
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, "🔐 تنظیم عضویت اجباری بر اساس زبان:", force_sub_lang_list())
                return
            if subaction == "open" and len(p) >= 4:
                lang_code = p[3]
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    f"🔐 عضویت اجباری ({lang_code})",
                    force_sub_lang_menu(lang_code),
                )
                return
            if subaction == "toggle" and len(p) >= 4:
                lang_code = p[3]
                key = f"FORCE_SUB_MODE_{lang_code}"
                cur = (db.get_setting(key, "none") or "none").lower()
                order = ["none", "new", "all"]
                nxt = order[(order.index(cur) + 1) % len(order)] if cur in order else "none"
                db.set_setting(key, nxt)
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    f"✅ اعمال شد.\n\n🔐 عضویت اجباری ({lang_code})",
                    force_sub_lang_menu(lang_code),
                )
                return
            if subaction == "set_tg" and len(p) >= 4:
                lang_code = p[3]
                db.clear_state(cq.from_user.id)
                db.set_state(cq.from_user.id, f"{STATE_SET_TG_LANG}:{lang_code}")
                edit_or_send(
                    bot,
                    cq.message.chat.id,
                    cq.message.message_id,
                    ASK_TG_LANG,
                    force_sub_lang_menu(lang_code),
                )
                return

        if action == "exports":
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, "📤 خروجی‌ها:", exports_menu())
            return

        if action == "set":
            field = p[2]
            db.clear_state(cq.from_user.id)
            if field == "bonus":
                db.set_state(cq.from_user.id, STATE_SET_BONUS)
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, ASK_BONUS, settings_menu()); return
            if field == "free":
                db.set_state(cq.from_user.id, STATE_SET_FREE)
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, ASK_FREE, settings_menu()); return
            if field == "tg":
                db.set_state(cq.from_user.id, STATE_SET_TG)
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, ASK_TG, settings_menu()); return
            if field == "ig":
                db.set_state(cq.from_user.id, STATE_SET_IG)
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, ASK_IG, settings_menu()); return

        if action == "toggle" and len(p) >= 3 and p[2] == "fs":
            cur = (db.get_setting("FORCE_SUB_MODE", "none") or "none").lower()
            order = ["none", "new", "all"]
            nxt = order[(order.index(cur) + 1) % len(order)] if cur in order else "none"
            db.set_setting("FORCE_SUB_MODE", nxt)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, "✅ اعمال شد.", settings_menu())
            return

        # خروجی کلی
        if action == "exp":
            what = p[2]
            if what == "users":
                path = db.export_users_csv()
            elif what == "buy":
                path = db.export_purchases_csv()
            elif what == "msg":
                path = db.export_messages_csv()
            else:
                bot.answer_callback_query(cq.id, "نامعتبر"); return
            with open(path, "rb") as f:
                bot.send_document(cq.message.chat.id, f)
            bot.answer_callback_query(cq.id, "ارسال شد.")
            return

        # خروجی پیام‌های یک کاربر
        if action == "exp_user_msgs":
            uid = int(p[2])
            path = db.export_user_messages_csv(uid)
            with open(path, "rb") as f:
                bot.send_document(cq.message.chat.id, f)
            bot.answer_callback_query(cq.id, "📥 پیام‌های کاربر ارسال شد.")
            return

        # خروجی فقط متن‌های TTS یک کاربر
        if action == "exp_user_tts":
            try:
                uid = int(p[2])
            except Exception:
                bot.answer_callback_query(cq.id, "❌ آی‌دی نامعتبر."); return

            # پاسخ سریع برای جلوگیری از بی‌پاسخ ماندن UI
            try:
                bot.answer_callback_query(cq.id, "در حال آماده‌سازی فایل...")
            except Exception:
                pass

            try:
                path = db.export_user_tts_csv(uid)
                if not path:
                    bot.answer_callback_query(cq.id, "⚠️ برای این کاربر متنی یافت نشد."); return
                if not os.path.isfile(path):
                    bot.answer_callback_query(cq.id, "❌ فایل خروجی پیدا نشد."); return

                try:
                    with open(path, "rb") as f:
                        bot.send_document(cq.message.chat.id, f)
                    bot.answer_callback_query(cq.id, "📥 متن‌های TTS ارسال شد.")
                except Exception:
                    print("Error sending exported TTS file:", traceback.format_exc())
                    bot.answer_callback_query(cq.id, "❌ خطا در ارسال فایل خروجی.")
            except AttributeError:
                bot.answer_callback_query(cq.id, "❌ عملیات خروجی TTS پشتیبانی نمی‌شود (تابع موجود نیست).")
            except Exception:
                print("Error exporting user TTS:", traceback.format_exc())
                bot.answer_callback_query(cq.id, "❌ خطا در تولید فایل خروجی.")
            return

        if action == "exp_user_gpt":
            try:
                uid = int(p[2])
            except Exception:
                bot.answer_callback_query(cq.id, "❌ آی‌دی نامعتبر.")
                return

            try:
                bot.answer_callback_query(cq.id, "در حال آماده‌سازی فایل...")
            except Exception:
                pass

            try:
                path = db.export_user_gpt_messages_csv(uid)
            except AttributeError:
                bot.answer_callback_query(cq.id, "❌ خروجی پیام‌های GPT پشتیبانی نمی‌شود.")
                return
            except Exception:
                print("Error exporting user GPT messages:", traceback.format_exc())
                bot.answer_callback_query(cq.id, "❌ خطا در تولید فایل خروجی.")
                return

            if not path:
                bot.answer_callback_query(cq.id, "⚠️ برای این کاربر گفتگوی GPT ثبت نشده است.")
                return

            if not os.path.isfile(path):
                bot.answer_callback_query(cq.id, "❌ فایل خروجی پیدا نشد.")
                return

            try:
                with open(path, "rb") as f:
                    bot.send_document(cq.message.chat.id, f)
                bot.answer_callback_query(cq.id, "📥 گفتگوهای GPT ارسال شد.")
            except Exception:
                print("Error sending exported GPT file:", traceback.format_exc())
                bot.answer_callback_query(cq.id, "❌ خطا در ارسال فایل خروجی.")
            return

        if action == "exp_user_images":
            try:
                uid = int(p[2])
            except Exception:
                bot.answer_callback_query(cq.id, "❌ آی‌دی نامعتبر."); return

            try:
                result = db.export_user_images_zip(uid)
            except AttributeError:
                bot.answer_callback_query(cq.id, "❌ عملیات خروجی تصاویر پشتیبانی نمی‌شود."); return
            except Exception:
                print("Error exporting user images:", traceback.format_exc())
                bot.answer_callback_query(cq.id, "❌ خطا در تولید فایل خروجی.")
                return

            if not result:
                bot.answer_callback_query(cq.id, "⚠️ برای این کاربر تصویری ثبت نشده است.")
                return

            path = result.get("path") if isinstance(result, dict) else result
            if not path or not os.path.isfile(path):
                bot.answer_callback_query(cq.id, "❌ فایل خروجی پیدا نشد.")
                return

            caption = None
            if isinstance(result, dict):
                total = result.get("total", 0)
                downloaded = result.get("downloaded", 0)
                skipped = result.get("skipped", 0)
                caption = (
                    f"🖼️ {downloaded} از {total} تصویر دانلود شد."
                    if total
                    else "🖼️ آرشیو تصاویر"
                )
                if skipped:
                    caption += f"\n⚠️ {skipped} مورد دانلود نشد."

            try:
                with open(path, "rb") as f:
                    bot.send_document(cq.message.chat.id, f, caption=caption)
                bot.answer_callback_query(cq.id, "📥 فایل تصاویر ارسال شد.")
            except Exception:
                print("Error sending exported images file:", traceback.format_exc())
                bot.answer_callback_query(cq.id, "❌ خطا در ارسال فایل خروجی.")
            finally:
                try:
                    os.remove(path)
                except Exception:
                    pass
            return

        if action == "noop":
            bot.answer_callback_query(cq.id); return

    # ---------- States ----------
    @bot.message_handler(func=lambda m: db.get_state(m.from_user.id) == STATE_USER_LOOKUP, content_types=['text'])
    def s_lookup(msg: types.Message):
        if not _is_owner(msg.from_user): return
        uid = _resolve_user_id(msg.text)
        if not uid:
            bot.reply_to(msg, "❌ آی‌دی/یوزرنیم معتبر نیست."); return
        u = db.get_user(uid)
        if not u:
            bot.reply_to(msg, "❌ کاربر یافت نشد."); return
        txt = _format_user_details(uid, u)
        edit_or_send(bot, msg.chat.id, msg.message_id, txt, user_actions(uid))
        db.clear_state(msg.from_user.id)

    @bot.message_handler(func=lambda m: db.get_state(m.from_user.id) == STATE_FORMULA, content_types=['text'])
    def s_formula(msg: types.Message):
        if not _is_owner(msg.from_user): return
        expr = (msg.text or "").strip()
        try:
            updates, preview = _compute_formula_updates(expr)
        except ValueError as e:
            bot.reply_to(msg, f"❌ {e}")
            return

        if not updates:
            bot.reply_to(msg, "ℹ️ هیچ کاربری برای به‌روزرسانی وجود ندارد.")
            db.clear_state(msg.from_user.id)
            return

        try:
            affected = db.bulk_update_user_credits(updates)
        except Exception:
            print("Error during bulk credit update:", traceback.format_exc())
            bot.reply_to(msg, "❌ خطا در ذخیره‌سازی تغییرات.")
            return

        summary = [f"✅ کردیت {affected} کاربر به‌روزرسانی شد."]
        if preview:
            summary.append("\nنمونه نتایج:")
            summary.extend(f"• {line}" for line in preview)
            remaining = affected - len(preview)
            if remaining > 0:
                summary.append(f"• … و {remaining} کاربر دیگر.")
        bot.reply_to(msg, "\n".join(summary))
        db.clear_state(msg.from_user.id)

    # افزودن کردیت
    @bot.message_handler(func=lambda m: db.get_state(m.from_user.id) == STATE_ADD_UID, content_types=['text'])
    def s_add_uid(msg: types.Message):
        if not _is_owner(msg.from_user): return
        uid = _resolve_user_id(msg.text)
        if not uid: bot.reply_to(msg, "❌ آی‌دی/یوزرنیم معتبر نیست."); return
        if not db.get_user(uid): bot.reply_to(msg, "❌ کاربر یافت نشد."); return
        db.set_state(msg.from_user.id, f"{STATE_ADD_AMT}:{uid}")
        bot.reply_to(msg, ASK_AMT_ADD)

    @bot.message_handler(func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_ADD_AMT), content_types=['text'])
    def s_add_amt(msg: types.Message):
        if not _is_owner(msg.from_user): return
        raw = (db.get_state(msg.from_user.id) or "").split(":")
        uid = int(raw[-1]) if raw and raw[-1].isdigit() else None
        if not uid: db.clear_state(msg.from_user.id); bot.reply_to(msg, "⚠️ وضعیت نامعتبر."); return
        try:
            amt = parse_int(msg.text)
        except Exception:
            bot.reply_to(msg, "❌ فقط عدد."); return
        db.add_credits(uid, amt)
        newc = db.get_user(uid)["credits"]
        bot.reply_to(msg, f"{DONE}\n👤 <code>{uid}</code>\n➕ +{amt}💳\n💼 موجودی: <b>{newc}</b>")
        db.clear_state(msg.from_user.id)

    # کسر کردیت
    @bot.message_handler(func=lambda m: db.get_state(m.from_user.id) == STATE_SUB_UID, content_types=['text'])
    def s_sub_uid(msg: types.Message):
        if not _is_owner(msg.from_user): return
        uid = _resolve_user_id(msg.text)
        if not uid: bot.reply_to(msg, "❌ آی‌دی/یوزرنیم معتبر نیست."); return
        if not db.get_user(uid): bot.reply_to(msg, "❌ کاربر یافت نشد."); return
        db.set_state(msg.from_user.id, f"{STATE_SUB_AMT}:{uid}")
        bot.reply_to(msg, ASK_AMT_SUB)

    @bot.message_handler(func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_SUB_AMT), content_types=['text'])
    def s_sub_amt(msg: types.Message):
        if not _is_owner(msg.from_user): return
        raw = (db.get_state(msg.from_user.id) or "").split(":")
        uid = int(raw[-1]) if raw and raw[-1].isdigit() else None
        if not uid: db.clear_state(msg.from_user.id); bot.reply_to(msg, "⚠️ وضعیت نامعتبر."); return
        try:
            amt = abs(parse_int(msg.text))
        except Exception:
            bot.reply_to(msg, "❌ فقط عدد."); return
        db.add_credits(uid, -amt)
        newc = db.get_user(uid)["credits"]
        bot.reply_to(msg, f"{DONE}\n👤 <code>{uid}</code>\n➖ -{amt}💳\n💼 موجودی: <b>{newc}</b>")
        db.clear_state(msg.from_user.id)

    @bot.message_handler(func=lambda m: db.get_state(m.from_user.id) == STATE_RESET_UID, content_types=['text'])
    def s_reset(msg: types.Message):
        if not _is_owner(msg.from_user): return
        uid = _resolve_user_id(msg.text)
        if not uid:
            bot.reply_to(msg, "❌ آی‌دی/یوزرنیم معتبر نیست."); return
        if not db.reset_user(uid):
            bot.reply_to(msg, "❌ کاربری با این مشخصات یافت نشد یا قبلاً حذف شده است."); return
        bot.reply_to(msg, f"{DONE}\n👤 <code>{uid}</code>\n♻️ اطلاعات کاربر حذف شد و باید دوباره استارت کند.")
        db.clear_state(msg.from_user.id)

    # پیام تکی
    @bot.message_handler(func=lambda m: db.get_state(m.from_user.id) == STATE_MSG_UID, content_types=['text', 'photo', 'document', 'audio', 'voice', 'video', 'sticker'])
    def s_msg_uid(msg: types.Message):
        if not _is_owner(msg.from_user): return
        # Allow admin to send UID either as plain text or as a reply with text.
        text = msg.text or ""
        if not text and msg.reply_to_message and (msg.reply_to_message.text):
            text = msg.reply_to_message.text
        uid = _resolve_user_id(text)
        if not uid:
            bot.reply_to(msg, "❌ آی‌دی/یوزرنیم معتبر نیست."); return
        if not db.get_user(uid): bot.reply_to(msg, "❌ کاربر یافت نشد."); return
        db.set_state(msg.from_user.id, f"{STATE_MSG_TXT}:{uid}")
        bot.reply_to(msg, ASK_TXT_MSG)

    @bot.message_handler(func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_MSG_TXT), content_types=['text', 'photo', 'document', 'audio', 'voice', 'video', 'sticker'])
    def s_msg_txt(msg: types.Message):
        if not _is_owner(msg.from_user): return
        state_raw = db.get_state(msg.from_user.id) or ""
        raw = state_raw.split(":")
        uid = None
        for part in reversed(raw):
            if part.isdigit():
                uid = int(part)
                break
        if not uid:
            db.clear_state(msg.from_user.id); bot.reply_to(msg, "⚠️ وضعیت نامعتبر."); return

        lang = db.get_user_lang(uid, "fa")

        success, err = _send_content_to_user(bot, uid, msg)
        if success:
            bot.reply_to(msg, DONE)
        else:
            # give a clearer message and include the error string for debugging
            bot.reply_to(msg, f"❌ ارسال نشد: {err}\n(ممکن است کاربر استارت نکرده باشد یا خطای دیگری وجود دارد.)")

        db.clear_state(msg.from_user.id)

    # پیام همگانی
    @bot.message_handler(func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_CAST_TXT), content_types=['text', 'photo', 'document', 'audio', 'voice', 'video', 'sticker'])
    def s_cast(msg: types.Message):
        if not _is_owner(msg.from_user): return
        sent = 0
        state_raw = db.get_state(msg.from_user.id) or ""
        parts = state_raw.split(":")
        lang_code = parts[-1] if len(parts) >= 3 else "all"
        user_ids = db.get_all_user_ids() if lang_code == "all" else db.get_user_ids_by_lang(lang_code)
        for uid in user_ids:
            try:
                ok, err = _send_content_to_user(bot, uid, msg)
                if ok:
                    sent += 1
            except Exception:
                # keep sending to others even on errors
                print("Error during cast to", uid, traceback.format_exc())
                pass
        db.clear_state(msg.from_user.id)
        bot.reply_to(msg, f"{DONE}\n📣 ارسال شد به {sent} کاربر.")

    @bot.message_handler(func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_CLONE_TTS), content_types=['text'])
    def s_clone_tts(msg: types.Message):
        if not _is_owner(msg.from_user): return
        state_raw = db.get_state(msg.from_user.id) or ""
        parts = state_raw.split(":")
        voice_id = parts[-1] if len(parts) >= 4 else ""
        text = (msg.text or "").strip()
        if not voice_id:
            db.clear_state(msg.from_user.id)
            bot.reply_to(msg, "⚠️ وضعیت نامعتبر.")
            return
        if not text:
            bot.reply_to(msg, "❌ متن خالی است.")
            return

        status = bot.reply_to(msg, "⏳ در حال ساخت صدا...")
        try:
            audio_data = synthesize(text, voice_id, "audio/mpeg")
            bio = BytesIO(audio_data)
            bio.name = "Vexa-Admin-Clone.mp3"
            bot.send_document(msg.chat.id, document=bio)
            bot.reply_to(msg, DONE)
            db.clear_state(msg.from_user.id)
        except Exception:
            print("Error generating clone audio:", traceback.format_exc())
            bot.reply_to(msg, "❌ خطا در ساخت صدا.")
        finally:
            try:
                bot.delete_message(status.chat.id, status.message_id)
            except Exception:
                pass

    # تنظیمات
    @bot.message_handler(func=lambda m: db.get_state(m.from_user.id) == STATE_SET_BONUS, content_types=['text', 'photo', 'document'])
    def s_set_bonus(msg: types.Message):
        if not _is_owner(msg.from_user): return
        try:
            val = parse_int(msg.text)
        except Exception:
            bot.reply_to(msg, "❌ فقط عدد."); return
        db.set_setting("BONUS_REFERRAL", val)
        db.clear_state(msg.from_user.id)
        bot.reply_to(msg, f"{DONE}\n🎁 بونوس رفرال: <b>{val}</b>")

    @bot.message_handler(func=lambda m: db.get_state(m.from_user.id) == STATE_SET_FREE, content_types=['text', 'photo', 'document'])
    def s_set_free(msg: types.Message):
        if not _is_owner(msg.from_user): return
        try:
            val = parse_int(msg.text)
        except Exception:
            bot.reply_to(msg, "❌ فقط عدد."); return
        db.set_setting("FREE_CREDIT", val)
        db.clear_state(msg.from_user.id)
        bot.reply_to(msg, f"{DONE}\n🎉 کردیت شروع: <b>{val}</b>")

    @bot.message_handler(func=lambda m: db.get_state(m.from_user.id) == STATE_SET_TG, content_types=['text'])
    def s_set_tg(msg: types.Message):
        if not _is_owner(msg.from_user): return
        db.set_setting("TG_CHANNEL", (msg.text or "").strip())
        db.clear_state(msg.from_user.id)
        bot.reply_to(msg, DONE)

    @bot.message_handler(func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_SET_TG_LANG), content_types=['text'])
    def s_set_tg_lang(msg: types.Message):
        if not _is_owner(msg.from_user): return
        raw_state = db.get_state(msg.from_user.id) or ""
        parts = raw_state.split(":")
        lang_code = parts[-1] if parts else ""
        if not lang_code:
            db.clear_state(msg.from_user.id)
            bot.reply_to(msg, "⚠️ وضعیت نامعتبر.")
            return
        db.set_setting(f"TG_CHANNEL_{lang_code}", (msg.text or "").strip())
        db.clear_state(msg.from_user.id)
        bot.reply_to(msg, DONE)

    @bot.message_handler(func=lambda m: db.get_state(m.from_user.id) == STATE_SET_IG, content_types=['text'])
    def s_set_ig(msg: types.Message):
        if not _is_owner(msg.from_user): return
        db.set_setting("IG_URL", (msg.text or "").strip())
        db.clear_state(msg.from_user.id)
        bot.reply_to(msg, DONE)

    @bot.message_handler(
        func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_DEMO_AUDIO),
        content_types=['audio', 'voice', 'document'],
    )
    def s_set_demo_audio(msg: types.Message):
        if not _is_owner(msg.from_user): return
        raw_state = db.get_state(msg.from_user.id) or ""
        parts = raw_state.split(":")
        if len(parts) < 3:
            db.clear_state(msg.from_user.id)
            bot.reply_to(msg, "⚠️ وضعیت نامعتبر.")
            return
        lang_code = parts[-2]
        voice_name = parts[-1]
        if not voice_name or not lang_code:
            db.clear_state(msg.from_user.id)
            bot.reply_to(msg, "⚠️ وضعیت نامعتبر.")
            return

        file_id = None
        kind = "audio"
        if getattr(msg, "audio", None):
            file_id = msg.audio.file_id
            kind = "audio"
        elif getattr(msg, "voice", None):
            file_id = msg.voice.file_id
            kind = "voice"
        elif getattr(msg, "document", None):
            mime_type = getattr(msg.document, "mime_type", "") or ""
            if mime_type and not mime_type.startswith("audio/"):
                bot.reply_to(msg, "❌ فایل باید صوتی باشد.")
                return
            file_id = msg.document.file_id
            kind = "document"

        if not file_id:
            bot.reply_to(msg, "❌ فایل صوتی ارسال کنید.")
            return

        set_demo_audio(voice_name, file_id, kind=kind, lang=lang_code)
        db.clear_state(msg.from_user.id)
        lang_label = LANG_LABELS.get(lang_code, lang_code)
        bot.reply_to(msg, f"{DONE}\n🎧 دمو برای <b>{voice_name}</b> ({lang_label}) ذخیره شد.")

    @bot.message_handler(
        func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_WELCOME_AUDIO),
        content_types=['audio', 'voice', 'document'],
    )
    def s_set_welcome_audio(msg: types.Message):
        if not _is_owner(msg.from_user): return
        raw_state = db.get_state(msg.from_user.id) or ""
        parts = raw_state.split(":")
        if len(parts) < 2:
            db.clear_state(msg.from_user.id)
            bot.reply_to(msg, "⚠️ وضعیت نامعتبر.")
            return
        lang_code = parts[-1]
        if not lang_code:
            db.clear_state(msg.from_user.id)
            bot.reply_to(msg, "⚠️ وضعیت نامعتبر.")
            return

        file_id = None
        kind = "audio"
        if getattr(msg, "audio", None):
            file_id = msg.audio.file_id
            kind = "audio"
        elif getattr(msg, "voice", None):
            file_id = msg.voice.file_id
            kind = "voice"
        elif getattr(msg, "document", None):
            mime_type = getattr(msg.document, "mime_type", "") or ""
            if mime_type and not mime_type.startswith("audio/"):
                bot.reply_to(msg, "❌ فایل باید صوتی باشد.")
                return
            file_id = msg.document.file_id
            kind = "document"

        if not file_id:
            bot.reply_to(msg, "❌ فایل صوتی ارسال کنید.")
            return

        set_welcome_audio(lang_code, file_id, kind=kind)
        db.clear_state(msg.from_user.id)
        lang_label = LANG_LABELS.get(lang_code, lang_code)
        bot.reply_to(msg, f"{DONE}\n🎙 پیام خوش‌آمد ({lang_label}) ذخیره شد.")
