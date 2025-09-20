# modules/admin/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import db

# ————— منوی اصلی ادمین —————
def admin_menu():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("📊 آمار", callback_data="admin:stats"),
        InlineKeyboardButton("👥 کاربران", callback_data="admin:users"),
    )
    kb.row(
        InlineKeyboardButton("➕ افزودن کردیت", callback_data="admin:add"),
        InlineKeyboardButton("➖ کسر کردیت", callback_data="admin:sub"),
    )
    kb.add(InlineKeyboardButton("♻️ ریست کاربر", callback_data="admin:reset"))
    kb.row(
        InlineKeyboardButton("✉️ پیام تکی", callback_data="admin:dm"),
        InlineKeyboardButton("📣 پیام همگانی", callback_data="admin:cast"),
    )
    kb.row(
        InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin:settings"),
        InlineKeyboardButton("📤 خروجی‌ها", callback_data="admin:exports"),
    )
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:back"))
    return kb

# ————— منوی تنظیمات —————
def settings_menu():
    s = db.get_settings()
    mode = (s.get("FORCE_SUB_MODE") or "none").lower()
    mode_label = {"none": "خاموش", "new": "فقط جدیدها", "all": "همه"}.get(mode, mode)

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("🎁 بونوس رفرال", callback_data="admin:set:bonus"),
        InlineKeyboardButton("🎉 کردیت شروع", callback_data="admin:set:free"),
    )
    kb.row(
        InlineKeyboardButton("📢 کانال تلگرام", callback_data="admin:set:tg"),
        InlineKeyboardButton("📷 لینک اینستاگرام", callback_data="admin:set:ig"),
    )
    kb.add(InlineKeyboardButton(f"🔐 عضویت اجباری: {mode_label}", callback_data="admin:toggle:fs"))
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:menu"))
    return kb

# ————— لیست کاربران با صفحه‌بندی —————
def users_menu(page: int = 0, page_size: int = 10):
    page = max(0, int(page))
    offset = page * page_size
    rows = db.list_users(limit=page_size, offset=offset)

    kb = InlineKeyboardMarkup()
    if not rows:
        kb.add(InlineKeyboardButton("— کاربری یافت نشد —", callback_data="admin:noop"))
    else:
        for user_id, username, credits, banned in rows:
            label = f"{'🚫' if banned else '✅'} {user_id}"
            if username:
                label += f" · @{username}"
            label += f" · 💳 {credits}"
            kb.add(InlineKeyboardButton(label, callback_data=f"admin:user:{user_id}"))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:users:prev:{page}"))
    if len(rows) == page_size:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:users:next:{page}"))
    if nav:
        kb.row(*nav)

    kb.add(InlineKeyboardButton("🔎 جستجوی کاربر", callback_data="admin:user:lookup"))
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:menu"))
    return kb

# ————— اکشن‌های مربوط به یک کاربر —————
def user_actions(uid: int):
    u = db.get_user(uid) or {}
    banned = bool(u.get("banned"))

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("➕ افزودن", callback_data=f"admin:uadd:{uid}"),
        InlineKeyboardButton("➖ کسر",   callback_data=f"admin:usub:{uid}"),
    )
    kb.row(
        InlineKeyboardButton("✉️ پیام تکی", callback_data=f"admin:dm:{uid}"),
        InlineKeyboardButton("🚫 بن" if not banned else "✅ آن‌بن",
                             callback_data=f"admin:{'ban' if not banned else 'unban'}:{uid}"),
    )
    kb.row(
        InlineKeyboardButton("📥 متن‌های TTS کاربر", callback_data=f"admin:exp_user_tts:{uid}"),
        InlineKeyboardButton("💬 پیام‌های کاربر",     callback_data=f"admin:exp_user_msgs:{uid}"),
    )
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:users"))
    return kb

# ————— منوی خروجی‌ها —————
def exports_menu():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("👥 کاربران", callback_data="admin:exp:users"),
        InlineKeyboardButton("🪙 خریدها",  callback_data="admin:exp:buy"),
    )
    kb.add(InlineKeyboardButton("💬 پیام‌ها", callback_data="admin:exp:msg"))
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:menu"))
    return kb