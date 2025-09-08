from telebot import types
from ..i18n import t
from .keyboards import credit_menu_kb, stars_packages_kb, payrial_plans_kb, instant_cancel_kb
from .settings import STAR_PACKAGES

# NOTE: ensure `bot` is the TeleBot instance available in this module (import or inject it).
# Also set PROVIDER_TOKEN for Telegram invoices (if you plan to use telegram payment):
PROVIDER_TOKEN = ""  # <-- قرار بدین یا از تنظیمات بارگذاری کنید

def register_credit_handlers(bot):
    # register callback query handler for credit menu
    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("credit:"))
    def _credit_cb(call: types.CallbackQuery):
        data = call.data.split(":")
        action = data[1] if len(data) > 1 else ""
        lang = (call.from_user.language_code or "fa")[:2]

        if action == "menu":
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=t("pay_rial_title", lang),
                reply_markup=credit_menu_kb(lang)
            )
        elif action == "stars":
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=t("credit_invoice_desc", lang),
                reply_markup=stars_packages_kb(lang)
            )
        elif action == "buy" and len(data) >= 4:
            # credit:buy:{stars}:{credits}
            stars = int(data[2])
            credits = int(data[3])
            # create invoice for stars (example: using Telegram invoices)
            # Provider token must be configured. If not provided, send a confirmation message instead.
            title = f"{stars} ⭐"
            description = t("credit_invoice_desc", lang)
            payload = f"stars:{stars}:user:{call.from_user.id}"
            currency = "USD"  # adapt as needed or map to virtual currency
            prices = [types.LabeledPrice(label=title, amount=stars * 100)]  # example amount

            if PROVIDER_TOKEN:
                bot.send_invoice(
                    chat_id=call.from_user.id,
                    title=title,
                    description=description,
                    invoice_payload=payload,
                    provider_token=PROVIDER_TOKEN,
                    currency=currency,
                    prices=prices,
                    reply_markup=instant_cancel_kb(lang)
                )
            else:
                bot.send_message(
                    call.from_user.id,
                    f"{t('credit_invoice_title', lang)}: {title}\n(پرداخت شبیه‌سازی شده — PROVIDER_TOKEN تنظیم نشده)",
                    reply_markup=instant_cancel_kb(lang)
                )
        elif action == "payrial":
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=t("pay_rial_plans_header", lang),
                reply_markup=payrial_plans_kb(lang)
            )
        elif action == "payrial" and len(data) >= 3:
            # handlers for specific rial plans can be added here
            bot.answer_callback_query(call.id, "پرداخت تومانی در دست ساخت است.")
        elif action == "cancel":
            bot.send_message(call.from_user.id, t("cancel", lang))
        else:
            bot.answer_callback_query(call.id, "Unhandled credit action.")
