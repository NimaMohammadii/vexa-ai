# modules/tts/handlers.py
from io import BytesIO
import db
from utils import edit_or_send
from config import DEBUG
from .texts import ask_text, PROCESSING, NO_CREDIT, ERROR
from .keyboards import keyboard as tts_keyboard
from .settings import (
    STATE_WAIT_TEXT, VOICES, DEFAULT_VOICE_NAME, CREDIT_PER_CHAR, OUTPUTS
)
from .service import synthesize

# -------- helper: ذخیره/خواندن صدای انتخابی با settings (بدون تغییر db.py) --------
def _voice_key(uid: int) -> str:
    return f"user:{uid}:voice"

def get_user_voice(uid: int) -> str | None:
    try:
        v = db.get_setting(_voice_key(uid))
        return v if v in VOICES else None
    except Exception:
        return None

def set_user_voice(uid: int, name: str):
    try:
        db.set_setting(_voice_key(uid), name)
    except Exception:
        pass

def _effective_voice(uid: int) -> str:
    return get_user_voice(uid) or DEFAULT_VOICE_NAME

# -------- state helpers --------
def _parse_state(raw: str):
    # 'tts:wait_text:<menu_msg_id>:<voice_name>'
    parts = (raw or "").split(":")
    menu_id = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None
    vname = parts[3] if len(parts) >= 4 and parts[3] in VOICES else DEFAULT_VOICE_NAME
    return menu_id, vname

def _make_state(menu_id: int, vname: str) -> str:
    return f"{STATE_WAIT_TEXT}:{menu_id}:{vname}"

def _safe_del(bot, chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

# -------- register --------
def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("tts:"))
    def tts_router(cq):
        user = db.get_or_create_user(cq.from_user)
        action = cq.data.split(":", 1)[1]

        if action == "back":
            from modules.home.texts import MAIN
            from modules.home.keyboards import main_menu
            db.clear_state(cq.from_user.id)
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MAIN("fa"), main_menu("fa"))
            return

        if action.startswith("voice:"):
            name = action.split(":", 1)[1]
            if name not in VOICES:
                bot.answer_callback_query(cq.id, "Voice not found"); return

            # ذخیره ترجیح کاربر — مستقل از هر چیز دیگر
            set_user_voice(user["user_id"], name)

            # منوی «متن را بفرست» با صدای جدید
            edit_or_send(
                bot, cq.message.chat.id, cq.message.message_id,
                ask_text("fa", name), tts_keyboard(name, "fa")
            )
            db.set_state(cq.from_user.id, _make_state(cq.message.message_id, name))
            bot.answer_callback_query(cq.id, name)
            return

    @bot.message_handler(
        func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_WAIT_TEXT),
        content_types=['text']
    )
    def on_text_to_tts(msg):
        user = db.get_or_create_user(msg.from_user)

        raw = db.get_state(user["user_id"]) or ""
        last_menu_id, state_voice = _parse_state(raw)

        # همیشه از صدای ذخیره‌شده کاربر استفاده کن (اگر نبود از state/پیش‌فرض)
        voice_name = get_user_voice(user["user_id"]) or state_voice or DEFAULT_VOICE_NAME
        voice_id = VOICES.get(voice_name, VOICES[DEFAULT_VOICE_NAME])

        text = (msg.text or "").strip()
        if not text:
            return

        # لاگ برای خروجی ادمین (متن‌های TTS)
        try:
            db.log_tts_request(user["user_id"], text)
        except Exception:
            pass

        cost = len(text) * CREDIT_PER_CHAR
        if user["credits"] < cost:
            db.clear_state(user["user_id"])
            bot.send_message(msg.chat.id, NO_CREDIT("fa"))
            return

        status = bot.send_message(msg.chat.id, PROCESSING("fa"))
        try:
            produced = [synthesize(text, voice_id, fmt["mime"]) for fmt in OUTPUTS]

            if not db.deduct_credits(user["user_id"], cost):
                _safe_del(bot, status.chat.id, status.message_id)
                bot.send_message(msg.chat.id, NO_CREDIT("fa"))
                db.clear_state(user["user_id"])
                return

            _safe_del(bot, status.chat.id, status.message_id)
            if last_menu_id:
                _safe_del(bot, msg.chat.id, last_menu_id)

            # ارسال دو فایل MP3 با نام ثابت و بدون کپشن
            for data in produced:
                bio = BytesIO(data)
                bio.name = "Vexa.mp3"
                bot.send_document(msg.chat.id, document=bio)

            # بازگشت به منوی TTS با همان صدای انتخابی
            new_menu = bot.send_message(
                msg.chat.id,
                ask_text("fa", voice_name),
                reply_markup=tts_keyboard(voice_name, "fa")
            )
            db.set_state(user["user_id"], _make_state(new_menu.message_id, voice_name))

        except Exception as e:
            _safe_del(bot, status.chat.id, status.message_id)
            err = ERROR("fa") if not DEBUG else f"{ERROR('fa')}\n\n<code>{e}</code>"
            bot.send_message(msg.chat.id, err)
            db.clear_state(user["user_id"])

def open_tts(bot, cq):
    user = db.get_or_create_user(cq.from_user)
    sel = _effective_voice(user["user_id"])
    edit_or_send(
        bot, cq.message.chat.id, cq.message.message_id,
        ask_text("fa", sel), tts_keyboard(sel, "fa")
    )
    db.set_state(cq.from_user.id, _make_state(cq.message.message_id, sel))