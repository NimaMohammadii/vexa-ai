from __future__ import annotations
from telebot import TeleBot
from telebot.types import CallbackQuery, Message
import telebot.types as ttypes
import time

from .texts import (
    CREDIT_TITLE, CREDIT_HEADER, PAY_RIAL_TITLE, PAY_RIAL_PLANS_HEADER, INSTANT_PAY_INSTRUCT, WAITING_CONFIRM
)
from .keyboards import credit_menu_kb, stars_packages_kb, payrial_plans_kb, instant_cancel_kb, augment_with_rial
from config import BOT_OWNER_ID as ADMIN_REVIEW_CHAT_ID, CARD_NUMBER
from .settings import PAYMENT_PLANS
from .settings import RECEIPT_WAIT_TTL

# تلاش برای خواندن تنظیمات پرداخت تلگرام از config (اختیاری اضافه کنید)
try:
    from config import TELEGRAM_PAYMENT_PROVIDER_TOKEN  # باید در config شما اضافه شود
except Exception:
    TELEGRAM_PAYMENT_PROVIDER_TOKEN = None

try:
    from config import TELEGRAM_PAYMENT_CURRENCY
except Exception:
    # مقدار پیش‌فرض؛ تنظیمش کنید به ارزی که provider شما پشتیبانی می‌کند (مثلاً "IRR" یا "USD")
    TELEGRAM_PAYMENT_CURRENCY = "USD"

# تلاش برای استفاده از منوی اصلی پروژه‌ی تو؛ اگر نبود، از fallback استفاده می‌کنیم.
try:
    from ..home.keyboards import home_menu_kb  # type: ignore
except Exception:
    home_menu_kb = None

try:
    from ..home.texts import HOME_TITLE  # type: ignore
except Exception:
    HOME_TITLE = "منوی اصلی"

# --- حالت موقت انتظار رسید (بدون دخالت DB) ---
# user_id -> expires_at (epoch)
_RECEIPT_WAIT: dict[int, float] = {}
# user_id -> message_id (برای ادیت کردن پیام بعد از ارسال عکس)
_USER_MESSAGE_IDS: dict[int, int] = {}

def _set_wait(user_id: int, message_id: int = None):
    _RECEIPT_WAIT[user_id] = time.time() + RECEIPT_WAIT_TTL
    if message_id:
        _USER_MESSAGE_IDS[user_id] = message_id

def _clear_wait(user_id: int):
    _RECEIPT_WAIT.pop(user_id, None)
    _USER_MESSAGE_IDS.pop(user_id, None)

def _get_message_id(user_id: int) -> int:
    return _USER_MESSAGE_IDS.get(user_id)

def _is_waiting(user_id: int) -> bool:
    exp = _RECEIPT_WAIT.get(user_id)
    return bool(exp and exp > time.time())

# === API اصلی برای منوی کردیت ===
def open_credit(bot: TeleBot, cq):
    """باز کردن منوی اصلی خرید کردیت"""
    try:
        text = f"💎 <b>{CREDIT_TITLE}</b>\n\n{CREDIT_HEADER}"
        bot.edit_message_text(
            text, cq.message.chat.id, cq.message.message_id,
            parse_mode="HTML", reply_markup=credit_menu_kb()
        )
    except Exception:
        bot.send_message(
            cq.message.chat.id, text,
            parse_mode="HTML", reply_markup=credit_menu_kb()
        )

# === API عمومی برای ادغام با منوی Credit موجود تو ===
def add_rial_button_to_credit_menu(markup):
    """در کد فعلی منوی Credit، قبل از ارسال reply_markup این تابع را صدا بزن:
        markup = add_rial_button_to_credit_menu(markup)
    """
    return augment_with_rial(markup)

def _go_home(bot: TeleBot, chat_id: int, msg_id: int | None = None):
    text = f"🏠 <b>{HOME_TITLE}</b>"
    if msg_id:
        try:
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="HTML",
                                  reply_markup=(home_menu_kb() if callable(home_menu_kb) else None))
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="HTML",
                     reply_markup=(home_menu_kb() if callable(home_menu_kb) else None))

def register(bot: TeleBot):
    """
    رجیستر کردن تمام هندلرهای مربوط به کردیت (Telegram Stars و پرداخت ریالی)
    """
    
    # منوی اصلی کردیت
    @bot.callback_query_handler(func=lambda c: c.data == "credit:menu")
    def on_credit_menu(c):
        bot.answer_callback_query(c.id)
        open_credit(bot, c)
    
    # نمایش بسته‌های Telegram Stars
    @bot.callback_query_handler(func=lambda c: c.data == "credit:stars")
    def on_stars_menu(c):
        bot.answer_callback_query(c.id)
        text = "⭐️ <b>خرید با ستاره تلگرام</b>\n\nیکی از بسته‌های زیر را انتخاب کنید:"
        try:
            bot.edit_message_text(text, c.message.chat.id, c.message.message_id,
                                  parse_mode="HTML", reply_markup=stars_packages_kb())
        except Exception:
            bot.send_message(c.message.chat.id, text, parse_mode="HTML",
                             reply_markup=stars_packages_kb())
    
    # خرید بسته Stars
    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("credit:buy:"))
    def on_buy_stars(c):
        try:
            parts = c.data.split(":")
            stars = int(parts[2])
            credits = int(parts[3])
            
            # ایجاد invoice برای پرداخت
            import json
            payload = json.dumps({"user_id": c.from_user.id, "credits": credits})
            
            # مقدار price باید به کوچک‌ترین واحد پولی ارسال شود (اینجا فرض 2 رقم اعشار)
            # اگر ارز شما قواعد دیگری دارد، تبدیل را مطابق آن تنظیم کنید.
            amount_smallest_unit = int(stars * 100)
            prices = [ttypes.LabeledPrice(label=f"{credits} کردیت", amount=amount_smallest_unit)]
            
            # حتماً provider_token را در config قرار دهید: TELEGRAM_PAYMENT_PROVIDER_TOKEN
            if not TELEGRAM_PAYMENT_PROVIDER_TOKEN:
                bot.answer_callback_query(c.id, "پرداخت غیرفعال است: توکن پرداخت تنظیم نشده")
                return
            
            bot.send_invoice(
                chat_id=c.from_user.id,
                title=f"خرید {credits} کردیت",
                description=f"خرید {credits} کردیت با {stars} ستاره تلگرام",
                payload=payload,
                provider_token=TELEGRAM_PAYMENT_PROVIDER_TOKEN,
                currency=TELEGRAM_PAYMENT_CURRENCY,  # مطمئن شوید provider آن ارز را پشتیبانی می‌کند
                prices=prices
            )
            bot.answer_callback_query(c.id, "لطفاً پرداخت را تکمیل کنید")
            
        except Exception as e:
            # بهتر است لاگ را هم ثبت کنید (print یا logger)
            print("error sending invoice:", e)
            bot.answer_callback_query(c.id, "خطا در ایجاد صورتحساب")
    
    # هندلر pre_checkout_query (ضروری برای Telegram Stars)
    @bot.pre_checkout_query_handler(func=lambda query: True)
    def pre_checkout_handler(pre_checkout_query):
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
    
    # هندلر successful payment
    @bot.message_handler(content_types=['successful_payment'])
    def on_successful_payment(message):
        try:
            import json, db
            user_id = message.from_user.id
            credits = json.loads(message.successful_payment.invoice_payload)["credits"]
            stars = message.successful_payment.total_amount
            
            # اضافه کردن کردیت به حساب کاربر
            user = db.get_or_create_user(message.from_user)
            db.add_credits(user_id, credits)
            
            # ذخیره تراکنش
            db.log_purchase(user_id, stars, credits, message.successful_payment.telegram_payment_charge_id)
            
            bot.send_message(
                message.chat.id,
                f"✅ پرداخت موفق!\n\n💎 {credits} کردیت به حساب شما اضافه شد.\n⭐️ مبلغ: {stars} ستاره",
                parse_mode="HTML"
            )
            
        except Exception as e:
            bot.send_message(message.chat.id, "خطا در پردازش پرداخت")

    # کاربر روی «پرداخت ریالی» کلیک می‌کند → نمایش قیمت‌ها
    @bot.callback_query_handler(func=lambda c: c.data == "credit:payrial")
    def on_payrial(c: CallbackQuery):
        bot.answer_callback_query(c.id)
        
        # فقط قیمت‌ها رو نشون بده
        plans_text = "\n".join([f"• {p['title']}" for p in PAYMENT_PLANS])
        text = (
            f"🧾 <b>{PAY_RIAL_TITLE}</b>\n\n"
            f"{plans_text}"
        )
        
        try:
            bot.edit_message_text(text, c.message.chat.id, c.message.message_id,
                                  parse_mode="HTML", reply_markup=payrial_plans_kb())
        except Exception:
            bot.send_message(c.message.chat.id, text, parse_mode="HTML",
                             reply_markup=payrial_plans_kb())

    # ورود به حالت «پرداخت فوری (کارت‌به‌کارت)» → انتظار دریافت تصویر رسید
    @bot.callback_query_handler(func=lambda c: c.data == "credit:payrial:instant")
    def on_instant(c: CallbackQuery):
        bot.answer_callback_query(c.id)
        _set_wait(c.from_user.id, c.message.message_id)  # ذخیره message_id
        text = INSTANT_PAY_INSTRUCT.format(card=CARD_NUMBER)
        try:
            bot.edit_message_text(text, c.message.chat.id, c.message.message_id,
                                  parse_mode="HTML", reply_markup=instant_cancel_kb())
        except Exception:
            bot.send_message(c.message.chat.id, text, parse_mode="HTML",
                             reply_markup=instant_cancel_kb())

    # بازگشت/لغو → خروج از حالت انتظار و برگشت به منوی اصلی
    @bot.callback_query_handler(func=lambda c: c.data in ("credit:menu", "credit:cancel"))
    def on_back(c: CallbackQuery):
        bot.answer_callback_query(c.id)
        _clear_wait(c.from_user.id)
        # برگشت به منوی اصلی home
        from modules.home.texts import MAIN
        from modules.home.keyboards import main_menu
        import db
        user = db.get_or_create_user(c.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        try:
            bot.edit_message_text(MAIN(lang), c.message.chat.id, c.message.message_id,
                                  parse_mode="HTML", reply_markup=main_menu(lang))
        except Exception:
            bot.send_message(c.message.chat.id, MAIN(lang), parse_mode="HTML",
                             reply_markup=main_menu(lang))

    # دریافت تصویر رسید (فقط وقتی در حالت انتظار است)
    @bot.message_handler(content_types=['photo'])
    def on_receipt(msg: Message):
        if not _is_waiting(msg.from_user.id):
            return  # دخالت نکن؛ این عکس ربطی به پرداخت ندارد

        # گرفتن message_id قبل از پاک کردن
        payment_msg_id = _get_message_id(msg.from_user.id)
        _clear_wait(msg.from_user.id)

        # فوروارد تصویر رسید برای ادمین با اطلاعات کاربر
        caption = (
            "🧾 رسید پرداخت جدید\n"
            f"User ID: <code>{msg.from_user.id}</code>\n"
            f"Username: @{msg.from_user.username or '-'}\n"
            f"Name: {msg.from_user.first_name or ''} {msg.from_user.last_name or ''}"
        )
        try:
            file_id = msg.photo[-1].file_id  # بزرگترین رزولوشن
            bot.send_photo(ADMIN_REVIEW_CHAT_ID, file_id, caption=caption, parse_mode="HTML")
        except Exception:
            pass

        # بارگیری متغیرهای مورد نیاز
        from modules.home.texts import MAIN
        from modules.home.keyboards import main_menu
        import db
        user = db.get_or_create_user(msg.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        
        # 1. پاک کردن پیام قبلی (شماره کارت)
        if payment_msg_id:
            try:
                bot.delete_message(msg.chat.id, payment_msg_id)
            except Exception:
                pass
        
        # 2. ارسال پیام تایید (جداگانه)
        bot.send_message(msg.chat.id, "✅ رسید دریافت شد.\n⏳ لطفاً منتظر تایید ادمین باش.", parse_mode="HTML")
        
        # 3. ارسال منوی اصلی (جداگانه)
        bot.send_message(msg.chat.id, MAIN(lang), parse_mode="HTML", reply_markup=main_menu(lang))
