from __future__ import annotations
from telebot import TeleBot
from telebot.types import CallbackQuery, Message, LabeledPrice
import time

from .texts import (
    CREDIT_TITLE, CREDIT_HEADER, PAY_RIAL_TITLE, PAY_RIAL_PLANS_HEADER, INSTANT_PAY_INSTRUCT, WAITING_CONFIRM
)
from .keyboards import credit_menu_kb, stars_packages_kb, payrial_plans_kb, instant_cancel_kb, augment_with_rial
from config import BOT_OWNER_ID as ADMIN_REVIEW_CHAT_ID, CARD_NUMBER
from .settings import PAYMENT_PLANS
from .settings import RECEIPT_WAIT_TTL

# Optional payment config from config.py
try:
    from config import TELEGRAM_PAYMENT_PROVIDER_TOKEN
except Exception:
    TELEGRAM_PAYMENT_PROVIDER_TOKEN = None

try:
    from config import TELEGRAM_PAYMENT_CURRENCY
except Exception:
    TELEGRAM_PAYMENT_CURRENCY = "USD"

# Try importing home menu/texts, fallback if not available
try:
    from ..home.keyboards import home_menu_kb  # type: ignore
except Exception:
    home_menu_kb = None

try:
    from ..home.texts import HOME_TITLE  # type: ignore
except Exception:
    HOME_TITLE = "منوی اصلی"

# Temporary receipt-wait state
_RECEIPT_WAIT: dict[int, float] = {}
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

def open_credit(bot: TeleBot, cq):
    """Open credit menu — build keyboard according to user's language (from DB if possible)."""
    try:
        # read user language from DB if available
        try:
            import db
            user = db.get_or_create_user(cq.from_user)
            user_lang = db.get_user_lang(user["user_id"], "fa")
        except Exception:
            # fallback: maybe we only have chat id
            try:
                import db
                user_lang = db.get_user_lang(cq.message.chat.id, "fa")
            except Exception:
                user_lang = "fa"

        text = f"🛒 <b>{CREDIT_TITLE}</b>\n\n{CREDIT_HEADER}"
        bot.edit_message_text(
            text, cq.message.chat.id, cq.message.message_id,
            parse_mode="HTML", reply_markup=credit_menu_kb(user_lang)
        )
    except Exception:
        # last-resort send
        bot.send_message(
            cq.message.chat.id, text,
            parse_mode="HTML", reply_markup=credit_menu_kb(user_lang if 'user_lang' in locals() else "fa")
        )

def add_rial_button_to_credit_menu(markup, lang: str = "fa"):
    """
    Add Rial button to an existing markup according to lang.
    Default lang='fa' keeps previous behavior.
    """
    return augment_with_rial(markup, lang)

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
    Register handlers for credit (Telegram Stars and Rial flows).
    """

    @bot.callback_query_handler(func=lambda c: c.data == "credit:menu")
    def on_credit_menu(c):
        bot.answer_callback_query(c.id)
        open_credit(bot, c)

    @bot.callback_query_handler(func=lambda c: c.data == "credit:stars")
    def on_stars_menu(c):
        bot.answer_callback_query(c.id)
        text = "⭐️ <b>خرید به صورت آنـی با Telegram Stars</b>\n\nیکی از بسته‌های زیر را انتخاب کنید:"
        try:
            bot.edit_message_text(text, c.message.chat.id, c.message.message_id,
                                  parse_mode="HTML", reply_markup=stars_packages_kb())
        except Exception:
            bot.send_message(c.message.chat.id, text, parse_mode="HTML",
                             reply_markup=stars_packages_kb())

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("credit:buy:"))
    def on_buy_stars(c: CallbackQuery):
        bot.answer_callback_query(c.id)
        # parse callback_data robustly
        parts = c.data.split(":")
        if len(parts) < 4:
            bot.answer_callback_query(c.id, "داده نامعتبر")
            return
        try:
            stars = int(parts[2])
            credits = int(parts[3])
        except Exception:
            bot.answer_callback_query(c.id, "داده نامعتبر")
            return

        import json
        invoice_payload = json.dumps({
            "user_id": c.from_user.id,
            "credits": credits
        })

        # First attempt: send as Telegram Stars invoice (provider_token usually empty, currency XTR)
        prices = [LabeledPrice(label=f"{credits} کردیت", amount=stars)]
        try:
            bot.send_invoice(
                chat_id=c.from_user.id,
                title=f"خرید {credits} کردیت – Vexa",
                description=f"شارژ موجودی با Telegram Stars",
                invoice_payload=invoice_payload,
                provider_token="",  # empty for Stars (depends on BotFather/provider setup)
                currency="XTR",
                prices=prices
            )
            bot.answer_callback_query(c.id, "فاکتور ارسال شد")
            return
        except Exception as e:
            # Stars invoice failed; try fallback to configured payment provider if available
            print("stars invoice failed:", e)

        # Fallback: use configured provider token (if available)
        if not TELEGRAM_PAYMENT_PROVIDER_TOKEN:
            bot.answer_callback_query(c.id, "پرداخت غیرفعال است: توکن پرداخت تنظیم نشده")
            return

        # Convert amount to smallest unit required by provider (e.g., cents)
        # NOTE: adjust multiplier if your currency uses different smallest unit
        amount_smallest_unit = int(stars * 100)
        prices_fb = [LabeledPrice(label=f"{credits} کردیت", amount=amount_smallest_unit)]
        try:
            bot.send_invoice(
                chat_id=c.from_user.id,
                title=f"خرید {credits} کردیت",
                description=f"خرید {credits} کردیت با {stars} ستاره تلگرام",
                invoice_payload=invoice_payload,
                provider_token=TELEGRAM_PAYMENT_PROVIDER_TOKEN,
                currency=TELEGRAM_PAYMENT_CURRENCY,
                prices=prices_fb
            )
            bot.answer_callback_query(c.id, "لطفاً پرداخت را تکمیل کنید")
        except Exception as e2:
            print("error sending fallback invoice:", e2)
            try:
                bot.answer_callback_query(c.id, "خطا در ایجاد صورتحساب")
            except Exception:
                pass

    @bot.pre_checkout_query_handler(func=lambda query: True)
    def pre_checkout_handler(pre_checkout_query):
        bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

    @bot.message_handler(content_types=['successful_payment'])
    def on_successful_payment(message):
        try:
            import json, db
            user_id = message.from_user.id
            credits = json.loads(message.successful_payment.invoice_payload)["credits"]
            amount_paid = message.successful_payment.total_amount

            user = db.get_or_create_user(message.from_user)
            db.add_credits(user_id, credits)

            # Log purchase: amount_paid is provider-specific (in smallest unit)
            db.log_purchase(user_id, amount_paid, credits, message.successful_payment.telegram_payment_charge_id)

            bot.send_message(
                message.chat.id,
                f"✅ پرداخت موفق!\n\n💎 {credits} کردیت به حساب شما اضافه شد.\n⭐️ مبلغ: {amount_paid}",
                parse_mode="HTML"
            )
        except Exception as e:
            print("error processing successful_payment:", e)
            try:
                bot.send_message(message.chat.id, "خطا در پردازش پرداخت")
            except Exception:
                pass

    @bot.callback_query_handler(func=lambda c: c.data == "credit:payrial")
    def on_payrial(c: CallbackQuery):
        bot.answer_callback_query(c.id)
        plans_text = "\n".join([f\"{p['title']}\" for p in PAYMENT_PLANS])
        text = (
            f\"🧾 <b>{PAY_RIAL_TITLE}</b>\\n\\n\"
            f\"<pre>{plans_text}</pre>\"
        )
        try:
            bot.edit_message_text(text, c.message.chat.id, c.message.message_id,
                                  parse_mode="HTML", reply_markup=payrial_plans_kb())
        except Exception:
            bot.send_message(c.message.chat.id, text, parse_mode="HTML",
                             reply_markup=payrial_plans_kb())

    @bot.callback_query_handler(func=lambda c: c.data == "credit:payrial:instant")
    def on_instant(c: CallbackQuery):
        bot.answer_callback_query(c.id)
        _set_wait(c.from_user.id, c.message.message_id)
        text = INSTANT_PAY_INSTRUCT.format(card=CARD_NUMBER)
        try:
            bot.edit_message_text(text, c.message.chat.id, c.message.message_id,
                                  parse_mode="HTML", reply_markup=instant_cancel_kb())
        except Exception:
            bot.send_message(c.message.chat.id, text, parse_mode="HTML",
                             reply_markup=instant_cancel_kb())

    @bot.callback_query_handler(func=lambda c: c.data in ("credit:menu", "credit:cancel"))
    def on_back(c: CallbackQuery):
        bot.answer_callback_query(c.id)
        _clear_wait(c.from_user.id)
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

    @bot.message_handler(content_types=['photo'])
    def on_receipt(msg: Message):
        if not _is_waiting(msg.from_user.id):
            return
        payment_msg_id = _get_message_id(msg.from_user.id)
        _clear_wait(msg.from_user.id)

        caption = (
            "🧾 رسید پرداخت جدید\n"
            f"User ID: <code>{msg.from_user.id}</code>\n"
            f"Username: @{msg.from_user.username or '-'}\n"
            f"Name: {msg.from_user.first_name or ''} {msg.from_user.last_name or ''}"
        )
        try:
            file_id = msg.photo[-1].file_id
            bot.send_photo(ADMIN_REVIEW_CHAT_ID, file_id, caption=caption, parse_mode="HTML")
        except Exception:
            pass

        from modules.home.texts import MAIN
        from modules.home.keyboards import main_menu
        import db
        user = db.get_or_create_user(msg.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")

        if payment_msg_id:
            try:
                bot.delete_message(msg.chat.id, payment_msg_id)
            except Exception:
                pass

        bot.send_message(msg.chat.id, "✅ رسید دریافت شد\n⏳ لطفاً منتظر تایید باش", parse_mode="HTML")
        bot.send_message(msg.chat.id, MAIN(lang), parse_mode="HTML", reply_markup=main_menu(lang))
