# modules/clone/handlers.py
import db
from config import DEBUG
from utils import edit_or_send
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from .service import clone_voice_with_cleanup  # صدا وقتی کاربر نام داد استفاده می‌شود

STATE_WAIT_VOICE = "clone:wait_voice"
STATE_WAIT_NAME  = "clone:wait_name"

MENU_TXT   = "🧬 <b>ساخت صدای شخصی – Voice Clone</b>\n\n<b>اینجا می‌تونی صدای خودت یا هر صدایی که دوست داری رو شبیه‌سازی کنی و بعدش فقط با نوشتن متن، همون صدا برات صحبت کنه! 🫧</b>\n\n<b>یک ویس کوتاه (۱۵–۳۰ ثانیه) ارسال کن</b>"
ASK_NAME   = "➕ <b>حالا یک اسم برای صدای جدیدت بفرست</b>"
SUCCESS_TXT= "✅ <b>صدای شخصی ساخته شد و به لیست صداهای شما اضافه شد</b>"
ERROR_TXT  = "❌ <b>خطا در ساخت صدا. دوباره تلاش کن</b>"

def _kb_home():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="home:back"))
    return kb

def open_clone(bot, cq):
    # فقط بازکردن صفحه‌ی کلون (بدون نیاز به import دیگر)
    db.set_state(cq.from_user.id, STATE_WAIT_VOICE)
    
    # ذخیره message_id برای پاک‌سازی بعدی
    if not hasattr(bot, "clone_start_messages"):
        bot.clone_start_messages = {}
    bot.clone_start_messages[cq.from_user.id] = cq.message.message_id
    
    edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MENU_TXT, _kb_home())

def register(bot):
    # استور موقت برای فایل ویس
    if not hasattr(bot, "temp_voice_bytes"):
        bot.temp_voice_bytes = {}

    @bot.callback_query_handler(func=lambda c: c.data == "home:clone")
    def _open_clone_cb(cq):
        try:
            open_clone(bot, cq)
            bot.answer_callback_query(cq.id)
        except Exception as e:
            if DEBUG: print("clone:open error", e)

    # قبول voice + audio + document(اگر audio/* باشد)
    @bot.message_handler(func=lambda m: db.get_state(m.from_user.id) == STATE_WAIT_VOICE,
                         content_types=["voice","audio","document"])
    def _on_voice(msg):
        try:
            # بررسی محدودیت تعداد صداهای کاربر (حداکثر 2 صدا)
            user_voices = db.list_user_voices(msg.from_user.id)
            if len(user_voices) >= 2:
                bot.reply_to(msg, "❌ شما حداکثر ۲ صدای شخصی می‌توانید داشته باشید<b> ابتدا یکی از صداهای قبلی را حذف کنید</b>")
                db.clear_state(msg.from_user.id)
                return
            
            fn, mime, file_id = "audio.wav", "audio/wav", None

            if msg.voice:  # ویس تلگرام (ogg/opus)
                file_id = msg.voice.file_id
                fn, mime = "voice.ogg", "audio/ogg"

            elif msg.audio:  # فایل صوتی (mp3/wav/…)
                file_id = msg.audio.file_id
                # اگر تلگرام filename/mime داد، استفاده کن
                if getattr(msg.audio, "file_name", None): fn = msg.audio.file_name
                if getattr(msg.audio, "mime_type", None): mime = msg.audio.mime_type or mime

            elif msg.document:  # فقط اگر audio/*
                if not (msg.document.mime_type or "").startswith("audio/"):
                    bot.reply_to(msg, "فقط فایل‌های صوتی مجازند (mp3/wav/ogg).")
                    return
                file_id = msg.document.file_id
                fn = msg.document.file_name or fn
                mime = msg.document.mime_type or mime

            fi = bot.get_file(file_id)
            audio = bot.download_file(fi.file_path)

            # ذخیره موقت با متادیتا
            if not hasattr(bot, "temp_voice_bytes"):
                bot.temp_voice_bytes = {}
            bot.temp_voice_bytes[msg.from_user.id] = {"bytes": audio, "filename": fn, "mime": mime}

            db.set_state(msg.from_user.id, STATE_WAIT_NAME)
            bot.send_message(msg.chat.id, ASK_NAME)

        except Exception as e:
            if DEBUG: print("clone:on_voice", e)
            bot.send_message(msg.chat.id, ERROR_TXT)
            db.clear_state(msg.from_user.id)

    # دریافت نام برای صدای ساخته شده
    @bot.message_handler(func=lambda m: db.get_state(m.from_user.id) == STATE_WAIT_NAME,
                         content_types=["text"])
    def _on_name(msg):
        try:
            user_id = msg.from_user.id
            voice_name = msg.text.strip()
            
            if not voice_name:
                bot.reply_to(msg, "❌ نام نمی‌تواند خالی باشد. دوباره تلاش کن.")
                return
            
            # بررسی وجود فایل صوتی موقت
            if not hasattr(bot, "temp_voice_bytes") or user_id not in bot.temp_voice_bytes:
                bot.reply_to(msg, "❌ فایل صوتی یافت نشد. از ابتدا شروع کن.")
                db.clear_state(user_id)
                return
            
            voice_data = bot.temp_voice_bytes[user_id]
            audio_bytes = voice_data["bytes"]
            filename = voice_data["filename"]
            mime = voice_data["mime"]
            
            # ساخت صدای شخصی با ElevenLabs (با پاک‌سازی خودکار)
            voice_id = clone_voice_with_cleanup(audio_bytes, voice_name, filename, mime)
            
            # ذخیره در دیتابیس
            db.add_user_voice(user_id, voice_name, voice_id)
            
            # پاک‌سازی داده‌های موقت
            del bot.temp_voice_bytes[user_id]
            db.clear_state(user_id)
            
            # پاک کردن تمام پیام‌ها و ارسال منوی اصلی جدید
            from modules.home.texts import MAIN
            from modules.home.keyboards import main_menu
            
            user = db.get_or_create_user(msg.from_user)
            lang = db.get_user_lang(user["user_id"], "fa")
            
            try:
                # ارسال پیام موفقیت
                success_msg = bot.send_message(msg.chat.id, SUCCESS_TXT)
                
                # پاک کردن پیام‌های مربوط به ساخت صدا
                try:
                    # اگر message_id شروع ذخیره شده، از اونجا تا الان پاک کن
                    if hasattr(bot, "clone_start_messages") and msg.from_user.id in bot.clone_start_messages:
                        start_msg_id = bot.clone_start_messages[msg.from_user.id]
                        # پاک کردن از پیام شروع تا پیام فعلی
                        for msg_id in range(start_msg_id, msg.message_id + 1):
                            try:
                                bot.delete_message(msg.chat.id, msg_id)
                            except:
                                pass
                        # پاک کردن از حافظه موقت
                        del bot.clone_start_messages[msg.from_user.id]
                    else:
                        # fallback: پاک کردن چند پیام آخر
                        for i in range(1, 6):
                            try:
                                bot.delete_message(msg.chat.id, msg.message_id - i)
                            except:
                                pass
                except:
                    pass
                
                # ارسال منوی اصلی جدید
                bot.send_message(msg.chat.id, MAIN(lang), reply_markup=main_menu(lang))
                
                # پاک کردن پیام موفقیت بعد از ۵ دقیقه (۳۰۰ ثانیه)
                import threading
                def delete_success_message():
                    try:
                        bot.delete_message(msg.chat.id, success_msg.message_id)
                    except:
                        pass
                
                timer = threading.Timer(300.0, delete_success_message)  # ۵ دقیقه = ۳۰۰ ثانیه
                timer.start()
                
            except Exception as e:
                if DEBUG: print(f"Menu refresh error: {e}")
                # در صورت خطا، فقط پیام موفقیت ارسال کن
                bot.send_message(msg.chat.id, SUCCESS_TXT)
            
        except Exception as e:
            if DEBUG: print("clone:on_name", e)
            
            # بررسی نوع خطا برای نمایش پیام مناسب
            error_msg = ERROR_TXT
            error_str = str(e).lower()
            
            if "maximum amount of custom voices" in error_str or "voice limit" in error_str:
                error_msg = "❌ در حال پاک‌سازی صداهای قدیمی و ساخت صدای جدید... لطفاً چند لحظه صبر کنید."
            elif "api" in error_str and "400" in error_str:
                error_msg = "❌ مشکل در پردازش فایل صوتی. لطفاً فایل صوتی با کیفیت بهتر ارسال کنید."
            elif "network" in error_str or "timeout" in error_str:
                error_msg = "❌ مشکل در ارتباط با سرور. لطفاً دوباره تلاش کنید."
            
            bot.send_message(msg.chat.id, error_msg)
            
            # پاک‌سازی در صورت خطا
            if hasattr(bot, "temp_voice_bytes") and msg.from_user.id in bot.temp_voice_bytes:
                del bot.temp_voice_bytes[msg.from_user.id]
            db.clear_state(msg.from_user.id)