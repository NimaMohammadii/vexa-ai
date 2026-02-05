# modules/admin/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import datetime
from typing import Optional
import db
from modules.lang.keyboards import LANGS
from modules.tts.settings import get_demo_audio, get_voices
from modules.welcome_audio import get_welcome_audio
from modules.tts_openai.settings import VOICES as OPENAI_VOICES

FEATURE_TOGGLES = [
    ("GPT", "FEATURE_GPT"),
    ("تبدیل متن به صدا", "FEATURE_TTS"),
    ("Voice Clone", "FEATURE_CLONE"),
    ("تولید تصویر", "FEATURE_IMAGE"),
    ("تولید ویدیو", "FEATURE_VIDEO"),
    ("Sora 2", "FEATURE_SORA2"),
]

def _chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]

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
    kb.add(InlineKeyboardButton("🧬 کاربران Voice Clone", callback_data="admin:clone"))
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


def voice_clone_menu(page: int = 0, page_size: int = 8):
    page = max(0, int(page))
    offset = page * page_size
    rows = db.list_voice_clones(limit=page_size, offset=offset)

    kb = InlineKeyboardMarkup()
    if not rows:
        kb.add(InlineKeyboardButton("— صدای کلونی ثبت نشده —", callback_data="admin:noop"))
    else:
        for item in rows:
            label = f"🎙 {item['voice_name']} · {item['user_id']}"
            if item["username"]:
                label += f" · @{item['username']}"
            kb.add(InlineKeyboardButton(label, callback_data=f"admin:clone:voice:{item['voice_id']}"))

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:clone:prev:{page}"))
    if len(rows) == page_size:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:clone:next:{page}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:menu"))
    return kb


def voice_clone_actions_menu(voice_id: str, user_id: int):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🎙 استفاده از صدا", callback_data=f"admin:clone:use:{voice_id}"))
    kb.add(InlineKeyboardButton("👤 پروفایل کاربر", callback_data=f"admin:user:{user_id}"))
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:clone"))
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
    kb.add(InlineKeyboardButton("🎧 دموهای صدا", callback_data="admin:demo"))
    kb.add(InlineKeyboardButton("🎙 پیام صوتی خوش‌آمد", callback_data="admin:welcome_audio"))
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:menu"))
    return kb


def _chunk(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def demo_languages_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    row = []
    for label, code in LANGS:
        row.append(InlineKeyboardButton(label, callback_data=f"admin:demo:lang:{code}"))
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:settings"))
    return kb


def demo_voices_menu(lang_code: str):
    voices = list(get_voices(lang_code).keys())
    voices.sort()

    kb = InlineKeyboardMarkup(row_width=3)
    for row in _chunk(voices, 3):
        buttons = []
        for name in row:
            has_demo = bool(get_demo_audio(name, lang_code))
            label = f"{'✅ ' if has_demo else ''}{name}"
            buttons.append(InlineKeyboardButton(label, callback_data=f"admin:demo:voice:{lang_code}:{name}"))
        kb.row(*buttons)
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:demo"))
    return kb


def demo_voice_actions_menu(lang_code: str, voice_name: str):
    has_demo = bool(get_demo_audio(voice_name, lang_code))
    kb = InlineKeyboardMarkup()
    if has_demo:
        kb.add(InlineKeyboardButton("🗑 حذف دمو", callback_data=f"admin:demo:delete:{lang_code}:{voice_name}"))
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data=f"admin:demo:lang:{lang_code}"))
    return kb


def welcome_audio_languages_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    row = []
    for label, code in LANGS:
        has_audio = bool(get_welcome_audio(code))
        prefix = "✅ " if has_audio else ""
        row.append(InlineKeyboardButton(f"{prefix}{label}", callback_data=f"admin:welcome_audio:lang:{code}"))
        if len(row) == 2:
            kb.row(*row)
            row = []
    if row:
        kb.row(*row)
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:settings"))
    return kb


def welcome_audio_actions_menu(lang_code: str):
    has_audio = bool(get_welcome_audio(lang_code))
    kb = InlineKeyboardMarkup()
    if has_audio:
        kb.add(InlineKeyboardButton("🗑 حذف پیام خوش‌آمد", callback_data=f"admin:welcome_audio:delete:{lang_code}"))
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:welcome_audio"))
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
    kb.add(
        InlineKeyboardButton(
            "🎛 مدیریت صداهای کاربر",
            callback_data=f"admin:user_voices:{uid}",
        )
    )
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data="admin:users"))
    return kb

def user_voice_languages_menu(uid: int):
    kb = InlineKeyboardMarkup()
    for row in _chunk(LANGS, 2):
        kb.row(
            *[
                InlineKeyboardButton(
                    label,
                    callback_data=f"admin:user_voices:lang:{uid}:{code}",
                )
                for label, code in row
            ]
        )
    kb.add(
        InlineKeyboardButton(
            "🎙 صداهای شخصی",
            callback_data=f"admin:user_voices:custom:{uid}",
        )
    )
    kb.add(
        InlineKeyboardButton(
            "🎧 صداهای OpenAI",
            callback_data=f"admin:user_voices:openai:{uid}",
        )
    )
    kb.add(InlineKeyboardButton("⬅️ بازگشت", callback_data=f"admin:user:{uid}"))
    return kb

def user_voice_list_menu(uid: int, lang_code: str, page: int = 0, page_size: int = 10):
    page = max(0, int(page))
    disabled = db.list_disabled_voices(uid, lang_code)

    if lang_code == "custom":
        voices = [voice[0] for voice in db.list_user_voices(uid)]
    elif lang_code == "openai":
        voices = list(OPENAI_VOICES.keys())
    else:
        voices = list(get_voices(lang_code).keys())

    voices.sort()
    offset = page * page_size
    page_items = voices[offset : offset + page_size]

    kb = InlineKeyboardMarkup()
    if not voices:
        kb.add(InlineKeyboardButton("— صدایی یافت نشد —", callback_data="admin:noop"))
    else:
        for name in page_items:
            status = "🚫" if name in disabled else "✅"
            kb.add(
                InlineKeyboardButton(
                    f"{status} {name}",
                    callback_data=f"admin:user_voices:toggle:{uid}:{lang_code}:{name}",
                )
            )

    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                "◀️ قبلی",
                callback_data=f"admin:user_voices:page:{uid}:{lang_code}:{page - 1}",
            )
        )
    if len(page_items) == page_size:
        nav.append(
            InlineKeyboardButton(
                "بعدی ▶️",
                callback_data=f"admin:user_voices:page:{uid}:{lang_code}:{page + 1}",
            )
        )
    if nav:
        kb.row(*nav)

    kb.add(
        InlineKeyboardButton(
            "⬅️ بازگشت",
            callback_data=f"admin:user_voices:{uid}",
        )
    )
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
