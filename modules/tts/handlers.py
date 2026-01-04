# modules/tts/handlers.py
from io import BytesIO
import time
import db
from utils import edit_or_send, ensure_force_sub
from config import DEBUG
from modules.i18n import t
from .texts import TITLE, ask_text, PROCESSING, NO_CREDIT, ERROR, BANNED
from .keyboards import keyboard as tts_keyboard
from .settings import (
    STATE_WAIT_TEXT,
    VOICES,
    DEFAULT_VOICE_NAME,
    CREDIT_PER_CHAR,
    OUTPUTS,  # [{'mime':'audio/mpeg'}, {'mime':'audio/mpeg'}] → دو خروجی MP3
    BANNED_WORDS,
)
from .service import synthesize

# ----------------- filters -----------------
_NORMALIZE_REPLACEMENTS = {
    "ك": "ک",
    "ي": "ی",
    "ى": "ی",
    "ؤ": "و",
    "إ": "ا",
    "أ": "ا",
    "آ": "ا",
    "ة": "ه",
    "ۀ": "ه",
}

def _normalize_text(text: str) -> str:
    normalized = (text or "").lower()
    for src, dst in _NORMALIZE_REPLACEMENTS.items():
        normalized = normalized.replace(src, dst)
    return normalized.replace("ـ", "").replace("\u200c", " ").replace("\u200d", "")

_BANNED_WORDS = tuple(_normalize_text(word) for word in BANNED_WORDS if word)

def _has_banned_word(text: str) -> bool:
    normalized = _normalize_text(text)
    return any(word and word in normalized for word in _BANNED_WORDS)

# ----------------- helpers -----------------
def _parse_state(raw: str):
    """
    state format: 'tts:wait_text:<menu_msg_id>:<voice_name>'
    """
    parts = (raw or "").split(":")
    menu_id = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None
    voice_name = parts[3] if len(parts) >= 4 else DEFAULT_VOICE_NAME
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

        if route == "quality:pro":
            state = db.get_state(cq.from_user.id) or ""
            _, voice_name = _parse_state(state)
            if not voice_name:
                voice_name = DEFAULT_VOICE_NAME

            edit_or_send(
                bot,
                cq.message.chat.id,
                cq.message.message_id,
                ask_text(lang, voice_name),
                tts_keyboard(voice_name, lang, user["user_id"], quality="pro"),
            )
            db.set_state(cq.from_user.id, _make_state(cq.message.message_id, voice_name))
            bot.answer_callback_query(cq.id, t("tts_quality_pro", lang))
            return

        if route == "quality:medium":
            from modules.tts_openai.handlers import open_tts as open_openai_tts

            open_openai_tts(bot, cq)
            bot.answer_callback_query(cq.id, t("tts_quality_medium", lang))
            return

        if route.startswith("voice:"):
            name = route.split(":", 1)[1]

            # بررسی وجود صدا در لیست پیش‌فرض یا کاستوم
            custom_voice_id = db.get_user_voice(user["user_id"], name)
            if name not in VOICES and not custom_voice_id:
                bot.answer_callback_query(cq.id, t("tts_voice_not_found", lang))
                return

            # منوی «متن را بفرست» با صدای انتخابی
            edit_or_send(
                bot,
                cq.message.chat.id,
                cq.message.message_id,
                ask_text(lang, name),
                tts_keyboard(name, lang, user["user_id"], quality="pro"),
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
                    
                    bot.answer_callback_query(
                        cq.id,
                        t("tts_delete_success", lang).format(voice=voice_name),
                    )
                    
                    # بازگشت به منوی انتخاب صدا
                    sel = DEFAULT_VOICE_NAME
                    edit_or_send(
                        bot,
                        cq.message.chat.id,
                        cq.message.message_id,
                        ask_text(lang, sel),
                        tts_keyboard(sel, lang, user["user_id"], quality="pro")
                    )
                    db.set_state(cq.from_user.id, _make_state(cq.message.message_id, sel))
                except Exception as e:
                    bot.answer_callback_query(cq.id, t("tts_delete_error", lang))
                    if DEBUG: print(f"Delete voice error: {e}")
            else:
                bot.answer_callback_query(cq.id, t("tts_voice_not_found", lang))
            return

    # دریافت متن برای تبدیل
    @bot.message_handler(
        func=lambda m: (db.get_state(m.from_user.id) or "").startswith(STATE_WAIT_TEXT),
        content_types=["text"]
    )
    def on_text_to_tts(msg):
        user = db.get_or_create_user(msg.from_user)
        user_id = user["user_id"]
        
        # 🔒 LOCK: جلوگیری از اجرای دوگانه
        lock_key = f"tts_processing_{user_id}"
        current_state = db.get_state(user_id) or ""
        
        # اگر در حالت processing است، return کن (جلوگیری از duplicate)
        if current_state.startswith("tts:processing"):
            return
            
        # تغییر state به processing تا دیگه handler دوباره اجرا نشه
        db.set_state(user_id, f"tts:processing:{int(time.time())}")
        
        try:
            lang = db.get_user_lang(user_id, "fa")

            if not ensure_force_sub(bot, user_id, msg.chat.id, msg.message_id, lang):
                return

            last_menu_id, voice_name = _parse_state(current_state)
            
            # بررسی صدای پیش‌فرض یا کاستوم
            voice_id = VOICES.get(voice_name)
            if not voice_id:
                # اگر صدای پیش‌فرض نبود، از صداهای کاستوم کاربر بگیر
                voice_id = db.get_user_voice(user_id, voice_name)
                if not voice_id:
                    voice_id = VOICES[DEFAULT_VOICE_NAME]
                    voice_name = DEFAULT_VOICE_NAME

            text = (msg.text or "").strip()
            if not text:
                return

            if _has_banned_word(text):
                bot.send_message(msg.chat.id, BANNED(lang))
                db.set_state(user_id, _make_state(last_menu_id or msg.message_id, voice_name))
                return

            # لاگ مخصوص پنل ادمین (برای خروجی متن‌های TTS)
            try:
                db.log_tts_request(user_id, text)
            except Exception:
                pass

            # محاسبه هزینه: صداهای کاستوم دو برابر هزینه پایه دارند
            is_custom_voice = db.get_user_voice(user_id, voice_name) is not None
            multiplier = 2 if is_custom_voice else 1
            cost = db.normalize_credit_amount(len(text) * CREDIT_PER_CHAR * multiplier)
            balance = db.normalize_credit_amount(user.get("credits", 0))
            if balance < cost:
                # state رو پاک نکن تا بتونیم منوی TTS رو بعداً پاک کنیم
                from .keyboards import no_credit_keyboard
                bot.send_message(
                    msg.chat.id,
                    NO_CREDIT(lang, balance, cost),
                    reply_markup=no_credit_keyboard(lang),
                )
                return

            # کسر کردیت قبل از API call
            if not db.deduct_credits(user_id, cost):
                refreshed = db.get_user(user_id) or {}
                from .keyboards import no_credit_keyboard
                new_balance = db.normalize_credit_amount(refreshed.get("credits", 0))
                bot.send_message(
                    msg.chat.id,
                    NO_CREDIT(lang, new_balance, cost),
                    reply_markup=no_credit_keyboard(lang),
                )
                return

            status = bot.send_message(msg.chat.id, PROCESSING(lang))
            
            # 🎯 فقط یکبار API call
            print(f"🔥 TTS REQUEST: user={user_id}, text_len={len(text)}, voice={voice_name}")
            audio_data = synthesize(text, voice_id, "audio/mpeg")
            print(f"✅ TTS RESPONSE: user={user_id}, audio_size={len(audio_data)} bytes")

            # پاک‌سازی پیام‌ها
            safe_del(bot, status.chat.id, status.message_id)
            if last_menu_id:
                safe_del(bot, msg.chat.id, last_menu_id)

            # ارسال فایل (بدون کپشن) با نام Vexa.mp3
            bio = BytesIO(audio_data)
            bio.name = "Vexa.mp3"
            bot.send_document(msg.chat.id, document=bio)

            # بازگرداندن منوی TTS با صدای فعلی
            new_menu = bot.send_message(
                msg.chat.id,
                ask_text(lang, voice_name),
                reply_markup=tts_keyboard(voice_name, lang, user_id, quality="pro")
            )
            db.set_state(user_id, _make_state(new_menu.message_id, voice_name))

        except Exception as e:
            # برگردان کردیت در صورت خطا
            try:
                db.add_credits(user_id, cost)
                print(f"❌ TTS ERROR: user={user_id}, credits refunded={cost}")
            except:
                pass
            safe_del(bot, status.chat.id if 'status' in locals() else None, status.message_id if 'status' in locals() else None)
            err = ERROR(lang)
            bot.send_message(msg.chat.id, err)
            db.clear_state(user_id)
        
        finally:
            # پاک کردن state processing در هر صورت
            current = db.get_state(user_id) or ""
            if current.startswith("tts:processing"):
                db.clear_state(user_id)

def open_tts(bot, cq):
    user = db.get_or_create_user(cq.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")
    sel = DEFAULT_VOICE_NAME
    edit_or_send(
        bot,
        cq.message.chat.id,
        cq.message.message_id,
        ask_text(lang, sel),
        tts_keyboard(sel, lang, user["user_id"], quality="pro"),
    )
    db.set_state(cq.from_user.id, _make_state(cq.message.message_id, sel))
