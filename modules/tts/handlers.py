# modules/tts/handlers.py
from io import BytesIO
import threading
import time
import db
from utils import (
    edit_or_send,
    ensure_force_sub,
    feature_disabled_text,
    is_feature_enabled,
    is_sound_enabled,
    send_main_menu,
)
from config import DEBUG
from modules.i18n import t
from .texts import TITLE, ask_text, PROCESSING, NO_CREDIT, ERROR, BANNED
from .keyboards import keyboard as tts_keyboard
from .upsell import schedule_creator_upsell
from .settings import (
    STATE_WAIT_TEXT,
    CREDIT_PER_CHAR,
    OUTPUTS,  # [{'mime':'audio/mpeg'}, {'mime':'audio/mpeg'}] → دو خروجی MP3
    BANNED_WORDS,
    get_default_voice_name,
    get_demo_audio,
    get_output_mode,
    get_voices,
    set_output_mode,
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
def _parse_state(raw: str, default_voice_name: str):
    """
    state format: 'tts:wait_text:<menu_msg_id>:<voice_name>'
    """
    parts = (raw or "").split(":")
    menu_id = int(parts[2]) if len(parts) >= 3 and parts[2].isdigit() else None
    voice_name = parts[3] if len(parts) >= 4 else default_voice_name
    return menu_id, voice_name

def _make_state(menu_id: int, voice_name: str) -> str:
    return f"{STATE_WAIT_TEXT}:{menu_id}:{voice_name}"

def _page_key(user_id: int) -> str:
    return f"tts_page:{user_id}"

def _get_page(user_id: int) -> int:
    try:
        return int(db.get_setting(_page_key(user_id), 0) or 0)
    except (TypeError, ValueError):
        return 0

def _set_page(user_id: int, page: int) -> None:
    db.set_setting(_page_key(user_id), max(0, page))

def _get_disabled_voice_sets(user_id: int, lang: str) -> tuple[set[str], set[str]]:
    try:
        disabled_default = db.list_disabled_voices(user_id, lang)
    except Exception:
        disabled_default = set()
    try:
        disabled_custom = db.list_disabled_voices(user_id, "custom")
    except Exception:
        disabled_custom = set()
    return disabled_default, disabled_custom

def _resolve_voice_selection(
    user_id: int,
    lang: str,
    desired_voice: str,
    voices: dict[str, str],
) -> tuple[str, str | None, bool]:
    disabled_default, disabled_custom = _get_disabled_voice_sets(user_id, lang)
    custom_voices = db.list_user_voices(user_id)
    custom_names = [voice[0] for voice in custom_voices]

    if desired_voice in voices and desired_voice not in disabled_default:
        return desired_voice, voices.get(desired_voice), False

    if desired_voice in custom_names and desired_voice not in disabled_custom:
        return desired_voice, db.get_user_voice(user_id, desired_voice), True

    for name in voices.keys():
        if name not in disabled_default:
            return name, voices.get(name), False

    for name in custom_names:
        if name not in disabled_custom:
            return name, db.get_user_voice(user_id, name), True

    return desired_voice, voices.get(desired_voice), False

def safe_del(bot, chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

_DEMO_AUTO_DELETE_SECONDS = 50

def _demo_lock_key(user_id: int, voice_name: str) -> str:
    return f"tts_demo_lock:{user_id}:{voice_name}"

def _get_demo_lock(user_id: int, voice_name: str):
    raw = db.get_setting(_demo_lock_key(user_id, voice_name))
    if not raw:
        return None
    try:
        message_id_str, expires_at_str = raw.split(":", 1)
        return {"message_id": int(message_id_str), "expires_at": int(expires_at_str)}
    except (ValueError, TypeError):
        return None

def _set_demo_lock(user_id: int, voice_name: str, message_id: int, expires_at: int) -> None:
    db.set_setting(_demo_lock_key(user_id, voice_name), f"{message_id}:{expires_at}")

def _clear_demo_lock(user_id: int, voice_name: str, message_id: int | None = None) -> None:
    if message_id is not None:
        current = _get_demo_lock(user_id, voice_name)
        if not current or current["message_id"] != message_id:
            return
    db.set_setting(_demo_lock_key(user_id, voice_name), "")

def _delete_demo_message(bot, chat_id: int, user_id: int, voice_name: str, message_id: int) -> None:
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass
    _clear_demo_lock(user_id, voice_name, message_id=message_id)

def _send_demo_audio(
    bot,
    chat_id: int,
    user_id: int,
    voice_name: str,
    lang: str,
) -> str:
    demo_audio = get_demo_audio(voice_name, lang)
    if not demo_audio:
        bot.send_message(chat_id, t("tts_demo_missing", lang))
        return "missing"
    existing_lock = _get_demo_lock(user_id, voice_name)
    now = int(time.time())
    if existing_lock and existing_lock["expires_at"] > now:
        return "locked"
    if existing_lock:
        _clear_demo_lock(user_id, voice_name, message_id=existing_lock["message_id"])
    file_id = demo_audio["file_id"]
    kind = demo_audio.get("kind", "audio")
    caption = t("tts_demo_caption", lang).format(
        voice=voice_name,
        seconds=_DEMO_AUTO_DELETE_SECONDS,
    )
    if kind == "voice":
        sent = bot.send_voice(chat_id, file_id, caption=caption)
    elif kind == "document":
        sent = bot.send_document(chat_id, file_id, caption=caption)
    else:
        sent = bot.send_audio(chat_id, file_id, caption=caption)
    expires_at = int(time.time()) + _DEMO_AUTO_DELETE_SECONDS
    _set_demo_lock(user_id, voice_name, sent.message_id, expires_at)
    timer = threading.Timer(
        _DEMO_AUTO_DELETE_SECONDS,
        _delete_demo_message,
        args=(bot, chat_id, user_id, voice_name, sent.message_id),
    )
    timer.daemon = True
    timer.start()
    return "sent"

# ----------------- public API -----------------
def register(bot):
    # دکمه‌های داخل منوی TTS
    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("tts:"))
    def tts_router(cq):
        user = db.get_or_create_user(cq.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        output_mode = get_output_mode(user["user_id"])
        if not is_feature_enabled("FEATURE_TTS"):
            edit_or_send(
                bot,
                cq.message.chat.id,
                cq.message.message_id,
                feature_disabled_text("FEATURE_TTS", lang),
                None,
            )
            db.clear_state(cq.from_user.id)
            bot.answer_callback_query(cq.id)
            return

        route = cq.data.split(":", 1)[1]
        if route != "back" and not is_sound_enabled():
            bot.answer_callback_query(cq.id, t("audio_disabled", lang), show_alert=True)
            return

        if route == "back":
            from modules.home.texts import MAIN
            from modules.home.keyboards import main_menu
            db.clear_state(cq.from_user.id)
            send_main_menu(
                bot,
                user["user_id"],
                cq.message.chat.id,
                MAIN(lang),
                main_menu(lang),
                message_id=cq.message.message_id,
            )
            return

        if route == "quality:pro":
            voices = get_voices(lang)
            default_voice_name = get_default_voice_name(lang)
            state = db.get_state(cq.from_user.id) or ""
            _, voice_name = _parse_state(state, default_voice_name)
            if voice_name not in voices:
                voice_name = default_voice_name

            edit_or_send(
                bot,
                cq.message.chat.id,
                cq.message.message_id,
                ask_text(lang, voice_name),
                tts_keyboard(
                    voice_name,
                    lang,
                    user["user_id"],
                    quality="pro",
                    voices=voices,
                    output_mode=output_mode,
                    page=_get_page(user["user_id"]),
                ),
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
            voices = get_voices(lang)

            # بررسی وجود صدا در لیست پیش‌فرض یا کاستوم
            custom_voice_id = db.get_user_voice(user["user_id"], name)
            if name not in voices and not custom_voice_id:
                bot.answer_callback_query(cq.id, t("tts_voice_not_found", lang))
                return
            disabled_default, disabled_custom = _get_disabled_voice_sets(user["user_id"], lang)
            if (name in voices and name in disabled_default) or (
                custom_voice_id and name in disabled_custom
            ):
                bot.answer_callback_query(cq.id, t("tts_voice_disabled", lang))
                return

            # منوی «متن را بفرست» با صدای انتخابی
            edit_or_send(
                bot,
                cq.message.chat.id,
                cq.message.message_id,
                ask_text(lang, name),
                tts_keyboard(
                    name,
                    lang,
                    user["user_id"],
                    quality="pro",
                    voices=voices,
                    output_mode=output_mode,
                    page=_get_page(user["user_id"]),
                ),
            )
            db.set_state(cq.from_user.id, _make_state(cq.message.message_id, name))
            bot.answer_callback_query(cq.id, name)
            return

        if route.startswith("page:"):
            direction = route.split(":", 1)[1]
            current_page = _get_page(user["user_id"])
            next_page = current_page + (1 if direction == "next" else -1)
            voices = get_voices(lang)
            default_voice_name = get_default_voice_name(lang)
            state = db.get_state(cq.from_user.id) or ""
            _, voice_name = _parse_state(state, default_voice_name)
            voice_name, _, _ = _resolve_voice_selection(
                user["user_id"],
                lang,
                voice_name,
                voices,
            )
            _set_page(user["user_id"], next_page)
            edit_or_send(
                bot,
                cq.message.chat.id,
                cq.message.message_id,
                ask_text(lang, voice_name),
                tts_keyboard(
                    voice_name,
                    lang,
                    user["user_id"],
                    quality="pro",
                    voices=voices,
                    output_mode=output_mode,
                    page=_get_page(user["user_id"]),
                ),
            )
            db.set_state(cq.from_user.id, _make_state(cq.message.message_id, voice_name))
            bot.answer_callback_query(cq.id)
            return

        if route == "noop":
            bot.answer_callback_query(cq.id)
            return

        if route.startswith("demo:"):
            voice_name = route.split(":", 1)[1]
            result = _send_demo_audio(bot, cq.message.chat.id, cq.from_user.id, voice_name, lang)
            if result == "sent":
                bot.answer_callback_query(cq.id)
            elif result == "locked":
                bot.answer_callback_query(cq.id, t("tts_demo_wait", lang), show_alert=False)
            else:
                bot.answer_callback_query(cq.id)
            return

        if route.startswith("output:"):
            mode = route.split(":", 1)[1]
            set_output_mode(user["user_id"], mode)
            voices = get_voices(lang)
            default_voice_name = get_default_voice_name(lang)
            state = db.get_state(cq.from_user.id) or ""
            _, voice_name = _parse_state(state, default_voice_name)
            voice_name, _, _ = _resolve_voice_selection(
                user["user_id"],
                lang,
                voice_name,
                voices,
            )
            output_mode = get_output_mode(user["user_id"])
            edit_or_send(
                bot,
                cq.message.chat.id,
                cq.message.message_id,
                ask_text(lang, voice_name),
                tts_keyboard(
                    voice_name,
                    lang,
                    user["user_id"],
                    quality="pro",
                    voices=voices,
                    output_mode=output_mode,
                    page=_get_page(user["user_id"]),
                ),
            )
            db.set_state(cq.from_user.id, _make_state(cq.message.message_id, voice_name))
            bot.answer_callback_query(cq.id)
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
                    voices = get_voices(lang)
                    sel = get_default_voice_name(lang)
                    edit_or_send(
                        bot,
                        cq.message.chat.id,
                        cq.message.message_id,
                        ask_text(lang, sel),
                        tts_keyboard(
                            sel,
                            lang,
                            user["user_id"],
                            quality="pro",
                            voices=voices,
                            output_mode=output_mode,
                            page=_get_page(user["user_id"]),
                        )
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
            if not is_sound_enabled():
                bot.send_message(msg.chat.id, t("audio_disabled", lang))
                voices = get_voices(lang)
                default_voice_name = get_default_voice_name(lang)
                last_menu_id, voice_name = _parse_state(current_state, default_voice_name)
                voice_name, _, _ = _resolve_voice_selection(user_id, lang, voice_name, voices)
                db.set_state(user_id, _make_state(last_menu_id or msg.message_id, voice_name))
                return

            voices = get_voices(lang)
            default_voice_name = get_default_voice_name(lang)
            last_menu_id, voice_name = _parse_state(current_state, default_voice_name)
            voice_name, voice_id, _ = _resolve_voice_selection(
                user_id,
                lang,
                voice_name,
                voices,
            )
            if not voice_id:
                bot.send_message(msg.chat.id, t("tts_voice_disabled", lang))
                db.set_state(user_id, _make_state(last_menu_id or msg.message_id, voice_name))
                return

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
            output_mode = get_output_mode(user_id)
            if output_mode == "voice":
                bot.send_voice(msg.chat.id, voice=bio)
            else:
                bot.send_audio(msg.chat.id, audio=bio)

            # بازگرداندن منوی TTS با صدای فعلی
            new_menu = bot.send_message(
                msg.chat.id,
                ask_text(lang, voice_name),
                reply_markup=tts_keyboard(
                    voice_name,
                    lang,
                    user_id,
                    quality="pro",
                    voices=voices,
                    output_mode=output_mode,
                    page=_get_page(user_id),
                )
            )
            db.set_state(user_id, _make_state(new_menu.message_id, voice_name))
            schedule_creator_upsell(bot, user_id, msg.chat.id)

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
    if not is_feature_enabled("FEATURE_TTS"):
        edit_or_send(
            bot,
            cq.message.chat.id,
            cq.message.message_id,
            feature_disabled_text("FEATURE_TTS", lang),
            None,
        )
        return
    if not is_sound_enabled():
        edit_or_send(
            bot,
            cq.message.chat.id,
            cq.message.message_id,
            t("audio_disabled", lang),
            None,
        )
        return
    voices = get_voices(lang)
    sel = get_default_voice_name(lang)
    sel, _, _ = _resolve_voice_selection(user["user_id"], lang, sel, voices)
    output_mode = get_output_mode(user["user_id"])
    _set_page(user["user_id"], 0)
    edit_or_send(
        bot,
        cq.message.chat.id,
        cq.message.message_id,
        ask_text(lang, sel),
        tts_keyboard(
            sel,
            lang,
            user["user_id"],
            quality="pro",
            voices=voices,
            output_mode=output_mode,
            page=_get_page(user["user_id"]),
        ),
    )
    db.set_state(cq.from_user.id, _make_state(cq.message.message_id, sel))
