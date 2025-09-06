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

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("home:"))
    def home_router(cq):
        user = db.get_or_create_user(cq.from_user)
        db.touch_last_seen(user["user_id"])
        lang = db.get_user_lang(user["user_id"], "fa")

        route = cq.data.split(":", 1)[1]

        if route == "back":  # برگشت به منوی اصلی
            edit_or_send(bot, cq.message.chat.id, cq.message.message_id, MAIN(lang), main_menu(lang))
            return

        if route == "tts":
            bot.answer_callback_query(cq.id)
            from modules.tts.handlers import open_tts
            open_tts(bot, cq); return

        if route == "profile":
            bot.answer_callback_query(cq.id)
            from modules.profile.handlers import open_profile
            open_profile(bot, cq); return

        if route == "credit":
            bot.answer_callback_query(cq.id)
            from modules.credit.handlers import open_credit
            open_credit(bot, cq); return

        if route == "invite":
            bot.answer_callback_query(cq.id)
            from modules.invite.handlers import open_invite
            open_invite(bot, cq); return

        if route == "lang":
            bot.answer_callback_query(cq.id)
            from modules.lang.handlers import open_language
            open_language(bot, cq); return
