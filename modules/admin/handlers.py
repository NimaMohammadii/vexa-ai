# modules/admin/handlers.py
from telebot import types
from utils import edit_or_send, parse_int
from config import BOT_OWNER_ID
import db

from .texts import (
    TITLE, MENU, DENY, DONE,
    ASK_UID_ADD, ASK_AMT_ADD, STATE_ADD_UID, STATE_ADD_AMT,
    ASK_UID_SUB, ASK_AMT_SUB, STATE_SUB_UID, STATE_SUB_AMT,
    ASK_UID_MSG, ASK_TXT_MSG, STATE_MSG_UID, STATE_MSG_TXT,
    ASK_TXT_CAST, STATE_CAST_TXT,
    ASK_UID_LOOKUP, STATE_USER_LOOKUP,
    ASK_BONUS, STATE_SET_BONUS,
    ASK_FREE,  STATE_SET_FREE,
    ASK_TG,    STATE_SET_TG,
    ASK_IG,    STATE_SET_IG,
)
from .keyboards import admin_menu, settings_menu, users_menu, user_actions, exports_menu

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
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang))
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
            txt = (f"📊 <b>آمار</b>\n\n"
                   f"👥 کل کاربران: <b>{total}</b>\n"
                   f"⚡️ فعال ۲۴ساعت: <b>{active24}</b>")
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
            txt = (f"👤 <b>{uid}</b>\n"
                   f"@{u['username'] or '-'} | 💳 {u['credits']} | "
                   f"{'🚫 بن' if u['banned'] else '✅ مجاز'}")
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, user_actions(uid))
            return

        # بن/آن‌بن
        if action == "ban":
            uid = int(p[2]); db.set_ban(uid, True)
            u = db.get_user(uid)
            txt = (f"👤 <b>{uid}</b>\n@{u['username'] or '-'} | 💳 {u['credits']} | 🚫 بن")
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, user_actions(uid))
            bot.answer_callback_query(cq.id, "کاربر بن شد."); return

        if action == "unban":
            uid = int(p[2]); db.set_ban(uid, False)
            u = db.get_user(uid)
            txt = (f"👤 <b>{uid}</b>\n@{u['username'] or '-'} | 💳 {u['credits']} | ✅ مجاز")
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
            db.set_state(cq.from_user.id, STATE_CAST_TXT)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, ASK_TXT_CAST, admin_menu())
            return

        # تنظیمات و خروجی‌ها
        if action == "settings":
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, "⚙️ تنظیمات ربات:", settings_menu())
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
            uid = int(p[2])
            path = db.export_user_tts_csv(uid)
            with open(path, "rb") as f:
                bot.send_document(cq.message.chat.id, f)
            bot.answer_callback_query(cq.id, "📥 متن‌های TTS ارسال شد.")
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
        txt = (f"👤 <b>{uid}</b>\n"
               f"@{u['username'] or '-'} | 💳 {u['credits']} | "
               f"{'🚫 بن' if u['banned'] else '✅ مجاز'}")
        edit_or_send(bot, msg.chat.id, msg.message_id, txt, user_actions(uid))
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

    # پیام تکی
    @bot.message_handler(func=lambda m: db.get_state(m.from_user.id) == STATE_MSG_UID, content_types=['text', 'photo', 'document', 'audio'])
    def s_msg_uid(msg: types.Message):
        if not _is_owner(msg.from_user): return
        uid = _resolve_user_id(msg.text)
        if not uid: bot.reply_to(msg, "❌ آی‌دی/یوزرنیم معتبر نیست."); return
        if not db.get_user(uid): bot.reply_to(msg, "❌ کاربر یافت نشد."); return
        db.set_state(msg.from_user.id, f"{STATE_MSG_TXT}:{uid}")
        bot.reply_to(msg, ASK_TXT_MSG)

    @bot.message_handler(func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_MSG_TXT), content_types=['text', 'photo', 'document', 'audio'])
    def s_msg_txt(msg: types.Message):
        if not _is_owner(msg.from_user): return
        raw = (db.get_state(msg.from_user.id) or "").split(":")
        uid = int(raw[-1]) if raw and raw[-1].isdigit() else None
        if not uid: db.clear_state(msg.from_user.id); bot.reply_to(msg, "⚠️ وضعیت نامعتبر."); return
        txt = msg.text or ""
        try:
            bot.send_message(uid, txt); db.log_message(uid, "out", txt)
            bot.reply_to(msg, DONE)
        except Exception:
            bot.reply_to(msg, "❌ ارسال نشد (ممکن است کاربر استارت نکرده باشد).")
        db.clear_state(msg.from_user.id)

    # پیام همگانی
    @bot.message_handler(func=lambda m: db.get_state(m.from_user.id) == STATE_CAST_TXT, content_types=['text', 'photo', 'document'])
    def s_cast(msg: types.Message):
        if not _is_owner(msg.from_user): return
        txt = msg.text or ""; sent = 0
        for uid in db.get_all_user_ids():
            try:
                bot.send_message(uid, txt); db.log_message(uid, "out", txt); sent += 1
            except Exception:
                pass
        db.clear_state(msg.from_user.id)
        bot.reply_to(msg, f"{DONE}\n📣 ارسال شد به {sent} کاربر.")

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

    @bot.message_handler(func=lambda m: db.get_state(m.from_user.id) == STATE_SET_IG, content_types=['text'])
    def s_set_ig(msg: types.Message):
        if not _is_owner(msg.from_user): return
        db.set_setting("IG_URL", (msg.text or "").strip())
        db.clear_state(msg.from_user.id)
        bot.reply_to(msg, DONE)
