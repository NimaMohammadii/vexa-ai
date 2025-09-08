# minimal non-destructive additions for translations used by credit module

try:
    LABELS
except NameError:
    LABELS = {}

LABELS.update({
    "pay_stars_btn": {
        "fa": "خرید با Telegram Stars ⭐️",
        "en": "Pay with Telegram Stars ⭐️",
        "ar": "الدفع عبر Telegram Stars ⭐️",
        "tr": "Telegram Stars ile Öde ⭐️",
        "ru": "Оплатить через Telegram Stars ⭐️",
        "es": "Pagar con Telegram Stars ⭐️",
        "de": "Mit Telegram Stars bezahlen ⭐️",
        "fr": "Payer avec Telegram Stars ⭐️",
    },
    "pay_rial_btn": {
        "fa": "پرداخت به تومان",
        "en": "Pay with Toman",
        "ar": "الدفع بالتومان",
        "tr": "Toman ile Öde",
        "ru": "Оплатить в томанах",
        "es": "Pagar con Toman",
        "de": "Mit Toman bezahlen",
        "fr": "Payer en Toman",
    },
    "pay_rial_title": {
        "fa": "پرداخت به تومـان – انتخاب پلن",
        "en": "Pay with Toman – Choose plan",
        "ar": "الدفع بالتومان – اختر الخطة",
        "tr": "Toman ile Öde – Plan Seç",
        "ru": "Оплата в туманах – Выберите план",
        "es": "Pago en Toman – Elige plan",
        "de": "Bezahlen in Toman – Plan wählen",
        "fr": "Paiement en Toman – Choisir un plan",
    },
    "pay_rial_plans_header": {
        "fa": "یکی از پلن‌های زیر را انتخاب کن:",
        "en": "Choose one of the plans below:",
        "ar": "اختر إحدى الخطط أدناه:",
        "tr": "Aşağıdaki planlardan birini seçin:",
        "ru": "Выберите один из планов ниже:",
        "es": "Elige uno de los планов a continuación:",
        "de": "Wähle einen der folgenden Pläne:",
        "fr": "Choisissez l'un des plans ci-dessous :",
    },
    "pay_rial_instant": {
        "fa": "پرداخت فوری (کارت‌به‌کارت)",
        "en": "Instant pay (card to card)",
        "ar": "دفع فوري (تحويل بطاقة إلى بطاقة)",
        "tr": "Anında ödeme (karttan karta)",
        "ru": "Мгновенная оплата (карта-карта)",
        "es": "Pago instantáneo (tarjeta a tarjeta)",
        "de": "Sofortzahlung (Karte zu Karte)",
        "fr": "Paiement instantané (carte à carte)",
    },
    "credits_label": {
        "fa": "{credits} کردیت",
        "en": "{credits} credits",
        "ar": "{credits} رصيد",
        "tr": "{credits} kredi",
        "ru": "{credits} кредитов",
        "es": "{credits} créditos",
        "de": "{credits} Guthaben",
        "fr": "{credits} crédits",
    },
    "cancel": {
        "fa": "لغو ❌",
        "en": "Cancel ❌",
        "ar": "إلغاء ❌",
        "tr": "İptal ❌",
        "ru": "Отмена ❌",
        "es": "Cancelar ❌",
        "de": "Abbrechen ❌",
        "fr": "Annuler ❌",
    },
    "credit_invoice_title": {
        "fa": "خرید کردیت",
        "en": "Buy credits",
        "ar": "شراء رصيد",
        "tr": "Kredi satın al",
        "ru": "Купить кредиты",
        "es": "Comprar créditos",
        "de": "Credits kaufen",
        "fr": "Acheter des crédits",
    },
    "credit_invoice_desc": {
        "fa": "با انتخاب بسته مورد نظر، پرداخت از طریق Telegram Stars انجام می‌شود.",
        "en": "Select a package to pay using Telegram Stars.",
        "ar": "اختر حزمة للدفع عبر Telegram Stars.",
        "tr": "Telegram Stars ile ödeme yapmak için bir paket seçin.",
        "ru": "Выберите пакет для оплаты через Telegram Stars.",
        "es": "Selecciona un paquete para pagar con Telegram Stars.",
        "de": "Wähle ein Paket, um mit Telegram Stars zu bezahlen.",
        "fr": "Sélectionnez un forfait pour payer avec Telegram Stars.",
    },
    "back": {
        "fa": "بازگشت 🔙",
        "en": "Back 🔙",
        "ar": "رجوع 🔙",
        "tr": "Geri 🔙",
        "ru": "Назад 🔙",
        "es": "Atrás 🔙",
        "de": "Zurück 🔙",
        "fr": "Retour 🔙",
    }
})

def t(key: str, lang: str | None = None) -> str:
    lang = (lang or "fa")[:2]
    entry = LABELS.get(key)
    if not entry:
        return key
    # try exact lang, then English fallback, then any available value
    if lang in entry:
        return entry[lang]
    if "en" in entry:
        return entry["en"]
    # return first available translation
    return next(iter(entry.values()))
