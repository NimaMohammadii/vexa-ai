# modules/credit/keyboards.py
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from modules.i18n import t

# ستاره ← کردیت
STAR_TO_CREDIT = {
    15: 300,
    28: 600,
    55: 1230,
    99: 2155,
    175: 4500,
    299: 8800,
}

def keyboard(lang: str = "fa"):
    kb = InlineKeyboardMarkup()

    stars = list(STAR_TO_CREDIT.keys())

    # ردیف ۱: 15, 28
    kb.row(
        InlineKeyboardButton(f"Pay ⭐{stars[0]} — {STAR_TO_CREDIT[stars[0]]}💳", callback_data=f"credit:buy:{stars[0]}"),
        InlineKeyboardButton(f"Pay ⭐{stars[1]} — {STAR_TO_CREDIT[stars[1]]}💳", callback_data=f"credit:buy:{stars[1]}"),
    )
    # ردیف ۲: 55
    kb.add(InlineKeyboardButton(f"Pay ⭐{stars[2]} — {STAR_TO_CREDIT[stars[2]]}💳", callback_data=f"credit:buy:{stars[2]}"))
    # ردیف ۳: 99, 175
    kb.row(
        InlineKeyboardButton(f"Pay ⭐{stars[3]} — {STAR_TO_CREDIT[stars[3]]}💳", callback_data=f"credit:buy:{stars[3]}"),
        InlineKeyboardButton(f"Pay ⭐{stars[4]} — {STAR_TO_CREDIT[stars[4]]}💳", callback_data=f"credit:buy:{stars[4]}"),
    )
    # ردیف ۴: 260
    kb.add(InlineKeyboardButton(f"Pay ⭐{stars[5]} — {STAR_TO_CREDIT[stars[5]]}💳", callback_data=f"credit:buy:{stars[5]}"))

    # فقط بازگشت (بدون پرداخت ریالی)
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb

# برای سازگاری با ایمپورت‌های قبلی
def plans_keyboard(lang: str = "fa"):
    return keyboard(lang)
