from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiTelegramException

from modules.i18n import t

def edit_or_send(bot, chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    try:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except ApiTelegramException as exc:
        # اگر پیام تغییری نکرده باشد، تلگرام خطای «message is not modified» می‌دهد.
        # در این حالت نیازی به ارسال پیام جدید نیست.
        if "message is not modified" in str(exc).lower():
            return
        bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

def smart_edit_or_send(bot, obj, text, reply_markup=None, parse_mode="HTML"):
    """
    فقط در صورتی که محتوای جدید متفاوت از محتوای فعلی باشد، پیام را ویرایش می‌کند
    obj می‌تواند callback_query، message، یا chat_id و message_id باشد
    """
    # تشخیص نوع ورودی
    if hasattr(obj, 'message'):  # callback_query
        chat_id = obj.message.chat.id
        message_id = obj.message.message_id
        current_text = getattr(obj.message, 'text', '') or getattr(obj.message, 'caption', '') or ''
        # بررسی keyboard فعلی
        current_markup = getattr(obj.message, 'reply_markup', None)
    elif hasattr(obj, 'chat'):  # message
        chat_id = obj.chat.id
        message_id = obj.message_id
        current_text = getattr(obj, 'text', '') or getattr(obj, 'caption', '') or ''
        current_markup = getattr(obj, 'reply_markup', None)
    else:  # فرض می‌کنیم اولی chat_id دومی message_id است (سازگاری عقب)
        chat_id = obj
        message_id = reply_markup if isinstance(reply_markup, int) else None
        current_text = ''
        current_markup = None
        # در این حالت پارامترها جابجا شده‌اند
        if isinstance(reply_markup, int):
            message_id = reply_markup
            reply_markup = parse_mode
            parse_mode = text if isinstance(text, str) and text in ["HTML", "Markdown"] else "HTML"
    
    # پاک کردن HTML tags برای مقایسه بهتر
    import re
    clean_current = re.sub(r'<[^>]+>', '', current_text.strip())
    clean_new = re.sub(r'<[^>]+>', '', text.strip())
    
    # اگر متن جدید همان متن فعلی است و keyboard هم یکسان است، هیچ کاری نکن
    if clean_current == clean_new:
        # بررسی اگر keyboard هم یکسان است
        if str(current_markup) == str(reply_markup):
            return
    
    try:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        # اگر ویرایش نشد (مثلاً محتوا یکسان بود)، هیچ کاری نکن
        pass

# --- عددخوان (فارسی/عربی/کاما/فاصله) ---
_DIGIT_MAP = str.maketrans({
    "۰":"0","۱":"1","۲":"2","۳":"3","۴":"4","۵":"5","۶":"6","۷":"7","۸":"8","۹":"9",
    "٠":"0","١":"1","٢":"2","٣":"3","٤":"4","٥":"5","٦":"6","٧":"7","٨":"8","٩":"9",
    "٬":"", ",":"", " ":""
})
def parse_int(text: str) -> int:
    t = (text or "").strip().translate(_DIGIT_MAP)
    if t.startswith("+"): t = t[1:]
    if t.startswith("-"): return -int(t[1:] or "0")
    return int(t or "0")

def check_force_sub(bot, user_id, settings, lang: str | None = None):
    """
    returns: (ok, text, markup)
    """
    mode = (settings.get("FORCE_SUB_MODE") or "none").strip()
    tg_channel = (settings.get("TG_CHANNEL") or "").strip()
    ig_url = (settings.get("IG_URL") or "").strip()

    lang = (lang or "fa")

    if mode == "none":
        return True, "", None

    ok_tg = True
    if tg_channel:
        try:
            mem = bot.get_chat_member(tg_channel, user_id)
            ok_tg = mem.status in ("creator", "administrator", "member")
            print(f"DEBUG: Force sub check for user {user_id} in channel {tg_channel}: status={mem.status}, ok={ok_tg}")
        except Exception as e:
            print(f"DEBUG: Force sub check failed for user {user_id} in channel {tg_channel}: {e}")
            ok_tg = False

    if ok_tg:
        return True, "", None

    kb = InlineKeyboardMarkup()
    if tg_channel:
        kb.add(
            InlineKeyboardButton(
                t("force_sub_btn_join_channel", lang),
                url=f"https://t.me/{tg_channel.lstrip('@')}",
            )
        )
    if ig_url:
        kb.add(InlineKeyboardButton(t("force_sub_btn_follow_instagram", lang), url=ig_url))
    kb.add(InlineKeyboardButton(t("force_sub_btn_joined", lang), callback_data="fs:recheck"))

    lines = [t("force_sub_title", lang)]
    if tg_channel:
        lines.append(t("force_sub_join_channel", lang))
    if ig_url:
        lines.append(t("force_sub_join_instagram", lang))
    lines.append("")
    lines.append(t("force_sub_hint", lang))
    txt = "\n".join(lines)
    return False, txt, kb
