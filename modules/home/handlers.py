# modules/home/handlers.py
import db
from utils import edit_or_send, check_force_sub
from modules.i18n import t
from .texts import MAIN
from .keyboards import main_menu
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def _handle_referral(bot, msg, user):
    """
    اگر /start با پارامتر بود و قبلا رفرال نگرفته، برای معرف بونوس می‌ریزد
    و برای کاربر جدید پیام خوشامد (به زبان خودش) می‌فرستد.
    ref_code در سیستم ما همان user_id معرف به‌صورت str است.
    """
    parts = (msg.text or "").split(maxsplit=1)
    if len(parts) < 2:
        return  # پارامتری ندارد

    ref_code = parts[1].strip()
    # اگر همین کاربر قبلاً با رفرال ثبت شده، دوباره جایزه نده
    if user.get("referred_by"):
        return

    # ref_code → user_id معرف
    ref_user = None
    if ref_code.isdigit():
        ref_user = db.get_user(int(ref_code))

    # شرایط معتبر: معرف وجود داشته باشد و خودش نباشد
    if not ref_user or ref_user["user_id"] == user["user_id"]:
        return

    # ثبت معرف (تابع در db موجود است در نسخه‌های قبل)
    try:
        db.set_referred_by(user["user_id"], ref_user["user_id"])
    except Exception:
        # اگر این تابع در db شما نام دیگری دارد و قبلاً کار می‌کرد،
        # همانجا ثبت می‌شود؛ این except فقط برای جلوگیری از کرش است.
        pass

    # بونوس برای معرف
    bonus = int(db.get_setting("BONUS_REFERRAL", "30") or 30)
    try:
        db.add_credits(ref_user["user_id"], bonus)
    except Exception:
        pass

    # پیام‌ها به زبان هر شخص
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


def register(bot):
    @bot.message_handler(commands=['start'])
    def start(msg):
        # ایجاد/به‌روزرسانی کاربر
        user = db.get_or_create_user(msg.from_user)
        db.touch_last_seen(user["user_id"])
        if user.get("banned"):
            bot.reply_to(msg, "⛔️ دسترسی شما مسدود است."); return

        # Force-Sub اگر فعال است
        settings = db.get_settings()
        mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
        if mode in ("new", "all"):
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings)
            if not ok:
                edit_or_send(bot, msg.chat.id, msg.message_id, txt, kb); return

        # اگر /start با رفرال بود، هندل کن (پیام‌ها چندزبانه)
        _handle_referral(bot, msg, user)

        # منوی اصلی با زبان کاربر
        lang = db.get_user_lang(user["user_id"], "fa")
        edit_or_send(bot, msg.chat.id, msg.message_id, MAIN(lang), main_menu(lang))

    @bot.message_handler(commands=['help'])
    def help_cmd(msg):
        # دستور /help — متن فارسی با یک خط عنوان بولد و دکمهٔ منوی اصلی (ادیت پیام)
        user = db.get_or_create_user(msg.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")

        help_text = (
            "<b>📖 راهنمای استفاده از Vexa</b>\n\n"
            "<b>🔹 کردیت یعنی چی؟</b>\n"
            "هر حرف، فاصله یا علامت = ۱ کردیت\n\n"
            "<b>🔹 کردیت رایگان اولیه:</b>\n"
            "بعد از استارت، <b>۴۵ کردیت رایگان</b> داری\n"
            "یعنی می‌تونی یه جمله کوتاه تست کنی (مثل: «سلام، من Vexa هستم»)\n<b>⏳ ( هر 1000 کردیت = 1:20 دقیقـه محتوا )</b>\n\n"
            "<b>🔹 اگر پیام «موجودی کافی نیست» دیدی:</b>\n"
            "یعنی متن بلندتر از کردیت موجودته\n"
            "مثلاً متن تو ۸۰ کردیت نیاز داشته ولی موجودی فقط ۴۵ بوده\n"
            "✅ <b>راه‌حل:</b> متن کوتاه‌تر بفرست یا اعتبار بخری\n\n"
            "<b>️نکته مهم برای گرفتن بهترین صدا از Vexa</b>\n\n"
            "برای اینکه ویس طبیعی‌تر و حرفه‌ای‌تر باشه، حتماً موقع نوشتن متن از علامت‌گذاری استفاده کنید:\n"
            "    •  جمله‌هاتونو با نقطه (.) جدا کنید.\n"
            "    •  برای مکث کوتاه از ویرگول (،) استفاده کنید.\n"
            "    •  پرسش‌ها رو با علامت سؤال (؟) بنویسید.\n"
            "    •  برای هیجان می‌تونید از ! هم استفاده کنید.\n\n"
            "✍️ مثال:\n"
            "    •  ❌ «سلام خوبی امیدوارم حالت خوب باشه»\n"
            "    •  ✅ «سلام! خوبی؟ امیدوارم حالت خوب باشه.»\n"
        )

        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("منوی اصلی", callback_data="home:back"))

        try:
            # تلاش برای ویرایش یا ارسال پیام با همان الگوی پروژه
            edit_or_send(bot, msg.chat.id, msg.message_id, help_text, kb)
        except Exception:
            # fallback به ارسال عادی با HTML parse mode
            try:
                bot.send_message(msg.chat.id, help_text, reply_markup=kb, parse_mode='HTML')
            except Exception:
                pass

# modules/home/handlers.py  ← فقط تابع register(bot) را جایگزین کن
def register(bot):
    @bot.message_handler(commands=['start'])
    def start(msg):
        user = db.get_or_create_user(msg.from_user)
        db.touch_last_seen(user["user_id"])
        if user.get("banned"):
            bot.reply_to(msg, "⛔️ دسترسی شما مسدود است."); return

        settings = db.get_settings()
        mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
        if mode in ("new","all"):
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings)
            if not ok:
                edit_or_send(bot, msg.chat.id, msg.message_id, txt, kb); return

        _handle_referral(bot, msg, user)
        current_state = db.get_state(user["user_id"]) or ""
        if current_state:
            db.clear_state(user["user_id"])
        if current_state.startswith("gpt:"):
            db.clear_gpt_history(user["user_id"])

        lang = db.get_user_lang(user["user_id"], "fa")
        edit_or_send(bot, msg.chat.id, msg.message_id, MAIN(lang), main_menu(lang))

    @bot.message_handler(commands=['help'])
    def help_cmd(msg):
        # بررسی عضویت اجباری
        user = db.get_or_create_user(msg.from_user)
        settings = db.get_settings()
        mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
        if mode in ("new","all"):
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings)
            if not ok:
                edit_or_send(bot, msg.chat.id, msg.message_id, txt, kb); return
        
        lang = db.get_user_lang(msg.from_user.id, "fa")
        from .texts import HELP
        from .keyboards import _back_to_home_kb
        edit_or_send(bot, msg.chat.id, msg.message_id, HELP(lang), _back_to_home_kb(lang))
    
    @bot.message_handler(commands=['menu'])
    def menu_cmd(msg):
        # بررسی عضویت اجباری
        user = db.get_or_create_user(msg.from_user)
        settings = db.get_settings()
        mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
        if mode in ("new","all"):
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings)
            if not ok:
                edit_or_send(bot, msg.chat.id, msg.message_id, txt, kb); return
        
        lang = db.get_user_lang(msg.from_user.id, "fa")
        edit_or_send(bot, msg.chat.id, msg.message_id, MAIN(lang), main_menu(lang))

    @bot.callback_query_handler(
        func=lambda c: c.data
        and c.data.startswith("home:")
        and c.data != "home:gpt_chat"
    )
    def home_router(cq):
        user = db.get_or_create_user(cq.from_user)
        db.touch_last_seen(user["user_id"])
        lang = db.get_user_lang(user["user_id"], "fa")
        
        # بررسی عضویت اجباری برای تمام اقدامات
        settings = db.get_settings()
        mode = (settings.get("FORCE_SUB_MODE") or "none").lower()
        if mode in ("new","all"):
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings)
            if not ok:
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, txt, kb)
                bot.answer_callback_query(cq.id)
                return

        route = cq.data.split(":", 1)[1] if ":" in cq.data else ""

        if route in ("", "back"):
            # پاک کردن پیام‌های clone اگر کاربر در حین process clone بوده
            user_state = db.get_state(user["user_id"]) or ""
            if user_state.startswith(("clone:wait_voice", "clone:wait_payment", "clone:wait_name")):
                try:
                    if hasattr(bot, "clone_start_messages") and user["user_id"] in bot.clone_start_messages:
                        clone_msg_id = bot.clone_start_messages[user["user_id"]]
                        bot.delete_message(cq.message.chat.id, clone_msg_id)
                        del bot.clone_start_messages[user["user_id"]]
                except Exception:
                    pass
                # پاک کردن state و temp data
                db.clear_state(user["user_id"])
                if hasattr(bot, "temp_voice_bytes") and user["user_id"] in bot.temp_voice_bytes:
                    del bot.temp_voice_bytes[user["user_id"]]
            
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang))
            bot.answer_callback_query(cq.id)
            return

        elif route == "tts":
            bot.answer_callback_query(cq.id)
            from modules.tts.handlers import open_tts
            open_tts(bot, cq); return

        elif route == "profile":
            bot.answer_callback_query(cq.id)
            from modules.profile.handlers import open_profile
            open_profile(bot, cq); return

        elif route == "credit":
            bot.answer_callback_query(cq.id)
            from modules.credit.handlers import open_credit
            open_credit(bot, cq); return

        elif route == "invite":
            bot.answer_callback_query(cq.id)
            from modules.invite.handlers import open_invite
            open_invite(bot, cq); return

        elif route == "lang":
            bot.answer_callback_query(cq.id)
            from modules.lang.handlers import open_language
            open_language(bot, cq); return

        elif route == "clone":
            bot.answer_callback_query(cq.id)
            from modules.clone.handlers import open_clone
            open_clone(bot, cq); return
    
    # هندلر دکمه بررسی مجدد عضویت
    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("fs:"))
    def force_sub_handler(cq):
        user = db.get_or_create_user(cq.from_user)
        db.touch_last_seen(user["user_id"])
        
        if cq.data == "fs:recheck":
            print(f"DEBUG: Force sub recheck for user {user['user_id']}")
            settings = db.get_settings()
            print(f"DEBUG: Settings: FORCE_SUB_MODE={settings.get('FORCE_SUB_MODE')}, TG_CHANNEL={settings.get('TG_CHANNEL')}")
            ok, txt, kb = check_force_sub(bot, user["user_id"], settings)
            
            if ok:
                # کاربر عضو شده، منوی اصلی رو نشان بده
                lang = db.get_user_lang(user["user_id"], "fa")
                edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang))
                bot.answer_callback_query(cq.id, "✅ عضویت تایید شد!")
                print(f"DEBUG: User {user['user_id']} membership confirmed!")
            else:
                # هنوز عضو نشده - فقط alert نشون بده، پیام رو تغییر نده
                bot.answer_callback_query(cq.id, "❌ هنوز عضو نشدی!")
                print(f"DEBUG: User {user['user_id']} still not a member")
        
        else:
            bot.answer_callback_query(cq.id)