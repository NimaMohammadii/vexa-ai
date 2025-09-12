from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def edit_or_send(bot, chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    try:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                              text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    except Exception:
        bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode)

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

def check_force_sub(bot, user_id, settings):
    """
    returns: (ok, text, markup)
    """
    mode = (settings.get("FORCE_SUB_MODE") or "none").strip()
    tg_channel = (settings.get("TG_CHANNEL") or "").strip()
    ig_url = (settings.get("IG_URL") or "").strip()

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
        kb.add(InlineKeyboardButton("عضو کانال تلگرام شو ✅", url=f"https://t.me/{tg_channel.lstrip('@')}"))
    if ig_url:
        kb.add(InlineKeyboardButton("اینستاگرام ما 📷", url=ig_url))
    kb.add(InlineKeyboardButton("✅ انجام شد", callback_data="fs:recheck"))

    txt = "برای ادامه، ابتدا عضو شو:\n"
    if tg_channel: txt += f"📢 {tg_channel}\n"
    if ig_url:     txt += f"📷 {ig_url}\n"
    txt += "\nسپس روی «انجام شد» بزن."
    return False, txt, kb