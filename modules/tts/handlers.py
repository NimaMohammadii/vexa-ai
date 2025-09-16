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
)
from .service import synthesize

# —————– helpers —————–

def _parse_state(raw: str):
“””
state format: ‘tts:wait_text:<menu_msg_id>:<voice_name>’
“””
parts = (raw or “”).split(”:”)
menu_id = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None
voice_name = parts[3] if len(parts) >= 4 else DEFAULT_VOICE_NAME
return menu_id, voice_name

def _make_state(menu_id: int, voice_name: str) -> str:
return f”{STATE_WAIT_TEXT}:{menu_id}:{voice_name}”

def safe_del(bot, chat_id, message_id):
try:
bot.delete_message(chat_id, message_id)
except Exception:
pass

# —————– public API —————–

def register(bot):
# دکمه‌های داخل منوی TTS
@bot.callback_query_handler(func=lambda c: c.data and c.data.startswith(“tts:”))
def tts_router(cq):
user = db.get_or_create_user(cq.from_user)
lang = db.get_user_lang(user[“user_id”], “fa”)

```
    route = cq.data.split(":", 1)[1]

    if route == "back":
        from modules.home.texts import MAIN
        from modules.home.keyboards import main_menu
        db.clear_state(cq.from_user.id)
        edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang))
        return

    if route.startswith("voice:"):
        name = route.split(":", 1)[1]
        
        # بررسی وجود صدا در لیست پیش‌فرض یا کاستوم
        custom_voice_id = db.get_user_voice(user["user_id"], name)
        if name not in VOICES and not custom_voice_id:
            bot.answer_callback_query(cq.id, "Voice not found")
            return

        # منوی «متن را بفرست» با صدای انتخابی
        edit_or_send(
            bot,
            cq.message.chat.id,
            cq.message.message_id,
            ask_text(lang, name),
            tts_keyboard(name, lang, user["user_id"])
        )
        db.set_state(cq.from_user.id, _make_state(cq.message.message_id, name))
        bot.answer_callback_query(cq.id, name)
        return

    if route.startswith("delete:"):
        voice_name = route.split(":", 1)[1]
        
        # حذف صدای کاستوم
        custom_voice_id = db.get_user_voice(user["user_id"], voice_name)
        if custom_voice_id:
            try:
                # حذف از الون لبز
                from modules.clone.service import delete_voice
                delete_voice(custom_voice_id)
                
                # حذف از دیتابیس
                db.delete_user_voice_by_voice_id(custom_voice_id)
                
                bot.answer_callback_query(cq.id, f"✅ صدای '{voice_name}' حذف شد")
                
                # بازگشت به منوی انتخاب صدا
                sel = DEFAULT_VOICE_NAME
                edit_or_send(
                    bot, 
                    cq.message.chat.id, 
                    cq.message.message_id, 
                    ask_text(lang, sel), 
                    tts_keyboard(sel, lang, user["user_id"])
                )
                db.set_state(cq.from_user.id, _make_state(cq.message.message_id, sel))
            except Exception as e:
                bot.answer_callback_query(cq.id, "❌ خطا در حذف صدا")
                if DEBUG: 
                    print(f"Delete voice error: {e}")
        else:
            bot.answer_callback_query(cq.id, "صدا یافت نشد")
        return

# دریافت متن برای تبدیل
@bot.message_handler(
    func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_WAIT_TEXT),
    content_types=["text"]
)
def on_text_to_tts(msg):
    user = db.get_or_create_user(msg.from_user)
    
    # بررسی عضویت اجباری
    from utils import check_force_sub
    settings = db.get_settings()
    mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
    if mode in ("new", "all"):
        ok, txt, kb = check_force_sub(bot, user["user_id"], settings)
        if not ok:
            edit_or_send(bot, msg.chat.id, msg.message_id, txt, kb)
            return
    
    lang = db.get_user_lang(user["user_id"], "fa")
    raw_state = db.get_state(user["user_id"]) or ""
    last_menu_id, voice_name = _parse_state(raw_state)
    
    # تعیین voice_id (پیش‌فرض یا کاستوم)
    voice_id = VOICES.get(voice_name)
    if not voice_id:
        voice_id = db.get_user_voice(user["user_id"], voice_name)
        if not voice_id:
            voice_id = VOICES[DEFAULT_VOICE_NAME]
            voice_name = DEFAULT_VOICE_NAME

    text = (msg.text or "").strip()
    if not text:
        return

    # لاگ درخواست TTS
    try:
        db.log_tts_request(user["user_id"], text)
    except Exception:
        pass

    # محاسبه هزینه (صداهای کاستوم ۲ کردیت، بقیه ۱ کردیت)
    is_custom_voice = db.get_user_voice(user["user_id"], voice_name) is not None
    cost_per_char = 2 if is_custom_voice else CREDIT_PER_CHAR
    cost = len(text) * cost_per_char
    
    if user["credits"] < cost:
        from .keyboards import no_credit_keyboard
        bot.send_message(
            msg.chat.id, 
            NO_CREDIT(lang, user.get("credits", 0), cost), 
            reply_markup=no_credit_keyboard(lang)
        )
        return

    # پیام در حال پردازش
    status = bot.send_message(msg.chat.id, PROCESSING(lang))
    
    try:
        # تولید فایل صوتی (تک خروجی MP3)
        audio_data = synthesize(text, voice_id, "audio/mpeg")

        # کسر کردیت
        if not db.deduct_credits(user["user_id"], cost):
            safe_del(bot, status.chat.id, status.message_id)
            refreshed = db.get_user(user["user_id"]) or {}
            from .keyboards import no_credit_keyboard
            bot.send_message(
                msg.chat.id, 
                NO_CREDIT(lang, refreshed.get("credits", 0), cost), 
                reply_markup=no_credit_keyboard(lang)
            )
            db.clear_state(user["user_id"])
            return

        # حذف پیام‌های قبلی
        safe_del(bot, status.chat.id, status.message_id)
        if last_menu_id:
            safe_del(bot, msg.chat.id, last_menu_id)

        # ارسال فایل صوتی
        bio = BytesIO(audio_data)
        bio.name = "Vexa.mp3"
        bot.send_document(msg.chat.id, document=bio)

        # نمایش مجدد منوی TTS
        new_menu = bot.send_message(
            msg.chat.id,
            ask_text(lang, voice_name),
            reply_markup=tts_keyboard(voice_name, lang, user["user_id"])
        )
        db.set_state(user["user_id"], _make_state(new_menu.message_id, voice_name))

    except Exception as e:
        safe_del(bot, status.chat.id, status.message_id)
        bot.send_message(msg.chat.id, ERROR(lang))
        db.clear_state(user["user_id"])
        if DEBUG:
            print(f"TTS Error: {e}")
```

def open_tts(bot, cq):
“”“باز کردن منوی TTS با صدای پیش‌فرض”””
user = db.get_or_create_user(cq.from_user)
lang = db.get_user_lang(user[“user_id”], “fa”)
sel = DEFAULT_VOICE_NAME

```
edit_or_send(
    bot, 
    cq.message.chat.id, 
    cq.message.message_id, 
    ask_text(lang, sel), 
    tts_keyboard(sel, lang, user["user_id"])
)
db.set_state(cq.from_user.id, _make_state(cq.message.message_id, sel))
```
