# modules/tts/handlers.py
from io import BytesIO
import db
from utils import edit_or_send
from config import DEBUG
from .texts import TITLE, ask_text, PROCESSING, NO_CREDIT, ERROR
from .keyboards import keyboard as tts_keyboard
from .settings import (
    STATE_WAIT_TEXT,
    VOICES,
    DEFAULT_VOICE_NAME,
    CREDIT_PER_CHAR,
    OUTPUTS,  # [{'mime':'audio/mpeg'}, {'mime':'audio/mpeg'}] → دو خروجی MP3
)
from .service import synthesize

# ----------------- helpers -----------------
def _parse_state(raw: str):
    """
    state format: 'tts:wait_text:<menu_msg_id>:<voice_name>'
    """
    parts = (raw or "").split(":")
    menu_id = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None
    voice_name = parts[3] if len(parts) >= 4 and parts[3] in VOICES else DEFAULT_VOICE_NAME
    return menu_id, voice_name

def _make_state(menu_id: int, voice_name: str) -> str:
    return f"{STATE_WAIT_TEXT}:{menu_id}:{voice_name}"

def safe_del(bot, chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

# ----------------- public API -----------------
def register(bot):
    # دکمه‌های داخل منوی TTS
    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("tts:"))
    def tts_router(cq):
        user = db.get_or_create_user(cq.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")

        route = cq.data.split(":", 1)[1]

        if route == "back":
            from modules.home.texts import MAIN
            from modules.home.keyboards import main_menu
            db.clear_state(cq.from_user.id)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang))
            return

        if route.startswith("voice:"):
            name = route.split(":", 1)[1]
            if name not in VOICES:
                bot.answer_callback_query(cq.id, "Voice not found"); return

            # منوی «متن را بفرست» با صدای انتخابی
            edit_or_send(
                bot,
                cq.message.chat.id,
                cq.message.message_id,
                ask_text(lang, name),
                tts_keyboard(name, lang)
            )
            db.set_state(cq.from_user.id, _make_state(cq.message.message_id, name))
            bot.answer_callback_query(cq.id, name)
            return

    # دریافت متن برای تبدیل
    @bot.message_handler(
        func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_WAIT_TEXT),
        content_types=["text"]
    )
    def on_text_to_tts(msg):
        user = db.get_or_create_user(msg.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")

        raw_state = db.get_state(user["user_id"]) or ""
        last_menu_id, voice_name = _parse_state(raw_state)
        voice_id = VOICES.get(voice_name, VOICES[DEFAULT_VOICE_NAME])

        text = (msg.text or "").strip()
        if not text:
            return

        # لاگ مخصوص پنل ادمین (برای خروجی متن‌های TTS)
        try:
            db.log_tts_request(user["user_id"], text)
        except Exception:
            pass

        cost = len(text) * CREDIT_PER_CHAR
        if user["credits"] < cost:
            db.clear_state(user["user_id"])
            bot.send_message(msg.chat.id, NO_CREDIT(lang, user.get("credits", 0)))
            return

        status = bot.send_message(msg.chat.id, PROCESSING(lang))
        try:
            # ساخت خروجی‌ها (دو MP3)
            produced = [synthesize(text, voice_id, fmt["mime"]) for fmt in OUTPUTS]

            # کسر کردیت
            if not db.deduct_credits(user["user_id"], cost):
                safe_del(bot, status.chat.id, status.message_id)
                # موجودی را تازه‌سازی کن و پیام کمبود اعتبار را با موجودی واقعی بفرست
                refreshed = db.get_user(user["user_id"]) or {}
                bot.send_message(msg.chat.id, NO_CREDIT(lang, refreshed.get("credits", 0)))
                db.clear_state(user["user_id"])
                return

            # پاک‌سازی پیام‌ها
            safe_del(bot, status.chat.id, status.message_id)
            if last_menu_id:
                safe_del(bot, msg.chat.id, last_menu_id)

            # ارسال فایل‌ها (بدون کپشن) با نام Vexa.mp3
            for data in produced:
                bio = BytesIO(data)
                bio.name = "Vexa.mp3"
                bot.send_document(msg.chat.id, document=bio)

            # بازگرداندن منوی TTS با صدای فعلی
            new_menu = bot.send_message(
                msg.chat.id,
                ask_text(lang, voice_name),
                reply_markup=tts_keyboard(voice_name, lang)
            )
            db.set_state(user["user_id"], _make_state(new_menu.message_id, voice_name))

        except Exception as e:
            safe_del(bot, status.chat.id, status.message_id)
            err = ERROR(lang)
            bot.send_message(msg.chat.id, err)
            db.clear_state(user["user_id"])

def open_tts(bot, cq):
    user = db.get_or_create_user(cq.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")
    sel = DEFAULT_VOICE_NAME
    edit_or_send(bot, cq.message.chat.id, cq.message.message_id, ask_text(lang, sel), tts_keyboard(sel, lang))
    db.set_state(cq.from_user.id, _make_state(cq.message.message_id, sel))
