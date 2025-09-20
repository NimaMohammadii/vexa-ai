from __future__ import annotations
from telebot import TeleBot
from telebot.types import CallbackQuery, Message, LabeledPrice
import telebot.types as ttypes
import time

from .texts import (
    PAY_RIAL_TITLE, PAY_RIAL_PLANS_HEADER, INSTANT_PAY_INSTRUCT, WAITING_CONFIRM
)
from modules.i18n import t
from .keyboards import credit_menu_kb, stars_packages_kb, payrial_plans_kb, instant_cancel_kb, augment_with_rial, admin_approve_kb
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
# user_id -> plan_index (برای اینکه بدونیم کدوم پلن انتخاب شده)
_USER_SELECTED_PLANS: dict[int, int] = {}

def _set_wait(user_id: int, message_id: int = None, plan_index: int = None):
    _RECEIPT_WAIT[user_id] = time.time() + RECEIPT_WAIT_TTL
    if message_id:
        _USER_MESSAGE_IDS[user_id] = message_id
    if plan_index is not None:
        _USER_SELECTED_PLANS[user_id] = plan_index

def _clear_wait(user_id: int):
    _RECEIPT_WAIT.pop(user_id, None)
    _USER_MESSAGE_IDS.pop(user_id, None)
    _USER_SELECTED_PLANS.pop(user_id, None)

def _get_selected_plan(user_id: int) -> int:
    return _USER_SELECTED_PLANS.get(user_id, 0)

def _get_message_id(user_id: int) -> int:
    return _USER_MESSAGE_IDS.get(user_id)

def _is_waiting(user_id: int) -> bool:
    exp = _RECEIPT_WAIT.get(user_id)
    return bool(exp and exp > time.time())

# === API اصلی برای منوی کردیت ===
def open_credit(bot: TeleBot, cq):
    """باز کردن منوی اصلی خرید کردیت"""
    import db

    # پاک کردن منوی TTS قبلی اگر وجود داشته باشه
    user_state = db.get_state(cq.from_user.id) or ""
    if user_state.startswith("tts:wait_text:"):
        try:
            # استخراج message_id منوی TTS از state
            parts = user_state.split(":")
            if len(parts) >= 3 and parts[2].isdigit():
                tts_menu_id = int(parts[2])
                bot.delete_message(cq.message.chat.id, tts_menu_id)
                print(f"DEBUG: Deleted TTS menu {tts_menu_id} for user {cq.from_user.id}")
        except Exception as e:
            print(f"DEBUG: Failed to delete TTS menu: {e}")
        # پاک کردن state
        db.clear_state(cq.from_user.id)
    
    user = db.get_or_create_user(cq.from_user)
    lang = db.get_user_lang(user["user_id"], "fa")
    text = f"🛒 <b>{t('credit_title', lang)}</b>\n\n{t('credit_header', lang)}"
    
    # ادیت کردن همین پیام
    try:
        bot.edit_message_text(
            text, cq.message.chat.id, cq.message.message_id,
            parse_mode="HTML", reply_markup=credit_menu_kb(lang)
        )
    except Exception:
        # اگر ادیت نشد، پیام جدید بفرست
        bot.send_message(
            cq.message.chat.id, text,
            parse_mode="HTML", reply_markup=credit_menu_kb(lang)
        )

# === API عمومی برای ادغام با منوی Credit موجود تو ===
def add_rial_button_to_credit_menu(markup, lang: str = "fa"):
    """در کد فعلی منوی Credit، قبل از ارسال reply_markup این تابع را صدا بزن:
        markup = add_rial_button_to_credit_menu(markup)
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
        import db

        user = db.get_or_create_user(c.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")

        bot.answer_callback_query(c.id)
        text = t("credit_stars_menu", lang)
        try:
            bot.edit_message_text(text, c.message.chat.id, c.message.message_id,
                                  parse_mode="HTML", reply_markup=stars_packages_kb(lang))
        except Exception:
            bot.send_message(c.message.chat.id, text, parse_mode="HTML",
                             reply_markup=stars_packages_kb(lang))

    # خرید بسته Stars
    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("credit:buy:"))
    def on_buy_stars(c: CallbackQuery):
        import db

        user = db.get_or_create_user(c.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")

        bot.answer_callback_query(c.id)
        try:
            stars = 0
            credits = 0
            parts = c.data.split(":")
            # expected: credit:buy:<stars>:<credits>
            if len(parts) < 4:
                bot.answer_callback_query(c.id, t("credit_invalid_data", lang), show_alert=True)
                return

            stars = int(parts[2])
            credits = int(parts[3])

            # ساخت payload برای تشخیص سفارش در پاسخ شیپینگ/پرداخت
            import json
            invoice_payload = json.dumps({
                "user_id": c.from_user.id,
                "credits": credits
            })

            # برای Telegram Stars معمولا provider_token خالی و currency = "XTR"
            prices = [LabeledPrice(label=t("credit_invoice_label", lang).format(credits=credits), amount=stars)]

            bot.send_invoice(
                chat_id=c.from_user.id,
                title=t("credit_invoice_title", lang),
                description=t("credit_invoice_desc", lang),
                invoice_payload=invoice_payload,
                provider_token="",                 # برای Stars خالی می‌ماند
                currency="XTR",
                prices=prices
            )

            bot.answer_callback_query(c.id, t("credit_invoice_sent", lang))
        except Exception as e:
            # اگر ارسال با Stars ناموفق شد، تلاش به ارسال invoice با provider معمولی (fallback)
            try:
                import json
                payload = json.dumps({"user_id": c.from_user.id, "credits": credits})

                # مقدار price باید به کوچک‌ترین واحد پولی ارسال شود (مثلاً سنت)
                amount_smallest_unit = int(stars * 100)
                prices = [LabeledPrice(label=t("credit_invoice_label", lang).format(credits=credits), amount=amount_smallest_unit)]

                if not TELEGRAM_PAYMENT_PROVIDER_TOKEN:
                    bot.answer_callback_query(c.id, t("credit_payment_disabled", lang), show_alert=True)
                    return

                bot.send_invoice(
                    chat_id=c.from_user.id,
                    title=t("credit_invoice_title", lang),
                    description=t("credit_invoice_desc", lang),
                    invoice_payload=payload,
                    provider_token=TELEGRAM_PAYMENT_PROVIDER_TOKEN,
                    currency=TELEGRAM_PAYMENT_CURRENCY,
                    prices=prices
                )
                bot.answer_callback_query(c.id, t("credit_invoice_complete", lang))
            except Exception as e2:
                print("error sending invoice:", e2)
                try:
                    bot.answer_callback_query(c.id, t("credit_invoice_error", lang), show_alert=True)
                except Exception:
                    pass
    
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
            lang = db.get_user_lang(user_id, "fa")
            credits = json.loads(message.successful_payment.invoice_payload)["credits"]
            stars = message.successful_payment.total_amount

            # اضافه کردن کردیت به حساب کاربر
            db.get_or_create_user(message.from_user)
            db.add_credits(user_id, credits)

            # ذخیره تراکنش
            db.log_purchase(user_id, stars, credits, message.successful_payment.telegram_payment_charge_id)

            updated_user = db.get_user(user_id)
            balance = (updated_user or {}).get("credits", credits)

            bot.send_message(
                message.chat.id,
                t("credit_pay_success", lang).format(stars=stars, credits=credits, balance=balance),
                parse_mode="HTML"
            )

        except Exception as e:
            lang = locals().get("lang")
            if not lang:
                try:
                    import db
                    lang = db.get_user_lang(message.from_user.id, "fa")
                except Exception:
                    lang = "fa"
            bot.send_message(message.chat.id, t("credit_payment_error", lang))

    # کاربر روی «پرداخت ریالی» کلیک می‌کند → نمایش قیمت‌ها
    @bot.callback_query_handler(func=lambda c: c.data == "credit:payrial")
    def on_payrial(c: CallbackQuery):
        import db

        user = db.get_or_create_user(c.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")

        if lang != "fa":
            bot.answer_callback_query(c.id, t("credit_unavailable", lang), show_alert=True)
            return

        bot.answer_callback_query(c.id)

        text = f"🧾 <b>{PAY_RIAL_TITLE}</b>\n\nیکی از بسته‌های زیر را انتخاب کنید:"

        try:
            bot.edit_message_text(text, c.message.chat.id, c.message.message_id,
                                  parse_mode="HTML", reply_markup=payrial_plans_kb(lang))
        except Exception:
            bot.send_message(c.message.chat.id, text, parse_mode="HTML",
                             reply_markup=payrial_plans_kb(lang))

    # انتخاب یکی از بسته‌های قیمت → ورود به مرحله پرداخت
    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("credit:select:"))
    def on_select_plan(c: CallbackQuery):
        import db

        user = db.get_or_create_user(c.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")

        bot.answer_callback_query(c.id)
        try:
            plan_index = int(c.data.split(":")[2])
            if plan_index < 0 or plan_index >= len(PAYMENT_PLANS):
                bot.answer_callback_query(c.id, t("credit_invalid_plan", lang), show_alert=True)
                return

            plan = PAYMENT_PLANS[plan_index]
            _set_wait(c.from_user.id, c.message.message_id, plan_index)
            
            text = (
                f"💱 <b>پرداخت فـوری (کارت‌به‌کارت)</b>\n"
                f"<b>شماره کارت:</b><code>{CARD_NUMBER}</code>\n\n"
                f"• دقیقاً مبلغ <b>{plan['amount_toman']:,} تومان</b> پرداخت کنید\n"
                f"• سپس <b>تصویر رسید</b> را همین‌جا ارسال کنید\n\n"
                f"✅ <b>پس از تایید، <b>{plan['credits']:,} کردیت</b> به حساب شما اضافه خواهد شد (کمتر از ۵ دقیقه)</b>"
            )
            
            try:
                bot.edit_message_text(text, c.message.chat.id, c.message.message_id,
                                      parse_mode="HTML", reply_markup=instant_cancel_kb(lang))
            except Exception:
                bot.send_message(c.message.chat.id, text, parse_mode="HTML",
                                 reply_markup=instant_cancel_kb(lang))

        except Exception as e:
            bot.answer_callback_query(c.id, t("credit_plan_error", lang), show_alert=True)

    # ورود به حالت «پرداخت فوری (کارت‌به‌کارت)» → انتظار دریافت تصویر رسید
    @bot.callback_query_handler(func=lambda c: c.data == "credit:payrial:instant")
    def on_instant(c: CallbackQuery):
        import db

        user = db.get_or_create_user(c.from_user)
        lang = db.get_user_lang(user["user_id"], "fa")

        bot.answer_callback_query(c.id)
        _set_wait(c.from_user.id, c.message.message_id)  # ذخیره message_id
        text = INSTANT_PAY_INSTRUCT.format(card=CARD_NUMBER)
        try:
            bot.edit_message_text(text, c.message.chat.id, c.message.message_id,
                                  parse_mode="HTML", reply_markup=instant_cancel_kb(lang))
        except Exception:
            bot.send_message(c.message.chat.id, text, parse_mode="HTML",
                             reply_markup=instant_cancel_kb(lang))

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

        # گرفتن اطلاعات قبل از پاک کردن
        payment_msg_id = _get_message_id(msg.from_user.id)
        plan_index = _get_selected_plan(msg.from_user.id)
        plan = PAYMENT_PLANS[plan_index] if plan_index < len(PAYMENT_PLANS) else None
        _clear_wait(msg.from_user.id)

        # فوروارد تصویر رسید برای ادمین با اطلاعات کامل
        if plan:
            caption = (
                f"🧾 <b>رسید پرداخت جدید</b>\n"
                
                f"• User ID: <code>{msg.from_user.id}</code>\n"
                f"• Username: @{msg.from_user.username or '-'}\n"
                f"• Name: {msg.from_user.first_name or ''} {msg.from_user.last_name or ''}\n\n"
                
                f"• مبلغ: {plan['amount_toman']:,} تومان\n"
                f"• کردیت: {plan['credits']:,}"
            )
        else:
            caption = (
                f"🧾 <b>رسید پرداخت جدید</b>\n\n"
                f"👤 <b>اطلاعات کاربر:</b>\n"
                f"• User ID: <code>{msg.from_user.id}</code>\n"
                f"• Username: @{msg.from_user.username or '-'}\n"
                f"• Name: {msg.from_user.first_name or ''} {msg.from_user.last_name or ''}"
            )
        
        try:
            file_id = msg.photo[-1].file_id  # بزرگترین رزولوشن
            bot.send_photo(ADMIN_REVIEW_CHAT_ID, file_id, caption=caption, 
                          parse_mode="HTML", reply_markup=admin_approve_kb(msg.from_user.id, plan_index))
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
        bot.send_message(msg.chat.id, "✅ رسید دریافت شد\n⏳ <b>لطفاً منتظر تایید باش</b>", parse_mode="HTML")
        
        # 3. ارسال منوی اصلی (جداگانه)
        bot.send_message(msg.chat.id, MAIN(lang), parse_mode="HTML", reply_markup=main_menu(lang))

    # هندلر تایید/رد ادمین
    @bot.callback_query_handler(func=lambda c: c.data and c.data.startswith("credit_admin:"))
    def on_admin_action(c: CallbackQuery):
        print(f"DEBUG: Credit admin action received: {c.data}")  # برای دیباگ
        try:
            parts = c.data.split(":")
            action = parts[1]  # approve یا reject
            user_id = int(parts[2])
            plan_index = int(parts[3])
            
            if plan_index < 0 or plan_index >= len(PAYMENT_PLANS):
                bot.answer_callback_query(c.id, "بسته نامعتبر")
                return
                
            plan = PAYMENT_PLANS[plan_index]
            
            if action == "approve":
                # اضافه کردن کردیت به کاربر
                import db
                db.add_credits(user_id, plan['credits'])
                
                # ثبت تراکنش در دیتابیس
                try:
                    db.log_purchase(user_id, plan['amount_toman'], plan['credits'], f"manual_approval_{int(time.time())}")
                except:
                    pass
                
                # پیام به کاربر
                try:
                    bot.send_message(
                        user_id,
                        f"✅ <b>پرداخت تأیید شد!</b>\n\n"
                        f"💎 <b>{plan['credits']:,} کردیت</b> به حساب شما اضافه شد.\n"
                        f"💰 مبلغ: {plan['amount_toman']:,} تومان",
                        parse_mode="HTML"
                    )
                except:
                    pass
                
                # پیام به ادمین
                bot.answer_callback_query(c.id, f"✅ تأیید شد - {plan['credits']:,} کردیت اضافه شد")
                
                # ویرایش پیام ادمین
                try:
                    new_caption = (c.message.caption or "") + f"\n\n✅ <b>تأیید شده توسط ادمین</b>"
                    bot.edit_message_caption(
                        chat_id=c.message.chat.id,
                        message_id=c.message.message_id,
                        caption=new_caption,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"DEBUG: Error editing caption: {e}")
                    
            elif action == "reject":
                # پیام رد به کاربر
                try:
                    bot.send_message(
                        user_id,
                        f"❌ <b>پرداخت رد شد</b>\n\n"
                        f"رسید ارسالی تأیید نشد. در صورت اطمینان از صحت پرداخت، مجدداً رسید ارسال کنید یا با پشتیبانی تماس بگیرید.",
                        parse_mode="HTML"
                    )
                except:
                    pass
                
                # پیام به ادمین
                bot.answer_callback_query(c.id, "❌ پرداخت رد شد")
                
                # ویرایش پیام ادمین
                try:
                    new_caption = (c.message.caption or "") + f"\n\n❌ <b>رد شده توسط ادمین</b>"
                    bot.edit_message_caption(
                        chat_id=c.message.chat.id,
                        message_id=c.message.message_id,
                        caption=new_caption,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"DEBUG: Error editing caption: {e}")
                    
        except Exception as e:
            print(f"DEBUG: Error in admin action: {e}")
            bot.answer_callback_query(c.id, "خطا در پردازش")
