# modules/i18n.py
LABELS = {
    # Home
    "home_title": {"fa":"منوی اصلی","en":"Main Menu","ar":"القائمة الرئيسية","tr":"Ana Menü","ru":"Главное меню","es":"Menú principal","de":"Hauptmenü","fr":"Menu principal"},
    "home_body":  {"fa":"یکی از گزینه‌های زیر را انتخاب کنید:","en":"Choose an option:","ar":"اختر خياراً:","tr":"Bir seçenek seçin:","ru":"Выберите опцию:","es":"Elige una opción:","de":"Wähle eine Option:","fr":"Choisissez une option :"},
    "btn_tts":    {"fa":"تبدیل متن به صدا 🎧","en":"Text to Speech 🎧","ar":"تحويل النص إلى صوت 🎧","tr":"Metinden Sese 🎧","ru":"Текст в речь 🎧","es":"Texto a voz 🎧","de":"Text zu Sprache 🎧","fr":"Texte en voix 🎧"},
    "btn_profile":{"fa":"پروفایل 🙋🏼‍♂️","en":"Profile 🙋🏼‍♂️","ar":"الملف الشخصي 🙋🏼‍♂️","tr":"Profil 🙋🏼‍♂️","ru":"Профиль 🙋🏼‍♂️","es":"Perfil 🙋🏼‍♂️","de":"Profil 🙋🏼‍♂️","fr":"Profil 🙋🏼‍♂️"},
    "btn_credit": {"fa":"خرید Credit 🛒","en":"Buy Credit 🛒","ar":"شراء الرصيد 🛒","tr":"Kredi Satın Al 🛒","ru":"Купить кредит 🛒","es":"Comprar crédito 🛒","de":"Guthaben kaufen 🛒","fr":"Acheter du crédit 🛒"},
    "btn_invite": {"fa":"دعوت دوستان 🎁","en":"Invite Friends 🎁","ar":"دعوة الأصدقاء 🎁","tr":"Arkadaş Davet Et 🎁","ru":"Пригласить друзей 🎁","es":"Invitar amigos 🎁","de":"Freunde einladen 🎁","fr":"Inviter des amis 🎁"},
    "btn_lang":   {"fa":"Language 📚","en":"Language 📚","ar":"اللغة 📚","tr":"Dil 📚","ru":"Язык 📚","es":"Idioma 📚","de":"Sprache 📚","fr":"Langue 📚"},

    # Language
    "lang_title": {"fa":"انتخاب زبان","en":"Choose language","ar":"اختر اللغة","tr":"Dil seç","ru":"Выберите язык","es":"Elige idioma","de":"Sprache wählen","fr":"Choisir la langue"},
    "lang_saved": {"fa":"✅ زبان ذخیره شد.","en":"✅ Language saved.","ar":"✅ تم حفظ اللغة.","tr":"✅ Dil kaydedildi.","ru":"✅ Язык сохранён.","es":"✅ Idioma guardado.","de":"✅ Sprache gespeichert.","fr":"✅ Langue enregistrée."},

    # TTS
    "tts_title":      {"fa":"تبدیل متن به صدا 🎧","en":"Text to Speech 🎧","ar":"تحويل النص إلى صوت 🎧","tr":"Metinden Sese 🎧","ru":"Текст в речь 🎧","es":"Texto a voz 🎧","de":"Text zu Sprache 🎧","fr":"Texte en voix 🎧"},
    "tts_prompt":     {"fa":"✨ <b>متن رو بفرست (هر کاراکتر = 1 Credit)</b>\n<b><a href='https://t.me/vexa_speech/171'>دموی صداها</a></b>","en":"✍️ Send your text (each character = 1 credit)","ar":"✍️ أرسل النص (كل حرف = 1 رصيد)","tr":"✍️ Metni gönder (her karakter = 1 kredi)","ru":"✍️ Отправьте текст (каждый символ = 1 кредит)","es":"✍️ Envía tu texto (cada carácter = 1 crédito)","de":"✍️ Sende deinen Text (jedes Zeichen = 1 Kredit)","fr":"✍️ Envoie ton texte (chaque caractère = 1 crédit)"},
    "tts_processing": {"fa":"👀 <b>در حال تبدیل...</b>","en":"⏳ Converting...","ar":"⏳ جارٍ التحويل...","tr":"⏳ Dönüştürülüyor...","ru":"⏳ Конвертация...","es":"⏳ Convirtiendo...","de":"⏳ Wird konvertiert...","fr":"⏳ Conversion..."},
    "tts_no_credit":  {"fa":"⚠️ <b>موجودی کافی نیست</b>","en":"⚠️ Not enough credits.","ar":"⚠️ الرصيد غير كافٍ.","tr":"⚠️ Yetersiz kredi.","ru":"⚠️ Недостаточно кредитов.","es":"⚠️ Créditos insuficientes.","de":"⚠️ Nicht genug Guthaben.","fr":"⚠️ Crédits insuffisants."},
    "tts_error":      {"fa":"⚠️ خطا در تبدیل. دوباره تلاش کن.","en":"⚠️ Conversion failed. Try again.","ar":"⚠️ فشل التحويل. جرب مرة أخرى.","tr":"⚠️ Dönüşüm hatası. Tekrar dene.","ru":"⚠️ Ошибка конвертации. Попробуйте снова.","es":"⚠️ Error de conversión. Inténtalo de nuevo.","de":"⚠️ Umwandlung fehlgeschlagen. Versuch's nochmal.","fr":"⚠️ Échec de conversion. Réessayez."},

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

# ——— Credit Purchase Section ———
LABELS.update({
    "credit_title": {
        "fa": "خرید کردیت",
        "en": "Buy Credits",
        "ar": "شراء الرصيد", 
        "tr": "Kredi Satın Al",
        "ru": "Купить кредит",
        "es": "Comprar crédito",
        "de": "Guthaben kaufen",
        "fr": "Acheter du crédit",
    },
    "credit_header": {
        "fa": "برای استفاده از ربات، کردیت لازم دارید.\nیکی از بسته‌های زیر را انتخاب کنید:",
        "en": "To use the bot, you need credits.\nChoose one of the packages below:",
        "ar": "لاستخدام البوت، تحتاج إلى رصيد.\nاختر إحدى الحزم أدناه:",
        "tr": "Botu kullanmak için krediye ihtiyacınız var.\nAşağıdaki paketlerden birini seçin:",
        "ru": "Для использования бота вам нужны кредиты.\nВыберите один из пакетов ниже:",
        "es": "Para usar el bot, necesitas créditos.\nElige uno de los paquetes a continuación:",
        "de": "Um den Bot zu nutzen, benötigen Sie Guthaben.\nWählen Sie eines der folgenden Pakete:",
        "fr": "Pour utiliser le bot, vous avez besoin de crédits.\nChoisissez l'un des forfaits ci-dessous :",
    },
    "pay_stars_btn": {
        "fa": "خرید با Telegram Stars ⭐️",
        "en": "Buy with Telegram Stars ⭐️",
        "ar": "شراء عبر Telegram Stars ⭐️",
        "tr": "Telegram Stars ile satın al ⭐️",
        "ru": "Купить за Telegram Stars ⭐️",
        "es": "Comprar con Telegram Stars ⭐️",
        "de": "Mit Telegram Stars kaufen ⭐️",
        "fr": "Acheter avec Telegram Stars ⭐️",
    },
    "pay_rial_btn": {
        "fa": "پرداخت به تومان",
        "en": "Pay in Toman", 
        "ar": "دفع بالتومان",
        "tr": "Toman ile öde",
        "ru": "Оплата в томанах",
        "es": "Pagar en Toman",
        "de": "In Toman bezahlen",
        "fr": "Payer en Toman",
    },
    "pay_rial_title": {
        "fa": "پرداخت به تومـان – انتخاب پلن",
        "en": "Toman Payment – Select Plan",
        "ar": "دفع بالتومان – اختيار الخطة",
        "tr": "Toman Ödemesi – Plan Seç",
        "ru": "Оплата томанами – Выбор плана",
        "es": "Pago en Toman – Seleccionar plan",
        "de": "Toman-Zahlung – Plan auswählen",
        "fr": "Paiement en Toman – Sélectionner un plan",
    },
    "pay_rial_plans_header": {
        "fa": "یکی از پلن‌های زیر را انتخاب کن:",
        "en": "Choose one of the plans below:",
        "ar": "اختر إحدى الخطط أدناه:",
        "tr": "Aşağıdaki planlardan birini seçin:",
        "ru": "Выберите один из планов ниже:",
        "es": "Elige uno de los planes a continuación:",
        "de": "Wählen Sie einen der folgenden Pläne:",
        "fr": "Choisissez l'un des plans ci-dessous :",
    },
    "pay_rial_instant": {
        "fa": "پرداخت فوری (کارت‌به‌کارت)",
        "en": "Instant Payment (Card to Card)",
        "ar": "دفع فوري (بطاقة إلى بطاقة)",
        "tr": "Anında Ödeme (Kart-Kart)",
        "ru": "Мгновенный платёж (карта на карту)",
        "es": "Pago instantáneo (tarjeta a tarjeta)",
        "de": "Sofortzahlung (Karte zu Karte)",
        "fr": "Paiement instantané (carte à carte)",
    },
    "stars_menu_title": {
        "fa": "⭐️ خرید به صورت آنـی با Telegram Stars",
        "en": "⭐️ Instant purchase with Telegram Stars",
        "ar": "⭐️ شراء فوري عبر Telegram Stars",
        "tr": "⭐️ Telegram Stars ile anında satın alma",
        "ru": "⭐️ Мгновенная покупка за Telegram Stars",
        "es": "⭐️ Compra instantánea con Telegram Stars",
        "de": "⭐️ Sofortkauf mit Telegram Stars",
        "fr": "⭐️ Achat instantané avec Telegram Stars",
    },
    "stars_menu_header": {
        "fa": "یکی از بسته‌های زیر را انتخاب کنید:",
        "en": "Choose one of the packages below:",
        "ar": "اختر إحدى الحزم أدناه:",
        "tr": "Aşağıdaki paketlerden birini seçin:",
        "ru": "Выберите один из пакетов ниже:",
        "es": "Elige uno de los paquetes a continuación:",
        "de": "Wählen Sie eines der folgenden Pakete:",
        "fr": "Choisissez l'un des forfaits ci-dessous :",
    },
    "instant_pay_instruct": {
        "fa": "💱 <b>پرداخت فوری (کارت‌به‌کارت)</b>\nشماره کارت: <code>{card}</code>\n\n• مطابق یکی از قیمت‌ها کارت‌به‌کارت کن.\n• سپس <b>تصویر رسید</b> را همین‌جا ارسال کن.\n\n✅ پس از پرداخت، کردیت شما کمتر از ۵ دقیقه به حساب کاربری‌تون اضافه میشه",
        "en": "💱 <b>Instant Payment (Card to Card)</b>\nCard number: <code>{card}</code>\n\n• Transfer according to one of the prices.\n• Then send the <b>receipt image</b> here.\n\n✅ After payment, your credit will be added to your account in less than 5 minutes",
        "ar": "💱 <b>دفع فوري (بطاقة إلى بطاقة)</b>\nرقم البطاقة: <code>{card}</code>\n\n• احول وفقاً لأحد الأسعار.\n• ثم أرسل <b>صورة الإيصال</b> هنا.\n\n✅ بعد الدفع، سيتم إضافة رصيدك إلى حسابك في أقل من 5 دقائق",
        "tr": "💱 <b>Anında Ödeme (Kart-Kart)</b>\nKart numarası: <code>{card}</code>\n\n• Fiyatlardan birine göre transfer yapın.\n• Sonra <b>makbuz resmini</b> buraya gönderin.\n\n✅ Ödeme sonrası krediniz 5 dakikadan az bir sürede hesabınıza eklenecek",
        "ru": "💱 <b>Мгновенный платёж (карта на карту)</b>\nНомер карты: <code>{card}</code>\n\n• Переведите согласно одной из цен.\n• Затем отправьте <b>изображение чека</b> сюда.\n\n✅ После оплаты ваш кредит будет добавлен на аккаунт менее чем за 5 минут",
        "es": "💱 <b>Pago instantáneo (tarjeta a tarjeta)</b>\nNúmero de tarjeta: <code>{card}</code>\n\n• Transfiere según uno de los precios.\n• Luego envía la <b>imagen del recibo</b> aquí.\n\n✅ Después del pago, tu crédito se agregará a tu cuenta en menos de 5 minutos",
        "de": "💱 <b>Sofortzahlung (Karte zu Karte)</b>\nKartennummer: <code>{card}</code>\n\n• Überweisen Sie entsprechend einem der Preise.\n• Senden Sie dann das <b>Quittungsbild</b> hierher.\n\n✅ Nach der Zahlung wird Ihr Guthaben in weniger als 5 Minuten Ihrem Konto gutgeschrieben",
        "fr": "💱 <b>Paiement instantané (carte à carte)</b>\nNuméro de carte : <code>{card}</code>\n\n• Transférez selon l'un des prix.\n• Puis envoyez l'<b>image du reçu</b> ici.\n\n✅ Après le paiement, votre crédit sera ajouté à votre compte en moins de 5 minutes",
    },
    "waiting_confirm": {
        "fa": "✅ رسید دریافت شد.\n⏳ لطفاً منتظر تایید باش.",
        "en": "✅ Receipt received.\n⏳ Please wait for confirmation.",
        "ar": "✅ تم استلام الإيصال.\n⏳ يرجى انتظار التأكيد.",
        "tr": "✅ Makbuz alındı.\n⏳ Lütfen onay bekleyin.",
        "ru": "✅ Чек получен.\n⏳ Пожалуйста, дождитесь подтверждения.",
        "es": "✅ Recibo recibido.\n⏳ Por favor espera la confirmación.",
        "de": "✅ Quittung erhalten.\n⏳ Bitte warten Sie auf die Bestätigung.",
        "fr": "✅ Reçu reçu.\n⏳ Veuillez attendre la confirmation.",
    },
    "cancel_btn": {
        "fa": "لغو ❌",
        "en": "Cancel ❌",
        "ar": "إلغاء ❌",
        "tr": "İptal ❌",
        "ru": "Отмена ❌",
        "es": "Cancelar ❌",
        "de": "Abbrechen ❌",
        "fr": "Annuler ❌",
    },
})

LABELS.update({
    "ref_welcome": {
        "fa": "🎉 <b>خوش آمدی! {credits} کردیت رایگان گرفتی.</b>",
        "en": "🎉 Welcome! You received {credits} free credits.",
        "ar": "🎉 أهلاً! حصلت على {credits} رصيد مجاني.",
        "tr": "🎉 Hoş geldin! {credits} ücretsiz kredi kazandın.",
        "ru": "🎉 Добро пожаловать! Вы получили {credits} бесплатных кредитов.",
        "es": "🎉 ¡Bienvenido! Recibiste {credits} créditos gratis.",
        "de": "🎉 Willkommen! Du hast {credits} Gratis-Guthaben erhalten.",
        "fr": "🎉 Bienvenue ! Tu as reçu {credits} crédits gratuits.",
    },
    "ref_notify": {
        "fa": "👥 یک کاربر با لینک تو عضو شد.\n🎁 <b>{credits}</b> کردیت بهت اضافه شد.",
        "en": "👥 A user joined with your invite link.\n🎁 You got {credits} bonus credits.",
        "ar": "👥 انضم مستخدم عبر رابط دعوتك.\n🎁 حصلت على {credits} رصيد إضافي.",
        "tr": "👥 Bir kullanıcı davet linkinle katıldı.\n🎁 {credits} bonus kredi kazandın.",
        "ru": "👥 Пользователь присоединился по вашей ссылке.\n🎁 Вы получили {credits} бонусных кредитов.",
        "es": "👥 Un usuario se unió con tu enlace.\n🎁 Recibiste {credits} créditos de bono.",
        "de": "👥 Ein Nutzer ist mit deinem Link beigetreten.\n🎁 Du hast {credits} Bonus-Guthaben erhalten.",
        "fr": "👥 Un utilisateur a rejoint via ton lien.\n🎁 Tu as reçu {credits} crédits bonus.",
    },
})
