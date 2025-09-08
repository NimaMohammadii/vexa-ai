from __future__ import annotations
from telebot import TeleBot
from telebot.types import CallbackQuery, Message, LabeledPrice
import telebot.types as ttypes
import time

from .texts import (
    CREDIT_TITLE, CREDIT_HEADER, PAY_RIAL_TITLE, PAY_RIAL_PLANS_HEADER,
    INSTANT_PAY_INSTRUCT, WAITING_CONFIRM
)
from .keyboards import credit_menu_kb, stars_packages_kb, payrial_plans_kb, instant_cancel_kb
from config import BOT_OWNER_ID as ADMIN_REVIEW_CHAT_ID, CARD_NUMBER
from .settings import PAYMENT_PLANS, RECEIPT_WAIT_TTL

# تلاش برای خواندن تنظیمات پرداخت تلگرام از config
try:
    from config import TELEGRAM_PAYMENT_PROVIDER_TOKEN
except Exception:
    TELEGRAM_PAYMENT_PROVIDER_TOKEN = None

try:
    from config import TELEGRAM_PAYMENT_CURRENCY
except Exception:
    TELEGRAM_PAYMENT_CURRENCY = "USD"

# تلاش برای استفاده از منوی اصلی پروژه
try:
    from ..home.keyboards import home_menu_kb  # type: ignore
except Exception:
    home_menu_kb = None

try:
    from ..home.texts import HOME_TITLE  # type: ignore
except Exception:
    HOME_TITLE = "منوی اصلی"

# --- حالت موقت انتظار رسید ---
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

# === منوی اصلی کردیت ===
def open_credit(bot: TeleBot, cq):
    """باز کردن منوی اصلی خرید کردیت"""
    import db
    user = db.get_or_create_user(cq.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")
    text = f"🛒 <b>{CREDIT_TITLE(lang)}</b>\n\n{CREDIT_HEADER(lang)}"
    try:
        bot.edit_message_text(
            text, cq.message.chat.id, cq.message.message_id,
            parse_mode="HTML", reply_markup=credit_menu_kb(lang)
        )
    except Exception:
        bot.send_message(
            cq.message.chat.id, text,
            parse_mode="HTML", reply_markup=credit_menu_kb(lang)
        )

def register(bot: TeleBot):
    """رجیستر کردن هندلرهای مربوط به کردیت"""
    
    @bot.callback_query_handler(func=lambda c: c.data == "credit:menu")
    def on_credit_menu(c):
        bot.answer_callback_query(c.id)
        open_credit(bot, c)

    @bot.callback_query_handler(func=lambda c: c.data == "credit:stars")
    def on_stars_menu(c):
        bot.answer_callback_query(c.id)
        text = "⭐️ <b>خرید با Telegram Stars</b>\n\nیکی از بسته‌ها را انتخاب کنید:"
        import db
        user = db.get_or_create_user(c.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        bot.send_message(c.message.chat.id, text,
                         parse_mode="HTML", reply_markup=stars_packages_kb(lang))

    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("credit:buy:"))
    def on_buy_stars(c: CallbackQuery):
        bot.answer_callback_query(c.id)
        parts = c.data.split(":")
        if len(parts) < 4:
            return
        stars = int(parts[2])
        credits = int(parts[3])
        import json
        invoice_payload = json.dumps({"user_id": c.from_user.id, "credits": credits})
        prices = [LabeledPrice(label=f"{credits} کردیت", amount=stars)]
        bot.send_invoice(
            chat_id=c.from_user.id,
            title=f"خرید {credits} کردیت – Vexa",
            description="شارژ موجودی با Telegram Stars",
            invoice_payload=invoice_payload,
            provider_token="",
            currency="XTR",
            prices=prices
        )

    @bot.callback_query_handler(func=lambda c: c.data == "credit:payrial")
    def on_payrial(c: CallbackQuery):
        import db
        user = db.get_or_create_user(c.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        if lang != "fa":
            open_credit(bot, c)
            return
        plans_text = "\n".join([f"{p['title']}" for p in PAYMENT_PLANS])
        text = f"🧾 <b>{PAY_RIAL_TITLE(lang)}</b>\n\n<pre>{plans_text}</pre>"
        bot.send_message(c.message.chat.id, text,
                         parse_mode="HTML", reply_markup=payrial_plans_kb(lang))

    @bot.callback_query_handler(func=lambda c: c.data == "credit:payrial:instant")
    def on_instant(c: CallbackQuery):
        import db
        user = db.get_or_create_user(c.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        _set_wait(c.from_user.id, c.message.message_id)
        text = INSTANT_PAY_INSTRUCT(lang, CARD_NUMBER)
        bot.send_message(c.message.chat.id, text,
                         parse_mode="HTML", reply_markup=instant_cancel_kb(lang))

    @bot.callback_query_handler(func=lambda c: c.data in ("credit:menu", "credit:cancel"))
    def on_back(c: CallbackQuery):
        bot.answer_callback_query(c.id)
        _clear_wait(c.from_user.id)
        from modules.home.texts import MAIN
        from modules.home.keyboards import main_menu
        import db
        user = db.get_or_create_user(c.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        bot.send_message(c.message.chat.id, MAIN(lang),
                         parse_mode="HTML", reply_markup=main_menu(lang))

    @bot.message_handler(content_types=['photo'])
    def on_receipt(msg: Message):
        if not _is_waiting(msg.from_user.id):
            return
        payment_msg_id = _get_message_id(msg.from_user.id)
        _clear_wait(msg.from_user.id)
        caption = (
            "🧾 رسید پرداخت\n"
            f"User ID: <code>{msg.from_user.id}</code>\n"
            f"Username: @{msg.from_user.username or '-'}"
        )
        file_id = msg.photo[-1].file_id
        bot.send_photo(ADMIN_REVIEW_CHAT_ID, file_id, caption=caption, parse_mode="HTML")
        import db
        user = db.get_or_create_user(msg.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")
        if payment_msg_id:
            try:
                bot.delete_message(msg.chat.id, payment_msg_id)
            except Exception:
                pass
        bot.send_message(msg.chat.id, WAITING_CONFIRM(lang), parse_mode="HTML")
