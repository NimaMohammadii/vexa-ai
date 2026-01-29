from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from modules.i18n import t

from .settings import PAYMENT_PLANS, STAR_PACKAGES


def augment_with_rial(base_kb: InlineKeyboardMarkup | None, lang: str) -> InlineKeyboardMarkup:
    kb = base_kb or InlineKeyboardMarkup(row_width=2)
    if lang == "fa":
        kb.add(InlineKeyboardButton(t("credit_pay_rial_btn", lang), callback_data="credit:payrial"))
    return kb

def payrial_plans_kb(lang: str = "fa") -> InlineKeyboardMarkup:
    """منوی دکمه‌های قیمت‌های مختلف"""
    kb = InlineKeyboardMarkup(row_width=2)
    
    # اضافه کردن دکمه‌ها بصورت 2 در 2
    row = []
    for i, plan in enumerate(PAYMENT_PLANS):
        btn = InlineKeyboardButton(
            plan["title"], 
            callback_data=f"credit:select:{i}"
        )
        row.append(btn)
        
        # هر 2 دکمه یا در انتها، ردیف رو اضافه کن
        if len(row) == 2 or i == len(PAYMENT_PLANS) - 1:
            kb.row(*row)
            row = []
    
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb

def admin_approve_kb(user_id: int, plan_index: int) -> InlineKeyboardMarkup:
    """دکمه‌های تایید/رد برای ادمین"""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ تایید", callback_data=f"credit_admin:approve:{user_id}:{plan_index}"),
        InlineKeyboardButton("❌ رد", callback_data=f"credit_admin:reject:{user_id}:{plan_index}")
    )
    return kb

def credit_menu_kb(lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(t("credit_pay_stars_btn", lang), callback_data="credit:stars"))
    if lang == "fa":
        kb.add(InlineKeyboardButton(t("credit_pay_rial_btn", lang), callback_data="credit:payrial"))
    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb

def stars_packages_kb(lang: str) -> InlineKeyboardMarkup:
    """منوی بسته‌های Telegram Stars — هر ردیف دو دکمه"""
    kb = InlineKeyboardMarkup(row_width=2)
    row: list[InlineKeyboardButton] = []
    for pkg in STAR_PACKAGES:
        btn = InlineKeyboardButton(
            pkg["title"],
            callback_data=f"credit:buy:{pkg['stars']}:{pkg['credits']}"
        )
        row.append(btn)
        if len(row) == 2:
            kb.row(*row)
            row = []
    # اگر تعداد دکمه‌ها فرد بود، ردیف آخر را اضافه کن
    if row:
        kb.row(*row)

    kb.add(InlineKeyboardButton(t("back", lang), callback_data="home:back"))
    return kb

def instant_cancel_kb(lang: str = "fa") -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(InlineKeyboardButton(t("credit_cancel", lang), callback_data="credit:cancel"))
    return kb
