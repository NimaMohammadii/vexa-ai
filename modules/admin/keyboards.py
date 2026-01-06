# modules/admin/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import datetime
from typing import Optional
import db
from modules.lang.keyboards import LANGS

FEATURE_TOGGLES = [
    ("GPT", "FEATURE_GPT"),
    ("تبدیل متن به صدا", "FEATURE_TTS"),
    ("Voice Clone", "FEATURE_CLONE"),
    ("تولید تصویر", "FEATURE_IMAGE"),
    ("تولید ویدیو", "FEATURE_VIDEO"),
    ("Sora 2", "FEATURE_SORA2"),
]

# ————— منوی اصلی ادمین —————
def admin_menu():
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("📊 آمار", callback_data="admin:stats"),
        InlineKeyboardButton("👥 کاربران", callback_data="admin:users"),
    )
    kb.row(
        InlineKeyboardButton("🌐 کاربران بر اساس زبان", callback_data="admin:lang_users"),
    )
    kb.row(
        InlineKeyboardButton("🖼️ کاربران تصویر", callback_data="admin:image_users"),
        InlineKeyboardButton("🤖 کاربران GPT", callback_data="admin:gpt_users"),
    )
    kb.add(InlineKeyboardButton("🎁 پاداش روزانه", callback_data="admin:daily_reward_users"))
    kb.row(
        InlineKeyboardButton("➕ افزودن کردیت", callback_data="admin:add"),
        InlineKeyboardButton("➖ کسر کردیت", callback_data="admin:sub"),
    )
    kb.add(InlineKeyboardButton("🧮 فرمول کردیت همگانی", callback_data="admin:bulk_credit"))
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

def cast_lang_menu():
    kb = InlineKeyboardMarkup()
    row = [InlineKeyboardButton("🌍 همه زبان‌ها", callback_data="admin:cast_lang:all")]
    kb.row(*row)
    row = []
    for label, code in LANGS:
        row.append(InlineKeyboardButton(label, callback_data=f"admin:cast_lang:{code}"))
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:menu"))
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
    kb.add(InlineKeyboardButton("🧩 دسترسی بخش‌ها", callback_data="admin:features"))
    kb.add(InlineKeyboardButton("🔐 عضویت اجباری بر اساس زبان", callback_data="admin:fs_lang:list"))
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:menu"))
    return kb


def feature_access_menu():
    s = db.get_settings()
    kb = InlineKeyboardMarkup()
    for label, key in FEATURE_TOGGLES:
        raw = (s.get(key) or "1").strip().lower()
        enabled = raw in {"1", "true", "yes", "on", "enabled"}
        status = "✅ فعال" if enabled else "❌ غیرفعال"
        kb.add(InlineKeyboardButton(f"{label}: {status}", callback_data=f"admin:feature:toggle:{key}"))
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:settings"))
    return kb


def force_sub_lang_list():
    kb = InlineKeyboardMarkup(row_width=2)
    row = []
    for label, code in LANGS:
        row.append(InlineKeyboardButton(label, callback_data=f"admin:fs_lang:open:{code}"))
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:settings"))
    return kb


def force_sub_lang_menu(lang_code: str):
    s = db.get_settings()
    mode_key = f"FORCE_SUB_MODE_{lang_code}"
    tg_key = f"TG_CHANNEL_{lang_code}"
    mode = (s.get(mode_key) or "none").lower()
    mode_label = {"none": "خاموش", "new": "فقط جدیدها", "all": "همه"}.get(mode, mode)
    channel = (s.get(tg_key) or "").strip() or "—"

    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(f"🔐 عضویت اجباری: {mode_label}", callback_data=f"admin:fs_lang:toggle:{lang_code}"))
    kb.add(InlineKeyboardButton(f"📢 کانال تلگرام: {channel}", callback_data=f"admin:fs_lang:set_tg:{lang_code}"))
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:fs_lang:list"))
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
            label += f" · 💳 {db.format_credit_amount(credits)}"
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


def _format_ts(ts: Optional[int]) -> str:
    if not ts:
        return "-"
    try:
        dt = datetime.datetime.fromtimestamp(int(ts))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)


def image_users_menu(page: int = 0, page_size: int = 10):
    page = max(0, int(page))
    offset = page * page_size
    rows = db.list_image_users(limit=page_size, offset=offset)

    kb = InlineKeyboardMarkup()
    if not rows:
        kb.add(InlineKeyboardButton("— کاربری یافت نشد —", callback_data="admin:noop"))
    else:
        for row in rows:
            uid = row.get("user_id")
            username = row.get("username")
            banned = bool(row.get("banned"))
            total = row.get("total_images") or 0
            last_ts = row.get("last_created_at")
            label = f"{'🚫' if banned else '✅'} {uid}"
            if username:
                label += f" · @{username}"
            label += f" · 🖼️ {total}"
            label += f" · 🕒 {_format_ts(last_ts)}"
            kb.add(InlineKeyboardButton(label, callback_data=f"admin:user:{uid}"))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:image_users:prev:{page}"))
    if len(rows) == page_size:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:image_users:next:{page}"))
    if nav:
        kb.row(*nav)

    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:menu"))
    return kb


def gpt_users_menu(page: int = 0, page_size: int = 10):
    page = max(0, int(page))
    offset = page * page_size
    rows = db.list_gpt_users(limit=page_size, offset=offset)

    kb = InlineKeyboardMarkup()
    if not rows:
        kb.add(InlineKeyboardButton("— کاربری یافت نشد —", callback_data="admin:noop"))
    else:
        for row in rows:
            uid = row.get("user_id")
            username = row.get("username")
            banned = bool(row.get("banned"))
            total = row.get("total_messages") or 0
            last_ts = row.get("last_created_at")
            label = f"{'🚫' if banned else '✅'} {uid}"
            if username:
                label += f" · @{username}"
            label += f" · 💬 {total}"
            label += f" · 🕒 {_format_ts(last_ts)}"
            kb.add(InlineKeyboardButton(label, callback_data=f"admin:user:{uid}"))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:gpt_users:prev:{page}"))
    if len(rows) == page_size:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:gpt_users:next:{page}"))
    if nav:
        kb.row(*nav)

    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:menu"))
    return kb


def daily_reward_users_menu(page: int = 0, page_size: int = 10):
    page = max(0, int(page))
    offset = page * page_size
    rows = db.list_daily_reward_users(limit=page_size, offset=offset)

    kb = InlineKeyboardMarkup()
    if not rows:
        kb.add(InlineKeyboardButton("— کاربری یافت نشد —", callback_data="admin:noop"))
    else:
        for row in rows:
            uid = row.get("user_id")
            username = row.get("username")
            banned = bool(row.get("banned"))
            credits = row.get("credits") or 0
            last_ts = row.get("last_daily_reward")
            label = f"{'🚫' if banned else '✅'} {uid}"
            if username:
                label += f" · @{username}"
            label += f" · 💳 {db.format_credit_amount(credits)}"
            label += f" · 🕒 {_format_ts(last_ts)}"
            kb.add(InlineKeyboardButton(label, callback_data=f"admin:user:{uid}"))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:daily_reward_users:prev:{page}"))
    if len(rows) == page_size:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:daily_reward_users:next:{page}"))
    if nav:
        kb.row(*nav)

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
    kb.add(
        InlineKeyboardButton(
            "🤖 گفتگوهای GPT",
            callback_data=f"admin:exp_user_gpt:{uid}",
        )
    )
    kb.add(
        InlineKeyboardButton(
            "🖼️ دانلود تبدیل عکس‌های کاربر",
            callback_data=f"admin:exp_user_images:{uid}"
        )
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
