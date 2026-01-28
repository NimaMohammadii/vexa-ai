from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telebot.apihelper import ApiTelegramException

from modules.i18n import t

import re
import db

_FEATURE_LABEL_KEYS = {
    "FEATURE_PROFILE": "feature_profile",
    "FEATURE_CREDIT": "feature_credit",
    "FEATURE_GPT": "feature_gpt",
    "FEATURE_TTS": "feature_tts",
    "FEATURE_CLONE": "feature_clone",
    "FEATURE_IMAGE": "feature_image",
    "FEATURE_VIDEO": "feature_video",
    "FEATURE_SORA2": "feature_sora2",
    "FEATURE_LANG": "feature_lang",
    "FEATURE_INVITE": "feature_invite",
}
_FEATURE_ENABLED_VALUES = {"1", "true", "yes", "on", "enabled"}


def is_feature_enabled(feature_key: str, default: str = "1") -> bool:
    value = (db.get_setting(feature_key, default) or default).strip().lower()
    return value in _FEATURE_ENABLED_VALUES


def feature_label(feature_key: str, lang: str) -> str:
    label_key = _FEATURE_LABEL_KEYS.get(feature_key)
    return t(label_key, lang) if label_key else feature_key


def feature_disabled_text(feature_key: str, lang: str) -> str:
    return t("feature_disabled", lang).format(feature=feature_label(feature_key, lang))

def edit_or_send(
    bot,
    chat_id,
    message_id,
    text,
    reply_markup=None,
    parse_mode="HTML",
    user_id: int | None = None,
):
    tracker_id = user_id or chat_id
    if tracker_id:
        last_menu_id = db.get_last_main_menu_id(tracker_id)
        if last_menu_id and last_menu_id != message_id:
            try:
                bot.delete_message(chat_id, last_menu_id)
            except Exception:
                pass
    try:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        if tracker_id and message_id is not None:
            db.set_last_main_menu_id(tracker_id, message_id)
    except ApiTelegramException as exc:
        # اگر پیام تغییری نکرده باشد، تلگرام خطای «message is not modified» می‌دهد.
        # در این حالت نیازی به ارسال پیام جدید نیست.
        if "message is not modified" in str(exc).lower():
            if tracker_id and message_id is not None:
                db.set_last_main_menu_id(tracker_id, message_id)
            return
        sent = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        if tracker_id:
            db.set_last_main_menu_id(tracker_id, sent.message_id)
        if message_id is not None:
            try:
                bot.delete_message(chat_id, message_id)
            except Exception:
                pass
    except Exception:
        sent = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        if tracker_id:
            db.set_last_main_menu_id(tracker_id, sent.message_id)
        if message_id is not None:
            try:
                bot.delete_message(chat_id, message_id)
            except Exception:
                pass

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


def send_main_menu(
    bot,
    user_id: int,
    chat_id: int,
    text: str,
    reply_markup=None,
    message_id: int | None = None,
    parse_mode: str = "HTML",
):
    last_menu_id = db.get_last_main_menu_id(user_id)
    if last_menu_id and last_menu_id != message_id:
        try:
            bot.delete_message(chat_id, last_menu_id)
        except Exception:
            pass

    if message_id is None:
        msg = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        db.set_last_main_menu_id(user_id, msg.message_id)
        return msg

    try:
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
        )
        db.set_last_main_menu_id(user_id, message_id)
        return None
    except ApiTelegramException as exc:
        if "message is not modified" in str(exc).lower():
            db.set_last_main_menu_id(user_id, message_id)
            return None
        msg = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        db.set_last_main_menu_id(user_id, msg.message_id)
        return msg
    except Exception:
        msg = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)
        db.set_last_main_menu_id(user_id, msg.message_id)
        return msg

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

def _lang_setting(settings: dict, key: str, lang: str | None):
    if not lang:
        return settings.get(key)
    lang_key = f"{key}_{lang}"
    if lang_key in settings:
        return settings.get(lang_key)
    return settings.get(key)


def check_force_sub(bot, user_id, settings, lang: str | None = None):
    """
    returns: (ok, text, markup)
    """
    mode = (_lang_setting(settings, "FORCE_SUB_MODE", lang) or "none").strip()
    tg_channel = (_lang_setting(settings, "TG_CHANNEL", lang) or "").strip()
    ig_url = (settings.get("IG_URL") or "").strip()

    lang = (lang or "fa")

    if mode == "none":
        return True, "", None

    ok_tg = True
    channel_ref = _normalize_tg_channel_ref(tg_channel)
    join_url = _build_tg_join_url(tg_channel)
    if channel_ref:
        try:
            mem = bot.get_chat_member(channel_ref, user_id)
            ok_tg = mem.status in ("creator", "administrator", "member") or (
                mem.status == "restricted" and getattr(mem, "is_member", False)
            )
            print(
                "DEBUG: Force sub check for user"
                f" {user_id} in channel {channel_ref}: status={mem.status}, ok={ok_tg}"
            )
        except ApiTelegramException as e:
            err = str(e).lower()
            perm_blocked = any(
                hint in err
                for hint in (
                    "chat not found",
                    "bot is not a member",
                    "not enough rights",
                    "not enough rights to get chat members",
                    "chat_admin_required",
                    "have no rights",
                )
            )
            print(
                "DEBUG: Force sub check failed for user"
                f" {user_id} in channel {channel_ref}: {e}"
            )
            ok_tg = perm_blocked
        except Exception as e:
            print(
                "DEBUG: Force sub check failed for user"
                f" {user_id} in channel {channel_ref}: {e}"
            )
            ok_tg = False

    if ok_tg:
        return True, "", None

    kb = InlineKeyboardMarkup()
    if join_url:
        kb.add(
            InlineKeyboardButton(
                t("force_sub_btn_join_channel", lang),
                url=join_url,
            )
        )
    if ig_url:
        kb.add(InlineKeyboardButton(t("force_sub_btn_follow_instagram", lang), url=ig_url))
    kb.add(InlineKeyboardButton(t("force_sub_btn_joined", lang), callback_data="fs:recheck"))

    lines = [t("force_sub_title", lang)]
    if join_url:
        lines.append(t("force_sub_join_channel", lang))
    if ig_url:
        lines.append(t("force_sub_join_instagram", lang))
    lines.append("")
    lines.append(t("force_sub_hint", lang))
    txt = "\n".join(lines)
    return False, txt, kb


def _normalize_tg_channel_ref(raw_channel: str | None) -> str | None:
    if not raw_channel:
        return None
    channel = raw_channel.strip()
    if not channel:
        return None
    if channel.startswith("@"):
        return channel
    match = re.search(r"t\.me/(?P<name>[A-Za-z0-9_]{4,})", channel)
    if match:
        return f"@{match.group('name')}"
    if re.fullmatch(r"[A-Za-z0-9_]{4,}", channel):
        return f"@{channel}"
    return None


def _build_tg_join_url(raw_channel: str | None) -> str | None:
    if not raw_channel:
        return None
    channel = raw_channel.strip()
    if not channel:
        return None
    if channel.startswith("http://") or channel.startswith("https://"):
        return channel
    if channel.startswith("t.me/"):
        return f"https://{channel}"
    if channel.startswith("@"):
        return f"https://t.me/{channel[1:]}"
    if re.fullmatch(r"[A-Za-z0-9_]{4,}", channel):
        return f"https://t.me/{channel}"
    return None


def ensure_force_sub(bot, user_id, chat_id, message_id, lang: str | None = None) -> bool:
    import db

    settings = db.get_settings()
    ok, txt, kb = check_force_sub(bot, user_id, settings, lang)
    if ok:
        return True
    if message_id is None:
        bot.send_message(chat_id, txt, reply_markup=kb, parse_mode="HTML")
    else:
        edit_or_send(bot, chat_id, message_id, txt, kb)
    return False
