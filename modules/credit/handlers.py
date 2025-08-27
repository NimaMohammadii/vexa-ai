# modules/credit/handlers.py
import db
from telebot import types
from utils import edit_or_send
from .texts import INTRO, INVOICE_TITLE, INVOICE_DESC, PAY_SUCCESS
from .keyboards import keyboard as credit_keyboard, STAR_TO_CREDIT

def register(bot):
    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("credit:buy:"))
    def cb_buy(cq):
        user = db.get_or_create_user(cq.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")

        try:
            stars = int(cq.data.split(":")[2])
        except Exception:
            bot.answer_callback_query(cq.id, "Invalid pack."); return

        if stars not in STAR_TO_CREDIT:
            bot.answer_callback_query(cq.id, "Invalid pack."); return

        prices = [types.LabeledPrice(label=f"{stars} Stars", amount=stars)]
        payload = f"stars:{stars}:{STAR_TO_CREDIT[stars]}:{user['user_id']}"

        bot.send_invoice(
            chat_id=cq.message.chat.id,
            title=INVOICE_TITLE(lang),
            description=INVOICE_DESC(lang),
            invoice_payload=payload,
            provider_token="",     # Stars
            currency="XTR",
            prices=prices,
            start_parameter=f"vexa_{stars}"
        )
        bot.answer_callback_query(cq.id)

    @bot.pre_checkout_query_handler(func=lambda q: True)
    def on_pre_checkout(pre_q):
        bot.answer_pre_checkout_query(pre_q.id, ok=True)

    @bot.message_handler(content_types=['successful_payment'])
    def on_success_pay(msg):
        sp = msg.successful_payment
        if not sp or sp.currency != "XTR":
            return
        payload = (sp.invoice_payload or "")
        try:
            _, stars_s, credits_s, uid_s = payload.split(":")
            stars = int(stars_s); credits = int(credits_s); uid = int(uid_s)
        except Exception:
            return

        db.add_credits(uid, credits)
        balance = db.get_user(uid)["credits"]
        lang = db.get_user_lang(uid, "fa")

        try:
            bot.send_message(msg.chat.id, PAY_SUCCESS(lang, stars, credits, balance))
        except Exception:
            pass

def open_credit(bot, cq):
    user = db.get_or_create_user(cq.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")
    edit_or_send(bot, cq.message.chat.id, cq.message.message_id, INTRO(lang), credit_keyboard(lang))