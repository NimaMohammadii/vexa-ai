# modules/i18n.py
LABELS = {
    # Home
    "home_title": {"fa":"/help   منوی اصلی","en":"Main Menu","ar":"القائمة الرئيسية","tr":"Ana Menü","ru":"Главное меню","es":"Menú principal","de":"Hauptmenü","fr":"Menu principal"},
    "home_body":  {"fa":"یکی از گزینه‌های زیر را انتخاب کنید:","en":"Choose an option:","ar":"اختر خياراً:","tr":"Bir seçenek seçin:","ru":"Выберите опцию:","es":"Elige una opción:","de":"Wähle eine Option:","fr":"Choisissez une option :"},
    "btn_tts":    {"fa":"تبدیل متن به صدا 🎧","en":"Text to Speech 🎧","ar":"تحويل النص إلى صوت 🎧","tr":"Metinden Sese 🎧","ru":"Текст в речь 🎧","es":"Texto a voz 🎧","de":"Text zu Sprache 🎧","fr":"Texte en voix 🎧"},
    "btn_profile":{"fa":"پروفایل 🙋🏼‍♂️","en":"Profile 🙋🏼‍♂️","ar":"الملف الشخصي 🙋🏼‍♂️","tr":"Profil 🙋🏼‍♂️","ru":"Профиль 🙋🏼‍♂️","es":"Perfil 🙋🏼‍♂️","de":"Profil 🙋🏼‍♂️","fr":"Profil 🙋🏼‍♂️"},
    "btn_credit": {"fa":"خرید کردیـت 🛒","en":"Buy Credit 🛒","ar":"شراء الرصيد 🛒","tr":"Kredi Satın Al 🛒","ru":"Купить кредит 🛒","es":"Comprar crédito 🛒","de":"Guthaben kaufen 🛒","fr":"Acheter du crédit 🛒"},
    "btn_invite": {"fa":"دعوت دوستان 🎁","en":"Invite Friends 🎁","ar":"دعوة الأصدقاء 🎁","tr":"Arkadaş Davet Et 🎁","ru":"Пригласить друзей 🎁","es":"Invitar amigos 🎁","de":"Freunde einladen 🎁","fr":"Inviter des amis 🎁"},
    "btn_lang":   {"fa":"Language 📚","en":"Language 📚","ar":"اللغة 📚","tr":"Dil 📚","ru":"Язык 📚","es":"Idioma 📚","de":"Sprache 📚","fr":"Langue 📚"},

    # Language
    "lang_title": {"fa":"انتخاب زبان","en":"Choose language","ar":"اختر اللغة","tr":"Dil seç","ru":"Выберите язык","es":"Elige idioma","de":"Sprache wählen","fr":"Choisir la langue"},
    "lang_saved": {"fa":"✅ زبان ذخیره شد.","en":"✅ Language saved.","ar":"✅ تم حفظ اللغة.","tr":"✅ Dil kaydedildi.","ru":"✅ Язык сохранён.","es":"✅ Idioma guardado.","de":"✅ Sprache gespeichert.","fr":"✅ Langue enregistrée."},

    # TTS
    "tts_title":      {"fa":"تبدیل متن به صدا 🎧","en":"Text to Speech 🎧","ar":"تحويل النص إلى صوت 🎧","tr":"Metinden Sese 🎧","ru":"Текст в речь 🎧","es":"Texto a voz 🎧","de":"Text zu Sprache 🎧","fr":"Texte en voix 🎧"},
    "tts_prompt":     {"fa":"✨ <b>متن رو بفرست (هر کاراکتر = 1 Credit)</b>\n<b><a href='https://t.me/vexa_speech/171'>دموی صداها</a></b>","en":"✍️ Send your text (each character = 1 credit)","ar":"✍️ أرسل النص (كل حرف = 1 رصيد)","tr":"✍️ Metni gönder (her karakter = 1 kredi)","ru":"✍️ Отправьте текст (каждый символ = 1 кредит)","es":"✍️ Envía tu texto (cada carácter = 1 crédito)","de":"✍️ Sende deinen Text (jedes Zeichen = 1 Kredit)","fr":"✍️ Envoie ton texte (chaque caractère = 1 crédit)"},
    "tts_processing": {"fa":"👀 <b>در حال تبدیل...</b>","en":"⏳ Converting...","ar":"⏳ جارٍ التحويل...","tr":"⏳ Dönüştürülüyor...","ru":"⏳ Конвертация...","es":"⏳ Convirtiendo...","de":"⏳ Wird konvertiert...","fr":"⏳ Conversion..."},
    "tts_no_credit":  {"fa":"⚠️ <b>کردیت کافی نیست</b>\n<b>موجـودی شما : {credits} Credit </b>\n❔ میتونـی کردیت بخری یا متن رو کوتاه‌تر کنی /help","en":"⚠️ Not enough credits.","ar":"⚠️ الرصيد غير كافٍ.","tr":"⚠️ Yetersiz kredi.","ru":"⚠️ Недостаточно кредитов.","es":"⚠️ Créditos insuficientes.","de":"⚠️ Nicht genug Guthaben.","fr":"⚠️ Crédits insuffisants."},
    "tts_error":      {"fa":"⚠️ <b>خطا در تبدیل٫ دوباره تلاش کن</b>","en":"⚠️ Conversion failed. Try again.","ar":"⚠️ فشل التحويل. جرب مرة أخرى.","tr":"⚠️ Dönüşüm hatası. Tekrar dene.","ru":"⚠️ Ошибка конвертации. Попробуйте снова.","es":"⚠️ Error de conversión. Inténtalo de nuevo.","de":"⚠️ Umwandlung fehlgeschlagen. Versuch's nochmal.","fr":"⚠️ Échec de conversion. Réessayez."},

    # Profile
    "profile_title":  {"fa":"پروفایل","en":"Profile","ar":"الملف الشخصي","tr":"Profil","ru":"Профиль","es":"Perfil","de":"Profil","fr":"Profil"},
    "profile_body":   {"fa":"👤 <b>ID : <code>{uid}</code></b>\n💳 <b>Credit : {credits}</b>","en":"👤 ID: {uid}\n💳 Credits: {credits}","ar":"👤 المعرف: {uid}\n💳 الرصيد: {credits}","tr":"👤 ID: {uid}\n💳 Kredi: {credits}","ru":"👤 ID: {uid}\n💳 Кредиты: {credits}","es":"👤 ID: {uid}\n💳 Créditos: {credits}","de":"👤 ID: {uid}\n💳 Guthaben: {credits}","fr":"👤 ID : {uid}\n💳 Crédits : {credits}"},

    # Credit (Stars intro متن کوتاه)
    "credit_intro": {
        "fa": "<b>شارژ آنـی با Telegram Stars 🌟</b>",
        "en": "Top up via Telegram Stars",
        "ar": "اشحن عبر Telegram Stars",
        "tr": "Telegram Stars ile yükleme",
        "ru": "Пополнение через Telegram Stars",
        "es": "Recarga con Telegram Stars",
        "de": "Aufladen mit Telegram Stars",
        "fr": "Recharge via Telegram Stars"
    },

    # Invite
    "invite_title":   {"fa":"دعوت دوستان 🎁","en":"Invite Friends 🎁","ar":"دعوة الأصدقاء 🎁","tr":"Arkadaş Davet Et 🎁","ru":"Пригласить друзей 🎁","es":"Invitar amigos 🎁","de":"Freunde einladen 🎁","fr":"Inviter des amis 🎁"},
    "invite_body":    {"fa":"لینک دعوت شما:\n<code>{ref}</code>\n\n<b>به ازای هر دعوت : +{bonus} کردیت</b>","en":"Your invite link:\n{ref}\nPer invite: {bonus} credits","ar":"رابط دعوتك:\n{ref}\nلكل دعوة: {bonus} رصيد","tr":"Davet bağlantın:\n{ref}\nDavet başına: {bonus} kredi","ru":"Ваша ссылка:\n{ref}\nЗа приглашение: {bonus} кредитов","es":"Tu enlace de invitación:\n{ref}\nPor invitación: {bonus} créditos","de":"Dein Einladungslink:\n{ref}\nPro Einladung: {bonus} Guthaben","fr":"Ton lien d'invitation :\n{ref}\nPar invitation : {bonus} crédits"},
}

def t(key: str, lang: str) -> str:
    return LABELS.get(key, {}).get(lang, LABELS.get(key, {}).get("en", key))

LABELS.update({
    "back": {
        "fa": "🔙 بازگشت",
        "en": "🔙 Back",
        "ar": "🔙 رجوع",
        "tr": "🔙 Geri",
        "ru": "🔙 Назад",
        "es": "🔙 Atrás",
        "de": "🔙 Zurück",
        "fr": "🔙 Retour",
    }
})
# ——— افزودن متن‌های پرداخت/فاکتور ———
LABELS.update({
    "credit_invoice_title": {
        "fa": "Vexa — خرید کردیت",
        "en": "Vexa — Buy Credits",
        "ar": "Vexa — شراء الرصيد",
        "tr": "Vexa — Kredi Satın Al",
        "ru": "Vexa — Покупка кредитов",
        "es": "Vexa — Comprar créditos",
        "de": "Vexa — Guthaben kaufen",
        "fr": "Vexa — Acheter des crédits",
    },
    "credit_invoice_desc": {
        "fa": "شارژ موجودی با Telegram Stars.",
        "en": "Top up your balance with Telegram Stars.",
        "ar": "اشحن رصيدك عبر Telegram Stars.",
        "tr": "Bakiyeni Telegram Stars ile doldur.",
        "ru": "Пополните баланс через Telegram Stars.",
        "es": "Recarga tu saldo con Telegram Stars.",
        "de": "Lade dein Guthaben mit Telegram Stars auf.",
        "fr": "Recharge ton solde avec Telegram Stars.",
    },
    "credit_pay_success": {
        "fa": "✅ پرداخت موفق: ⭐{stars}\n🎉 {credits} کردیت اضافه شد.\n💳 موجودی فعلی: <b>{balance}</b>",
        "en": "✅ Payment successful: ⭐{stars}\n🎉 Added {credits} credits.\n💳 Current balance: <b>{balance}</b>",
        "ar": "✅ تم الدفع: ⭐{stars}\n🎉 تمت إضافة {credits} رصيدًا.\n💳 الرصيد الحالي: <b>{balance}</b>",
        "tr": "✅ Ödeme başarılı: ⭐{stars}\n🎉 {credits} kredi eklendi.\n💳 Güncel bakiye: <b>{balance}</b>",
        "ru": "✅ Оплата прошла: ⭐{stars}\n🎉 Добавлено {credits} кредитов.\n💳 Текущий баланс: <b>{balance}</b>",
        "es": "✅ Pago exitoso: ⭐{stars}\n🎉 {credits} créditos añadidos.\n💳 Saldo actual: <b>{balance}</b>",
        "de": "✅ Zahlung erfolgreich: ⭐{stars}\n🎉 {credits} Guthaben gutgeschrieben.\n💳 Aktueller Stand: <b>{balance}</b>",
        "fr": "✅ Paiement réussi : ⭐{stars}\n🎉 {credits} crédits ajoutés.\n💳 Solde actuel : <b>{balance}</b>",
    },
})
LABELS.update({
    "ref_welcome": {
        "fa": "🎉 <b>خوش اومدی! {credits} کردیت رایگان گرفتی</b>",
        "en": "🎉 Welcome! You received {credits} free credits.",
        "ar": "🎉 أهلاً! حصلت على {credits} رصيد مجاني.",
        "tr": "🎉 Hoş geldin! {credits} ücretsiz kredi kazandın.",
        "ru": "🎉 Добро пожаловать! Вы получили {credits} бесплатных кредитов.",
        "es": "🎉 ¡Bienvenido! Recibiste {credits} créditos gratis.",
        "de": "🎉 Willkommen! Du hast {credits} Gratis-Guthaben erhalten.",
        "fr": "🎉 Bienvenue ! Tu as reçu {credits} crédits gratuits.",
    },
    "ref_notify": {
        "fa": "👥 یک کاربر با لینک تو عضو شد\n🎁 <b>{credits}</b> کردیت بهت اضافه شد",
        "en": "👥 A user joined with your invite link.\n🎁 You got {credits} bonus credits.",
        "ar": "👥 انضم مستخدم عبر رابط دعوتك.\n🎁 حصلت على {credits} رصيد إضافي.",
        "tr": "👥 Bir kullanıcı davet linkinle katıldı.\n🎁 {credits} bonus kredi kazandın.",
        "ru": "👥 Пользователь присоединился по вашей ссылке.\n🎁 Вы получили {credits} бонусных кредитов.",
        "es": "👥 Un usuario se unió con tu enlace.\n🎁 Recibiste {credits} créditos de bono.",
        "de": "👥 Ein Nutzer ist mit deinem Link beigetreten.\n🎁 Du hast {credits} Bonus-Guthaben erhalten.",
        "fr": "👥 Un utilisateur a rejoint via ton lien.\n🎁 Tu as reçu {credits} crédits bonus.",
    },
})
