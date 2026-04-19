import type { OwnerNotificationService, TelegramWebhookService } from "./user-services";
import type { BotConversationState, UserStateRepository } from "../storage/user-state-repository";
import type { ApiTokenService, CreditService, GptHistoryService, UserService } from "./user-services";

interface TelegramUser {
  id: number;
  username?: string;
  first_name?: string;
}

export interface TelegramWebhookUpdate {
  update_id?: number;
  pre_checkout_query?: { id: string; from?: TelegramUser };
  message?: {
    message_id?: number;
    text?: string;
    caption?: string;
    photo?: Array<{ file_id: string }>;
    voice?: { file_id: string };
    audio?: { file_id: string };
    document?: { file_id: string; mime_type?: string };
    successful_payment?: { invoice_payload?: string; total_amount?: number; telegram_payment_charge_id?: string };
    from?: TelegramUser;
    chat?: { id: number };
  };
  callback_query?: {
    id: string;
    data?: string;
    from?: TelegramUser;
    message?: { message_id?: number; chat?: { id: number }; caption?: string };
  };
}

interface TelegramBotFlowDeps {
  botToken: string;
  botUsername?: string;
  forceSubMode?: string;
  forceSubChannel?: string;
  forceSubInstagramUrl?: string;
  welcomeAudioFileId?: string;
  welcomeAudioKind?: "audio" | "voice" | "document";
  ownerTelegramChatId?: string;
  cardNumber?: string;
  ttsDemoAudiosJson?: string;
  users: UserService;
  credits: CreditService;
  tokens: ApiTokenService;
  history: GptHistoryService;
  userState: UserStateRepository;
  telegramEvents: TelegramWebhookService;
  ownerNotifications: OwnerNotificationService;
}

type ParseMode = "Markdown" | "HTML";

type InlineKeyboard = {
  inline_keyboard: Array<Array<{ text: string; callback_data?: string; url?: string }>>;
};

type ReplyKeyboard = {
  keyboard: Array<Array<{ text: string }>>;
  resize_keyboard?: boolean;
  one_time_keyboard?: boolean;
};

const nowTs = () => Math.floor(Date.now() / 1000);
const DAILY_REWARD_SECONDS = 24 * 60 * 60;
const ONBOARDING_DAILY_BONUS_DELAY = 15;
const ONBOARDING_DAILY_BONUS_UNLOCK_DELAY = 10 * 60;
const LOW_CREDIT_DELAY_SECONDS = 15;
const LOW_CREDIT_THRESHOLD = 15;
const REFERRAL_BONUS = 30;
const TTS_DEMO_AUTO_DELETE_SECONDS = 50;
const SORA2_COST = 259;
const SORA2_QUEUE_START = 22;
const LANGS: Array<{ label: string; code: string }> = [
  { label: "English", code: "en" },
  { label: "فارسی", code: "fa" },
  { label: "العربية", code: "ar" },
  { label: "Türkçe", code: "tr" },
  { label: "Русский", code: "ru" },
  { label: "Español", code: "es" },
  { label: "Deutsch", code: "de" },
  { label: "Français", code: "fr" },
];


const I18N: Record<string, Record<string, string>> = {
  home_title: { fa: "/help   منوی اصلی", en: "Main Menu", ar: "القائمة الرئيسية", tr: "Ana Menü", ru: "Главное меню", es: "Menú principal", de: "Hauptmenü", fr: "Menu principal" },
  home_body: { fa: "یکی از گزینه‌های زیر را انتخاب کنید:", en: "Choose an option:", ar: "اختر خياراً:", tr: "Bir seçenek seçin:", ru: "Выберите опцию:", es: "Elige una opción:", de: "Wähle eine Option:", fr: "Choisissez une option :" },
  btn_profile: { fa: "موجودی شما", en: "Your Balance", ar: "رصيدك", tr: "Bakiyeniz", ru: "Ваш баланс", es: "Tu saldo", de: "Dein Guthaben", fr: "Ton solde" },
  btn_credit: { fa: "خرید کردیـت 🛒", en: "Buy Credit 🛒", ar: "شراء الرصيد 🛒", tr: "Kredi Satın Al 🛒", ru: "Купить кредит 🛒", es: "Comprar crédito 🛒", de: "Guthaben kaufen 🛒", fr: "Acheter du crédit 🛒" },
  btn_tts: { fa: "تبدیل متن به صدا 🎧", en: "Text to Speech 🎧", ar: "تحويل النص إلى صوت 🎧", tr: "Metinden Sese 🎧", ru: "Текст в речь 🎧", es: "Texto a voz 🎧", de: "Text zu Sprache 🎧", fr: "Texte en voix 🎧" },
  btn_clone: { fa: "ساخت صدای شخصی 🧬", en: "Voice Clone 🧬", ar: "إنشاء صوت شخصي 🧬", tr: "Kişisel Ses Oluştur 🧬", ru: "Личный голос 🧬", es: "Voz personal 🧬", de: "Eigene Stimme 🧬", fr: "Voix perso 🧬" },
  btn_lang: { fa: "Language 📚", en: "Language 📚", ar: "اللغة 📚", tr: "Dil 📚", ru: "Язык 📚", es: "Idioma 📚", de: "Sprache 📚", fr: "Langue 📚" },
  btn_invite: { fa: "🎁", en: "🎁", ar: "دعوة الأصدقاء 🎁", tr: "🎁", ru: "🎁", es: "🎁", de: "🎁", fr: "🎁" },
  back: { fa: "🔙 بازگشت", en: "🔙 Back", ar: "🔙 رجوع", tr: "🔙 Geri", ru: "🔙 Назад", es: "🔙 Volver", de: "🔙 Zurück", fr: "🔙 Retour" },
  home_back_to_menu: { fa: "🏠 منوی اصلی", en: "🏠 Main menu", ar: "🏠 القائمة الرئيسية", tr: "🏠 Ana menü", ru: "🏠 Главное меню", es: "🏠 Menú principal", de: "🏠 Hauptmenü", fr: "🏠 Menu principal" },
  lang_title: { fa: "انتخاب زبان", en: "Choose language", ar: "اختر اللغة", tr: "Dil seç", ru: "Выберите язык", es: "Elige idioma", de: "Sprache wählen", fr: "Choisir la langue" },
  lang_hint: { fa: "یکی از زبان‌های زیر را انتخاب کن.", en: "Select one of the languages below.", ar: "اختر إحدى اللغات أدناه.", tr: "Aşağıdaki dillerden birini seç.", ru: "Выберите один из языков ниже.", es: "Elige uno de los idiomas de abajo.", de: "Wähle eine der folgenden Sprachen.", fr: "Choisis l'une des langues ci-dessous." },
  lang_saved: { fa: "✅ زبان ذخیره شد.", en: "✅ Language saved.", ar: "✅ تم حفظ اللغة.", tr: "✅ Dil kaydedildi.", ru: "✅ Язык сохранён.", es: "✅ Idioma guardado.", de: "✅ Sprache gespeichert.", fr: "✅ Langue enregistrée." },
  tts_title: { fa: "تبدیل متن به صدا 🎧", en: "AI Text to Speech ", ar: "تحويل النص إلى صوت 🎧", tr: "Metinden Sese 🎧", ru: "Текст в речь 🎧", es: "Texto a voz 🎧", de: "Text zu Sprache 🎧", fr: "Texte en voix 🎧" },
  tts_prompt: { fa: "✨ <b>متن رو بفرست (هر کاراکتر = {credit} Credit)</b>", en: "✍🏼 Send your text (1 character = {credit} credit)", ar: "✍🏼 أرسل النص (كل حرف = {credit} رصيد)", tr: "✍🏼 Metni gönder (her karakter = {credit} kredi)", ru: "✍🏼 Отправьте текст (каждый символ = {credit} кредит)", es: "✍🏼 Envía tu texto (cada carácter = {credit} crédito)", de: "✍🏼 Sende deinen Text (jedes Zeichen = {credit} Kredit)", fr: "✍🏼 Envoie ton texte (chaque caractère = {credit} crédit)" },
  tts_demo: { fa: "▶︎ دمو", en: "▶︎ Demo", ar: "▶︎ عرض تجريبي", tr: "▶︎ Demo", ru: "▶︎ Демо", es: "▶︎ Demo", de: "▶︎ Demo", fr: "▶︎ Démo" },
  tts_demo_caption: { fa: "🎧 دمو: {voice}\n⏳ حذف خودکار پس از {seconds} ثانیه", en: "🎧 Demo: {voice}\n⏳ Auto delete in {seconds} seconds", ar: "🎧 عرض تجريبي: {voice}\n⏳ الحذف التلقائي خلال {seconds} ثانية", tr: "🎧 Demo: {voice}\n⏳ Otomatik silme {seconds} saniye içinde", ru: "🎧 Демо: {voice}\n⏳ Автоудаление через {seconds} секунд", es: "🎧 Demo: {voice}\n⏳ Eliminación automática en {seconds} segundos", de: "🎧 Demo: {voice}\n⏳ Automatisches Löschen in {seconds} Sekunden", fr: "🎧 Démo : {voice}\n⏳ Suppression automatique dans {seconds} secondes" },
  tts_demo_wait: { fa: "⏳ دموی این صدا ارسال شده. لطفاً تا حذف شدنش صبر کنید.", en: "⏳ Demo already sent. Please wait for it to be deleted.", ar: "⏳ تم إرسال العرض التجريبي بالفعل. يرجى الانتظار حتى يتم حذفه.", tr: "⏳ Demo zaten gönderildi. Silinmesini bekleyin.", ru: "⏳ Демо уже отправлено. Подождите, пока оно будет удалено.", es: "⏳ La demo ya fue enviada. Espera a que se elimine.", de: "⏳ Demo bereits gesendet. Bitte warten, bis sie gelöscht wird.", fr: "⏳ Démo déjà envoyée. Merci d’attendre sa suppression." },
  tts_demo_missing: { fa: "❌ دموی این صدا هنوز تنظیم نشده است.", en: "❌ Demo for this voice is not available yet.", ar: "❌ العرض التجريبي لهذا الصوت غير متوفر بعد.", tr: "❌ Bu ses için demo henüz mevcut değil.", ru: "❌ Демоверсия для этого голоса пока недоступна.", es: "❌ La demo de esta voz aún no está disponible.", de: "❌ Für diese Stimme ist noch keine Demo verfügbar.", fr: "❌ La démo de cette voix n'est pas encore disponible." },
  tts_output_saved: { fa: "✅ خروجی روی <b>{mode}</b> تنظیم شد.", en: "✅ Output set to <b>{mode}</b>.", ar: "✅ تم ضبط المخرج على <b>{mode}</b>.", tr: "✅ Çıktı <b>{mode}</b> olarak ayarlandı.", ru: "✅ Формат вывода: <b>{mode}</b>.", es: "✅ Salida configurada en <b>{mode}</b>.", de: "✅ Ausgabe auf <b>{mode}</b> gesetzt.", fr: "✅ Sortie définie sur <b>{mode}</b>." },
  tts_request_saved: { fa: "✅ متن صوتی ثبت شد.\n\n🎙 صدا: <b>{voice}</b>\n📦 خروجی: <b>{output}</b>", en: "✅ Your TTS text has been queued.\n\n🎙 Voice: <b>{voice}</b>\n📦 Output: <b>{output}</b>", ar: "✅ تم تسجيل النص الصوتي.\n\n🎙 الصوت: <b>{voice}</b>\n📦 المخرج: <b>{output}</b>", tr: "✅ TTS metnin sıraya alındı.\n\n🎙 Ses: <b>{voice}</b>\n📦 Çıktı: <b>{output}</b>", ru: "✅ Текст для TTS сохранён.\n\n🎙 Голос: <b>{voice}</b>\n📦 Вывод: <b>{output}</b>", es: "✅ Tu texto TTS fue registrado.\n\n🎙 Voz: <b>{voice}</b>\n📦 Salida: <b>{output}</b>", de: "✅ Dein TTS-Text wurde übernommen.\n\n🎙 Stimme: <b>{voice}</b>\n📦 Ausgabe: <b>{output}</b>", fr: "✅ Ton texte TTS a été pris en compte.\n\n🎙 Voix : <b>{voice}</b>\n📦 Sortie : <b>{output}</b>" },
  tts_next: { fa: "بعدی ➜", en: "Next ➜", ar: "التالي ➜", tr: "Sonraki ➜", ru: "Далее ➜", es: "Siguiente ➜", de: "Weiter ➜", fr: "Suivant ➜" },
  tts_prev: { fa: "⬅︎ قبل", en: "⬅︎ Previous", ar: "⬅︎ السابق", tr: "⬅︎ Önceki", ru: "⬅︎ Назад", es: "⬅︎ Anterior", de: "⬅︎ Zurück", fr: "⬅︎ Précédent" },
  tts_output_mp3: { fa: "MP3 📁", en: "MP3 📁", ar: "MP3 📁", tr: "MP3 📁", ru: "MP3 📁", es: "MP3 📁", de: "MP3 📁", fr: "MP3 📁" },
  tts_output_voice: { fa: "Voice 🎙️", en: "Voice 🎙️", ar: "Voice 🎙️", tr: "Voice 🎙️", ru: "Voice 🎙️", es: "Voice 🎙️", de: "Voice 🎙️", fr: "Voice 🎙️" },
  credit_title: { fa: "خرید کردیت", en: "Buy credits", ar: "شراء الرصيد", tr: "Kredi satın al", ru: "Покупка кредитов", es: "Comprar créditos", de: "Credits kaufen", fr: "Acheter des crédits" },
  credit_header: { fa: "برای استفاده از ربات، کردیت لازم دارید", en: "Pick a package below to top up your balance.", ar: "اختر إحدى الباقات أدناه لشحن رصيدك.", tr: "Bakiyeni doldurmak için aşağıdaki paketlerden birini seç.", ru: "Выберите один из пакетов ниже, чтобы пополнить баланс.", es: "Elige uno de los paquetes para recargar tu saldo.", de: "Wähle eines der folgenden Pakete, um dein Guthaben aufzuladen.", fr: "Choisis l'un des packs ci-dessous pour recharger ton solde." },
  credit_pay_stars_btn: { fa: "خرید با Telegram Stars 🌟", en: "Buy with Telegram Stars 🌟", ar: "اشترِ عبر Telegram Stars 🌟", tr: "Telegram Stars ile satın al 🌟", ru: "Купить через Telegram Stars 🌟", es: "Comprar con Telegram Stars 🌟", de: "Mit Telegram Stars kaufen 🌟", fr: "Acheter avec Telegram Stars 🌟" },
  credit_pay_rial_btn: { fa: "پرداخت به تومان", en: "Pay in Toman", ar: "الدفع بالتومان", tr: "Toman ile öde", ru: "Оплата в томанах", es: "Pagar en tomanes", de: "In Toman zahlen", fr: "Payer en toman" },
  credit_cancel: { fa: "لغو ❌", en: "Cancel ❌", ar: "إلغاء ❌", tr: "İptal ❌", ru: "Отмена ❌", es: "Cancelar ❌", de: "Abbrechen ❌", fr: "Annuler ❌" },
  credit_unavailable: { fa: "پرداخت به تومان فقط برای کاربران فارسی فعال است.", en: "Payments in tomans are only available in the Persian language.", ar: "الدفع بالعملة المحلية متاح فقط باللغة الفارسية.", tr: "Toman ile ödeme yalnızca Farsça dilinde kullanılabilir.", ru: "Оплата в туманах доступна только для персидского языка.", es: "El pago en toman solo está disponible en el idioma persa.", de: "Zahlungen in Toman sind nur auf Persisch verfügbar.", fr: "Le paiement en tomans est disponible uniquement en persan." },
  credit_stars_menu: { fa: "🌟 شارژ آنی با Telegram Stars\n\nیکی از بسته‌های زیر را انتخاب کن:", en: "🌟 Instant top-up with Telegram Stars\n\nPick one of the packages below:", ar: "🌟 شحن فوري عبر Telegram Stars\n\nاختر إحدى الباقات أدناه:", tr: "🌟 Telegram Stars ile anında yükleme\n\nAşağıdaki paketlerden birini seç:", ru: "🌟 Мгновенное пополнение через Telegram Stars\n\nВыберите один из пакетов ниже:", es: "🌟 Recarga instantánea con Telegram Stars\n\nElige uno de los paquetes a continuación:", de: "🌟 Sofort aufladen mit Telegram Stars\n\nWähle eines der Pakete unten:", fr: "🌟 Recharge instantanée via Telegram Stars\n\nChoisis l'un des packs ci-dessous :" },
  credit_invoice_label: { fa: "{credits} کردیت", en: "{credits} credits", ar: "{credits} رصيداً", tr: "{credits} kredi", ru: "{credits} кредитов", es: "{credits} créditos", de: "{credits} Guthaben", fr: "{credits} crédits" },
  credit_invoice_title: { fa: "Vexa — خرید کردیت", en: "Vexa — Buy Credits", ar: "Vexa — شراء الرصيد", tr: "Vexa — Kredi Satın Al", ru: "Vexa — Покупка кредитов", es: "Vexa — Comprar créditos", de: "Vexa — Guthaben kaufen", fr: "Vexa — Acheter des crédits" },
  credit_invoice_desc: { fa: "شارژ موجودی با Telegram Stars.", en: "Top up your balance with Telegram Stars.", ar: "اشحن رصيدك عبر Telegram Stars.", tr: "Bakiyeni Telegram Stars ile doldur.", ru: "Пополните баланс через Telegram Stars.", es: "Recarga tu saldo con Telegram Stars.", de: "Lade dein Guthaben mit Telegram Stars auf.", fr: "Recharge ton solde avec Telegram Stars." },
  credit_pay_success: { fa: "✅ پرداخت موفق: ⭐{stars}\n🎉 {credits} کردیت اضافه شد.\n💳 موجودی فعلی: <b>{balance}</b>", en: "✅ Payment successful: ⭐{stars}\n🎉 Added {credits} credits.\n💳 Current balance: <b>{balance}</b>", ar: "✅ تم الدفع: ⭐{stars}\n🎉 تمت إضافة {credits} رصيدًا.\n💳 الرصيد الحالي: <b>{balance}</b>", tr: "✅ Ödeme başarılı: ⭐{stars}\n🎉 {credits} kredi eklendi.\n💳 Güncel bakiye: <b>{balance}</b>", ru: "✅ Оплата прошла: ⭐{stars}\n🎉 Добавлено {credits} кредитов.\n💳 Текущий баланс: <b>{balance}</b>", es: "✅ Pago exitoso: ⭐{stars}\n🎉 {credits} créditos añadidos.\n💳 Saldo actual: <b>{balance}</b>", de: "✅ Zahlung erfolgreich: ⭐{stars}\n🎉 {credits} Guthaben gutgeschrieben.\n💳 Aktueller Stand: <b>{balance}</b>", fr: "✅ Paiement réussi : ⭐{stars}\n🎉 {credits} crédits ajoutés.\n💳 Solde actuel : <b>{balance}</b>" },
  low_credit_warning: { fa: "کردیت‌ت رو به اتمامه.\nهر وقت خواستی شارژ کن تا راحت‌تر ادامه بدی.", en: "Your credits are running low.\nTop up anytime to keep going.", ar: "رصيدك على وشك النفاد.\nيمكنك الشحن في أي وقت للمتابعة.", tr: "Kredin bitmek üzere.\nDevam etmek için istediğin zaman yükleyebilirsin.", ru: "Кредиты заканчиваются.\nПополните баланс в любое время, чтобы продолжить.", es: "Tus créditos están por agotarse.\nRecarga cuando quieras para seguir.", de: "Deine Credits gehen zur Neige.\nLade jederzeit auf, um weiterzumachen.", fr: "Tes crédits sont presque épuisés.\nRecharge quand tu veux pour continuer." },
  low_credit_button: { fa: "خرید کردیت", en: "Buy credits", ar: "شراء الرصيد", tr: "Kredi satın al", ru: "Купить кредиты", es: "Comprar créditos", de: "Credits kaufen", fr: "Acheter des crédits" },
  force_sub_confirmed: { fa: "✅ عضویت تایید شد!", en: "✅ Subscription confirmed!", ar: "✅ تم تأكيد الاشتراك!", tr: "✅ Üyelik doğrulandı!", ru: "✅ Подписка подтверждена!", es: "✅ Suscripción confirmada.", de: "✅ Mitgliedschaft bestätigt!", fr: "✅ Inscription confirmée !" },
  force_sub_not_joined: { fa: "❌ هنوز عضو نشدی!", en: "❌ You're not a member yet!", ar: "❌ لم تنضم بعد!", tr: "❌ Henüz katılmadın!", ru: "❌ Вы ещё не подписались!", es: "❌ Aún no te has unido.", de: "❌ Du bist noch nicht beigetreten!", fr: "❌ Tu n'as pas encore rejoint !" },
};
const t = (key: string, lang: string) => I18N[key]?.[lang] || I18N[key]?.fa || key;
const DEFAULT_VOICE_NAME_BY_LANG: Record<string, string> = { fa: "Liam", en: "Ava", ar: "Liam", tr: "Arda", ru: "Алина", es: "Valeria", de: "Lena", fr: "Léa" };
const VOICES_BY_LANG: Record<string, Record<string, string>> = {"fa": {"Liam": "TX3LPaxmHKxFdv7VOQHJ", "Amir": "1SM7GgM6IMuvQlz2BwM3", "Nazy": "tnSpp4vdxKPjI9w0GnoV", "Sarah": "BIvP0GN1cAtSRTxNHnWS", "Alex": "GFGuOkimbpNkTEOVDkqX", "Noushin": "NZiuR1C6kVMSWHG27sIM", "Paniz": "BZgkqPqms7Kj9ulSkVzn", "Alexandra": "kdmDKE6EkgrWrrykO9Qt", "Laura": "7piC4m7q8WrpEAnMj5xC", "Maxon": "0dPqNXnhg2bmxQv1WKDp", "Jessica": "cgSgspJ2msm6clMCkdW9", "Austin": "Bj9UqZbhQsanLzgalpEG", "priyanka": "BpjGufoPiobT79j2vtj4", "horatius": "qXpMhyvQqiRxWQs4qSSB", "anika": "Sm1seazb4gs7RSlUVw7c", "brock": "DGzg6RaUqxGRTHSBjfgF", "Xavier": "YOq2y2Up4RgXP2HyXjE5", "Bradford": "NNl6r8mD7vthiJatiJt1"}, "en": {"Liam": "TX3LPaxmHKxFdv7VOQHJ", "Noah": "1SM7GgM6IMuvQlz2BwM3", "Ava": "tnSpp4vdxKPjI9w0GnoV", "Nora": "BIvP0GN1cAtSRTxNHnWS", "Alex": "GFGuOkimbpNkTEOVDkqX", "Ella": "NZiuR1C6kVMSWHG27sIM", "Chloe": "BZgkqPqms7Kj9ulSkVzn", "Alexandra": "kdmDKE6EkgrWrrykO9Qt", "Laura": "7piC4m7q8WrpEAnMj5xC", "Maxon": "0dPqNXnhg2bmxQv1WKDp", "Jessica": "cgSgspJ2msm6clMCkdW9", "Austin": "Bj9UqZbhQsanLzgalpEG", "priyanka": "BpjGufoPiobT79j2vtj4", "horatius": "qXpMhyvQqiRxWQs4qSSB", "anika": "Sm1seazb4gs7RSlUVw7c", "brock": "DGzg6RaUqxGRTHSBjfgF", "Xavier": "YOq2y2Up4RgXP2HyXjE5", "Lucas": "NNl6r8mD7vthiJatiJt1"}, "ar": {"Liam": "TX3LPaxmHKxFdv7VOQHJ", "Amir": "1SM7GgM6IMuvQlz2BwM3", "Nazy": "tnSpp4vdxKPjI9w0GnoV", "Sarah": "BIvP0GN1cAtSRTxNHnWS", "Alex": "GFGuOkimbpNkTEOVDkqX", "Noushin": "NZiuR1C6kVMSWHG27sIM", "Paniz": "BZgkqPqms7Kj9ulSkVzn", "Alexandra": "kdmDKE6EkgrWrrykO9Qt", "Laura": "7piC4m7q8WrpEAnMj5xC", "Maxon": "0dPqNXnhg2bmxQv1WKDp", "Jessica": "cgSgspJ2msm6clMCkdW9", "Austin": "Bj9UqZbhQsanLzgalpEG", "priyanka": "BpjGufoPiobT79j2vtj4", "horatius": "qXpMhyvQqiRxWQs4qSSB", "anika": "Sm1seazb4gs7RSlUVw7c", "brock": "DGzg6RaUqxGRTHSBjfgF", "Xavier": "YOq2y2Up4RgXP2HyXjE5", "Bradford": "NNl6r8mD7vthiJatiJt1"}, "tr": {"Arda": "TX3LPaxmHKxFdv7VOQHJ", "Emre": "1SM7GgM6IMuvQlz2BwM3", "Deniz": "tnSpp4vdxKPjI9w0GnoV", "Sarah": "BIvP0GN1cAtSRTxNHnWS", "Burak": "GFGuOkimbpNkTEOVDkqX", "Selin": "NZiuR1C6kVMSWHG27sIM", "Duru": "BZgkqPqms7Kj9ulSkVzn", "Elif": "kdmDKE6EkgrWrrykO9Qt", "İrem": "7piC4m7q8WrpEAnMj5xC", "Mert": "0dPqNXnhg2bmxQv1WKDp", "Asya": "cgSgspJ2msm6clMCkdW9", "Derya": "Bj9UqZbhQsanLzgalpEG", "priyanka": "BpjGufoPiobT79j2vtj4", "horatius": "qXpMhyvQqiRxWQs4qSSB", "anika": "Sm1seazb4gs7RSlUVw7c", "Ozan": "DGzg6RaUqxGRTHSBjfgF", "Xavier": "YOq2y2Up4RgXP2HyXjE5", "Kaan": "NNl6r8mD7vthiJatiJt1"}, "ru": {"Илья": "TX3LPaxmHKxFdv7VOQHJ", "Никита": "1SM7GgM6IMuvQlz2BwM3", "Алина": "tnSpp4vdxKPjI9w0GnoV", "Милана": "BIvP0GN1cAtSRTxNHnWS", "Даниил": "GFGuOkimbpNkTEOVDkqX", "София": "NZiuR1C6kVMSWHG27sIM", "Ева": "BZgkqPqms7Kj9ulSkVzn", "Полина": "kdmDKE6EkgrWrrykO9Qt", "Кира": "7piC4m7q8WrpEAnMj5xC", "Maxon": "0dPqNXnhg2bmxQv1WKDp", "Дарья": "cgSgspJ2msm6clMCkdW9", "Austin": "Bj9UqZbhQsanLzgalpEG", "priyanka": "BpjGufoPiobT79j2vtj4", "horatius": "qXpMhyvQqiRxWQs4qSSB", "Вероника": "Sm1seazb4gs7RSlUVw7c", "brock": "DGzg6RaUqxGRTHSBjfgF", "Xavier": "YOq2y2Up4RgXP2HyXjE5", "Матвей": "NNl6r8mD7vthiJatiJt1"}, "es": {"Mateo": "TX3LPaxmHKxFdv7VOQHJ", "Leo": "1SM7GgM6IMuvQlz2BwM3", "Valeria": "tnSpp4vdxKPjI9w0GnoV", "Sofía": "BIvP0GN1cAtSRTxNHnWS", "Diego": "GFGuOkimbpNkTEOVDkqX", "Camila": "NZiuR1C6kVMSWHG27sIM", "Luna": "BZgkqPqms7Kj9ulSkVzn", "Renata": "kdmDKE6EkgrWrrykO9Qt", "Martina": "7piC4m7q8WrpEAnMj5xC", "Bruno": "0dPqNXnhg2bmxQv1WKDp", "Paula": "cgSgspJ2msm6clMCkdW9", "Tomás": "Bj9UqZbhQsanLzgalpEG", "Elena": "BpjGufoPiobT79j2vtj4", "horatius": "qXpMhyvQqiRxWQs4qSSB", "Abril": "Sm1seazb4gs7RSlUVw7c", "brock": "DGzg6RaUqxGRTHSBjfgF", "Xavier": "YOq2y2Up4RgXP2HyXjE5", "Andrés": "NNl6r8mD7vthiJatiJt1"}, "de": {"Leon": "TX3LPaxmHKxFdv7VOQHJ", "Luca": "1SM7GgM6IMuvQlz2BwM3", "Lena": "tnSpp4vdxKPjI9w0GnoV", "Mia": "BIvP0GN1cAtSRTxNHnWS", "Finn": "GFGuOkimbpNkTEOVDkqX", "Emma": "NZiuR1C6kVMSWHG27sIM", "Lea": "BZgkqPqms7Kj9ulSkVzn", "Hannah": "kdmDKE6EkgrWrrykO9Qt", "Laura": "7piC4m7q8WrpEAnMj5xC", "Jonas": "0dPqNXnhg2bmxQv1WKDp", "Nina": "cgSgspJ2msm6clMCkdW9", "Paul": "Bj9UqZbhQsanLzgalpEG", "Clara": "BpjGufoPiobT79j2vtj4", "Max": "qXpMhyvQqiRxWQs4qSSB", "Sophie": "Sm1seazb4gs7RSlUVw7c", "Noah": "DGzg6RaUqxGRTHSBjfgF", "Xavier": "YOq2y2Up4RgXP2HyXjE5", "Tim": "NNl6r8mD7vthiJatiJt1"}, "fr": {"Hugo": "TX3LPaxmHKxFdv7VOQHJ", "Noah": "1SM7GgM6IMuvQlz2BwM3", "Léa": "tnSpp4vdxKPjI9w0GnoV", "Inès": "BIvP0GN1cAtSRTxNHnWS", "Theo": "GFGuOkimbpNkTEOVDkqX", "Emma": "NZiuR1C6kVMSWHG27sIM", "Jade": "BZgkqPqms7Kj9ulSkVzn", "Mila": "kdmDKE6EkgrWrrykO9Qt", "Louise": "7piC4m7q8WrpEAnMj5xC", "Jules": "0dPqNXnhg2bmxQv1WKDp", "Jessica": "cgSgspJ2msm6clMCkdW9", "Adrien": "Bj9UqZbhQsanLzgalpEG", "Nina": "BpjGufoPiobT79j2vtj4", "horatius": "qXpMhyvQqiRxWQs4qSSB", "Zoé": "Sm1seazb4gs7RSlUVw7c", "brock": "DGzg6RaUqxGRTHSBjfgF", "Xavier": "YOq2y2Up4RgXP2HyXjE5", "Paul": "NNl6r8mD7vthiJatiJt1"}};
const STAR_PACKAGES = [
  { stars: 250, credits: 8000, title: "• Starter " },
  { stars: 1000, credits: 40000, title: "🎯 Creator " },
  { stars: 3000, credits: 120000, title: "⚡️ Pro " },
  { stars: 5500, credits: 300000, title: "👑 Studio" },
];
const PAYMENT_PLANS = [
  { title: " 800 → 150,000T", amount_toman: 150000, credits: 800 },
  { title: " 2899 → 340,000T", amount_toman: 340000, credits: 2899 },
  { title: " 6100 → 550,000T", amount_toman: 550000, credits: 6100 },
  { title: " 9200 → 770,000T", amount_toman: 770000, credits: 9200 },
  { title: " 12K + 1k → 999,000T", amount_toman: 999000, credits: 13000 },
  { title: " 21K → 1,650,000T", amount_toman: 1650000, credits: 21000 },
  { title: " 46K → 3,420,000T", amount_toman: 3420000, credits: 46000 },
  { title: " 88K → 5,990,000T", amount_toman: 5990000, credits: 88000 },
  { title: " 120K → 8,100,000T", amount_toman: 8100000, credits: 120000 },
  { title: " 150K → 9,999,000T", amount_toman: 9999000, credits: 150000 },
];
const LABELS = {
  homeTitle: "/help   منوی اصلی",
  homeBody: "یکی از گزینه‌های زیر را انتخاب کنید:",
  homeHelp:
    "<b>📖 راهنمای استفاده از Vexa</b>\n\n🔹 <b>کردیت یعنی چی؟</b>\nهر حرف، فاصله یا علامت = ۱ کردیت.\n\n🔹 <b>کردیت رایگان شروع</b>\nبعد از /start، <b>۴۵ کردیت</b> هدیه می‌گیری؛ برای تست کوتاه مثل «سلام، من Vexa هستم».\n\n🔹 <b>اگر پیام «موجودی کافی نیست» دیدی</b>\nمتن رو کوتاه‌تر کن یا اول موجودی رو شارژ کن.\n\n🔹 <b>نکات صداگیری طبیعی</b>\nاز علائم نگارشی استفاده کن:\n• جمله‌ها رو با نقطه جدا کن.\n• برای مکث کوتاه از ویرگول استفاده کن.\n• سوال‌ها رو با ؟ ببند.\n• برای هیجان از ! کمک بگیر.\n\n✍️ <b>مثال</b>\n• ❌ «سلام خوبی امیدوارم حالت خوب باشه»\n• ✅ «سلام! خوبی؟ امیدوارم حالت خوب باشه.»",
  profile: "موجودی شما",
  credit: "خرید کردیـت 🛒",
  tts: "تبدیل متن به صدا 🎧",
  gpt: "GPT-5 mini 🫧",
  lang: "Language 📚",
  invite: "🎁",
  image: "تولید تصویر 🍌",
  video: "تولید ویدیو 🎬",
  apiToken: "API Token 🔑",
  back: "🔙 بازگشت",
  homeBack: "🏠 منوی اصلی",
  gptEnd: "✅ اتمام چت",
  langTitle: "انتخاب زبان",
  langHint: "یکی از زبان‌های زیر را انتخاب کن.",
  langSaved: "✅ زبان ذخیره شد.",
  inviteTitle: "دعوت دوستان 🎁",
  inviteDailyReward: "دریافت پاداش روزانه 🎁",
  lowCreditWarning: "کردیت‌ت رو به اتمامه.\nهر وقت خواستی شارژ کن تا راحت‌تر ادامه بدی.",
  lowCreditButton: "خرید کردیت",
  onboardingWelcome: "🎁 45 کردیت رایگان گرفتی\n≈ ۱۵ ثانیه صدای هوش مصنوعی\nالان امتحانش کن 👇",
  onboardingDailyReady: "🎁 پاداش روزانه آماده است!\nبرای دریافت کردیت رایگان روی دکمه زیر بزن.",
  onboardingDailyUnlocked: "🎉 جایزه روزانه فعال شد!\nحالا می‌تونی از بخش دعوت دوستان، هر روز جایزه بگیری.",
};

type DemoAudioKind = "audio" | "voice" | "document";
type DemoAudioConfig = { fileId: string; kind: DemoAudioKind };

export class TelegramBotFlowService {
  constructor(private deps: TelegramBotFlowDeps) {}

  async handleWebhook(update: TelegramWebhookUpdate): Promise<{ handled: string }> {
    if (await this.deps.telegramEvents.shouldSkipUpdate(update.update_id)) {
      return { handled: "duplicate_update" };
    }
    if (update.pre_checkout_query?.id) {
      await fetch(`https://api.telegram.org/bot${this.deps.botToken}/answerPreCheckoutQuery`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ pre_checkout_query_id: update.pre_checkout_query.id, ok: true }),
      });
      await this.markProcessed(update, update.pre_checkout_query.from?.id ?? null, "pre_checkout");
      return { handled: "pre_checkout" };
    }

    if (update.callback_query?.id) {
      const handled = await this.handleCallback(update.callback_query);
      await this.markProcessed(update, update.callback_query.from?.id ?? null, handled.handled);
      return handled;
    }

    const msg = update.message;
    if (!msg?.chat?.id || !msg.from?.id) {
      await this.markProcessed(update, null, "ignored");
      return { handled: "ignored" };
    }

    const user = await this.deps.users.bootstrapTelegramUser({
      userId: msg.from.id,
      username: msg.from.username,
      firstName: msg.from.first_name,
    });

    const text = (msg.text ?? "").trim();
    const state = await this.deps.userState.getBotState(user.userId);
    const lang = user.lang || "fa";

    if (msg.successful_payment) {
      const payload = JSON.parse(msg.successful_payment.invoice_payload || "{}") as { credits?: number };
      const credits = Number(payload.credits || 0);
      if (credits > 0) {
        await this.deps.credits.grant(user.userId, credits, "telegram_stars_purchase", "telegram_bot");
      }
      const balance = (await this.deps.credits.getCredits(user.userId)).credits;
      const successText = t("credit_pay_success", lang)
        .replace("{stars}", String(msg.successful_payment.total_amount || 0))
        .replace("{credits}", String(credits))
        .replace("{balance}", String(balance));
      await this.sendMessage(
        msg.chat.id,
        successText,
        "HTML"
      );
      await this.markProcessed(update, user.userId, "successful_payment");
      return { handled: "successful_payment" };
    }

    if (text.startsWith("/")) {
      const handled = await this.handleCommand(user.userId, lang, msg.chat.id, text, state);
      await this.markProcessed(update, user.userId, handled.handled);
      return handled;
    }

    if (!state.langSelected) {
      await this.sendLanguageMenu(msg.chat.id, lang, undefined, true);
      await this.markProcessed(update, user.userId, "lang_required");
      return { handled: "lang_required" };
    }

    if (await this.handleMediaDrivenMessage(user.userId, msg.chat.id, msg, state)) {
      await this.markProcessed(update, user.userId, `${state.mode}:media`);
      return { handled: `${state.mode}:media` };
    }

    if (await this.handleStateDrivenMessage(user.userId, lang, msg.chat.id, text, state)) {
      await this.markProcessed(update, user.userId, state.mode);
      return { handled: state.mode };
    }

    if (await this.handleTextNavigation(user.userId, lang, msg.chat.id, text)) {
      await this.markProcessed(update, user.userId, "text_navigation");
      return { handled: "text_navigation" };
    }

    await this.sendMainMenu(msg.chat.id, undefined, lang);
    await this.markProcessed(update, user.userId, "fallback_main_menu");
    return { handled: "fallback_main_menu" };
  }

  private async handleCallback(callback: NonNullable<TelegramWebhookUpdate["callback_query"]>): Promise<{ handled: string }> {
    const chatId = callback.message?.chat?.id;
    const messageId = callback.message?.message_id;
    const userId = callback.from?.id;
    if (!chatId || !userId) {
      await this.answerCallback(callback.id, "Action received ✅");
      return { handled: "callback_ignored" };
    }

    const user = await this.deps.users.bootstrapTelegramUser({
      userId,
      username: callback.from?.username,
      firstName: callback.from?.first_name,
    });

    const lang = user.lang || "fa";
    const data = callback.data ?? "";
    const state = await this.deps.userState.getBotState(user.userId);

    if (data.startsWith("fs:")) {
      return this.handleForceSubCallback(callback.id, chatId, messageId, user.userId, lang, data);
    }

    if (data !== "lang:set:fa" && data.startsWith("lang:set:")) {
      // no-op, handled below
    } else if (!state.langSelected && data !== "home:lang" && !data.startsWith("lang:set:")) {
      await this.answerCallback(callback.id);
      await this.sendLanguageMenu(chatId, lang, messageId, true);
      return { handled: "lang_required" };
    }

    if (!data.startsWith("lang:set:") && !(await this.ensureForceSub(chatId, user.userId, lang, messageId))) {
      await this.answerCallback(callback.id);
      return { handled: "force_sub_required" };
    }

    if (data === "home:back") {
      await this.sendMainMenu(chatId, messageId, lang);
      await this.maybeSendLowCreditWarning(chatId, user.userId, lang, true);
      await this.maybeAdvanceOnboardingMilestones(chatId, user.userId, lang);
      await this.answerCallback(callback.id);
      return { handled: "home_back" };
    }
    if (data === "home:profile") {
      const credits = (await this.deps.credits.getCredits(user.userId)).credits;
      await this.answerCallback(callback.id, `نمای کلی حساب\n\n💳 موجودی شما: ${credits} کردیت`, true);
      return { handled: "profile" };
    }
    if (data === "home:credit" || data === "credit:menu") {
      await this.sendCreditMenu(chatId, lang, messageId);
      await this.answerCallback(callback.id);
      return { handled: "credit_menu" };
    }
    if (data === "credit:stars") {
      await this.sendOrEditMessage(chatId, t("credit_stars_menu", lang), this.starsPackagesKeyboard(lang), messageId, "HTML");
      await this.answerCallback(callback.id);
      return { handled: "credit_stars" };
    }
    if (data.startsWith("credit:buy:")) {
      const parts = data.split(":");
      const stars = Number(parts[2] || 0);
      const credits = Number(parts[3] || 0);
      await this.sendInvoice(chatId, stars, credits, lang);
      await this.answerCallback(callback.id);
      return { handled: "credit_buy_stars" };
    }
    if (data === "credit:payrial") {
      if (lang !== "fa") {
        await this.answerCallback(callback.id, t("credit_unavailable", lang), true);
        return { handled: "credit_unavailable" };
      }
      await this.sendOrEditMessage(chatId, "🧾 <b>پرداخت به تومـان – انتخاب پلن</b>\n\nبا خرید هر بسته 30% کردیت بیشتر دریافت میکنید\nیکی از بسته‌های زیر را انتخاب کنید:", this.payRialPlansKeyboard(lang), messageId, "HTML");
      await this.answerCallback(callback.id);
      return { handled: "credit_payrial" };
    }
    if (data.startsWith("credit:select:")) {
      const index = Number(data.split(":")[2] || 0);
      const plan = PAYMENT_PLANS[index];
      if (!plan) {
        await this.answerCallback(callback.id, t("credit_invalid_plan", lang), true);
        return { handled: "credit_invalid_plan" };
      }
      await this.deps.userState.setBotState(user.userId, { ...state, mode: "idle", updatedAt: nowTs(), waitingReceipt: true, selectedPlanIndex: index });
      const card = this.deps.cardNumber || "---- ---- ---- ----";
      const text = `💱 <b>پرداخت فـوری (کارت‌به‌کارت)</b>\n<b>شماره کارت:</b><code>${card}</code>\n\n• دقیقاً مبلغ <b>${plan.amount_toman.toLocaleString("en-US")} تومان</b> پرداخت کنید\n• سپس <b>تصویر رسید</b> را همین‌جا ارسال کنید\n\n✅ <b>پس از تایید، <b>${plan.credits.toLocaleString("en-US")} کردیت</b> + 30% کردیت اضافه به حساب شما اضافه خواهد شد (کمتر از ۵ دقیقه)</b>`;
      await this.sendOrEditMessage(chatId, text, { inline_keyboard: [[{ text: t("credit_cancel", lang), callback_data: "credit:cancel" }]] }, messageId, "HTML");
      await this.answerCallback(callback.id);
      return { handled: "credit_select_plan" };
    }
    if (data === "credit:cancel") {
      await this.deps.userState.setBotState(user.userId, { ...state, mode: "idle", updatedAt: nowTs(), waitingReceipt: undefined, selectedPlanIndex: undefined });
      await this.sendCreditMenu(chatId, lang, messageId);
      await this.answerCallback(callback.id);
      return { handled: "credit_cancel" };
    }
    if (data === "home:api_token") {
      const token = await this.deps.tokens.getOrCreate(user.userId);
      await this.sendApiTokenMenu(chatId, token, messageId);
      await this.answerCallback(callback.id);
      return { handled: "api_token" };
    }
    if (data === "api:rotate") {
      const token = await this.deps.tokens.rotate(user.userId);
      await this.sendApiTokenMenu(chatId, token, messageId);
      await this.answerCallback(callback.id, "✅ توکن API چرخانده شد.");
      return { handled: "api_rotate" };
    }
    if (data === "home:lang") {
      await this.sendLanguageMenu(chatId, lang, messageId);
      await this.answerCallback(callback.id);
      return { handled: "lang_menu" };
    }
    if (data.startsWith("lang:set:")) {
      const code = data.split(":")[2] || "fa";
      await this.deps.users.setLanguage(user.userId, code);
      const nextState = await this.deps.userState.getBotState(user.userId);
      await this.deps.userState.setBotState(user.userId, {
        ...nextState,
        langSelected: true,
        onboardingPending: nextState.welcomeSentAt ? nextState.onboardingPending : true,
        updatedAt: nowTs(),
      });
      const langState = await this.deps.userState.getBotState(user.userId);
      await this.answerCallback(callback.id, t("lang_saved", code));
      if (!(await this.ensureForceSub(chatId, user.userId, code, messageId))) {
        return { handled: "lang_set_force_sub" };
      }
      await this.consumePendingReferral(user.userId, chatId, code);
      await this.maybeSendWelcomeAudio(chatId, user.userId, code, langState);
      await this.sendMainMenu(chatId, messageId, code);
      await this.maybeSendLowCreditWarning(chatId, user.userId, code, true);
      await this.triggerOnboarding(chatId, user.userId, code);
      await this.maybeAdvanceOnboardingMilestones(chatId, user.userId, code);
      return { handled: "lang_set" };
    }
    if (data === "home:gpt_chat") {
      await this.deps.userState.setBotState(user.userId, { mode: "gpt:chat", updatedAt: nowTs() });
      await this.sendMessage(chatId, "<b>GPT-5 mini آماده است 🙂</b>\n<b>پیامت رو پایین بنویس</b>", "HTML", undefined, {
        keyboard: [[{ text: LABELS.gptEnd }]],
        resize_keyboard: true,
      });
      await this.answerCallback(callback.id);
      return { handled: "gpt_open" };
    }
    if (data === "home:tts") {
      const selected = state.ttsVoice || DEFAULT_VOICE_NAME_BY_LANG[lang] || DEFAULT_VOICE_NAME_BY_LANG.fa;
      await this.deps.userState.setBotState(user.userId, { ...state, mode: "tts:wait_text", updatedAt: nowTs(), ttsVoice: selected, ttsOutput: state.ttsOutput || "mp3", ttsPage: state.ttsPage || 0 });
      await this.sendMessage(chatId, this.ttsAskText(lang, selected), "HTML", this.ttsKeyboard(lang, selected, state.ttsOutput || "mp3", state.ttsPage || 0));
      await this.answerCallback(callback.id);
      return { handled: "tts_open" };
    }
    if (data.startsWith("tts:voice:")) {
      const name = data.split(":").slice(2).join(":");
      const st = await this.deps.userState.getBotState(user.userId);
      await this.deps.userState.setBotState(user.userId, { ...st, mode: "tts:wait_text", updatedAt: nowTs(), ttsVoice: name });
      await this.sendOrEditMessage(chatId, this.ttsAskText(lang, name), this.ttsKeyboard(lang, name, st.ttsOutput || "mp3", st.ttsPage || 0), messageId, "HTML");
      await this.answerCallback(callback.id, name);
      return { handled: "tts_voice" };
    }
    if (data.startsWith("tts:page:")) {
      const st = await this.deps.userState.getBotState(user.userId);
      const step = data.endsWith(":next") ? 1 : -1;
      const nextPage = Math.max(0, (st.ttsPage || 0) + step);
      await this.deps.userState.setBotState(user.userId, { ...st, ttsPage: nextPage, updatedAt: nowTs() });
      const selected = st.ttsVoice || DEFAULT_VOICE_NAME_BY_LANG[lang] || DEFAULT_VOICE_NAME_BY_LANG.fa;
      await this.sendOrEditMessage(chatId, this.ttsAskText(lang, selected), this.ttsKeyboard(lang, selected, st.ttsOutput || "mp3", nextPage), messageId, "HTML");
      await this.answerCallback(callback.id);
      return { handled: "tts_page" };
    }
    if (data.startsWith("tts:demo:")) {
      const voice = data.split(":")[2] || "";
      const demo = this.getDemoAudio(voice, lang);
      if (!demo) {
        await this.answerCallback(callback.id);
        await this.sendMessage(chatId, t("tts_demo_missing", lang), "HTML");
        return { handled: "tts_demo_missing" };
      }
      const now = nowTs();
      const lockKey = `${lang}:${voice}`;
      const existingLock = state.ttsDemoLocks?.[lockKey];
      if (existingLock && existingLock.expiresAt > now) {
        await this.answerCallback(callback.id, t("tts_demo_wait", lang));
        return { handled: "tts_demo_locked" };
      }
      const caption = t("tts_demo_caption", lang).replace("{voice}", voice).replace("{seconds}", String(TTS_DEMO_AUTO_DELETE_SECONDS));
      const method = demo.kind === "voice" ? "sendVoice" : demo.kind === "document" ? "sendDocument" : "sendAudio";
      const mediaKey = demo.kind === "voice" ? "voice" : demo.kind === "document" ? "document" : "audio";
      const sent = await fetch(`https://api.telegram.org/bot${this.deps.botToken}/${method}`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, [mediaKey]: demo.fileId, caption }),
      });
      const payload = (await sent.json().catch(() => ({}))) as { result?: { message_id?: number } };
      const messageIdToDelete = payload.result?.message_id;
      if (messageIdToDelete) {
        setTimeout(async () => {
          await fetch(`https://api.telegram.org/bot${this.deps.botToken}/deleteMessage`, {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({ chat_id: chatId, message_id: messageIdToDelete }),
          });
        }, TTS_DEMO_AUTO_DELETE_SECONDS * 1000);
        await this.deps.userState.setBotState(user.userId, {
          ...state,
          ttsDemoLocks: {
            ...(state.ttsDemoLocks || {}),
            [lockKey]: { messageId: messageIdToDelete, expiresAt: now + TTS_DEMO_AUTO_DELETE_SECONDS },
          },
          updatedAt: now,
        });
      }
      await this.answerCallback(callback.id);
      return { handled: "tts_demo" };
    }
    if (data.startsWith("tts:output:")) {
      const state = await this.deps.userState.getBotState(user.userId);
      const output = data.endsWith(":voice") ? "voice" : "mp3";
      const voice = state.ttsVoice || DEFAULT_VOICE_NAME_BY_LANG[lang] || DEFAULT_VOICE_NAME_BY_LANG.fa;
      await this.deps.userState.setBotState(user.userId, { ...state, mode: "tts:wait_text", updatedAt: nowTs(), ttsOutput: output });
      await this.sendMessage(chatId, t("tts_output_saved", lang).replace("{mode}", output.toUpperCase()), "HTML", this.ttsKeyboard(lang, voice, output, state.ttsPage || 0));
      await this.answerCallback(callback.id);
      return { handled: "tts_output" };
    }
    if (data === "home:clone") {
      await this.deps.userState.setBotState(user.userId, { mode: "clone:wait_audio", updatedAt: nowTs() });
      await this.sendMessage(
        chatId,
        "🧬 <b>ساخت صدای شخصی</b>\n\nیک فایل صوتی (voice/audio) بفرست. بعد از دریافت، اسم صدا را ازت می‌پرسم.",
        "HTML",
        { inline_keyboard: [[{ text: LABELS.back, callback_data: "home:back" }]] }
      );
      await this.answerCallback(callback.id);
      return { handled: "clone_open" };
    }
    if (data === "home:image") {
      await this.deps.userState.setBotState(user.userId, { mode: "image:wait_prompt", updatedAt: nowTs() });
      await this.sendMessage(chatId, "🖼️ <b>تولید تصویر</b>\n\nپرامپتت رو بفرست تا تصویر ساخته بشه.", "HTML", {
        inline_keyboard: [[{ text: LABELS.back, callback_data: "image:back" }]],
      });
      await this.answerCallback(callback.id);
      return { handled: "image_open" };
    }
    if (data === "image:back") {
      await this.deps.userState.setBotState(user.userId, { mode: "idle", updatedAt: nowTs() });
      await this.sendMainMenu(chatId, messageId, lang);
      await this.answerCallback(callback.id);
      return { handled: "image_back" };
    }
    if (data === "home:video") {
      await this.deps.userState.setBotState(user.userId, { mode: "video:wait_image", updatedAt: nowTs() });
      await this.sendMessage(chatId, "🎬 <b>Gen-4 Video</b>\n\nیک عکس بفرست تا ویدیو ساخته شود.", "HTML", {
        inline_keyboard: [[{ text: LABELS.back, callback_data: "video_gen4:back" }]],
      });
      await this.answerCallback(callback.id);
      return { handled: "video_open" };
    }
    if (data === "video_gen4:back") {
      await this.deps.userState.setBotState(user.userId, { mode: "idle", updatedAt: nowTs() });
      await this.sendMainMenu(chatId, messageId, lang);
      await this.answerCallback(callback.id);
      return { handled: "video_back" };
    }
    if (data === "home:invite") {
      await this.sendInviteMenu(chatId, user.userId);
      await this.answerCallback(callback.id);
      return { handled: "invite_open" };
    }
    if (data === "invite:daily_reward" || data === "onboarding:daily_reward") {
      const state = await this.deps.userState.getBotState(user.userId);
      const last = state.dailyRewardClaimedAt ?? 0;
      const diff = nowTs() - last;
      if (diff < DAILY_REWARD_SECONDS) {
        const minutes = Math.ceil((DAILY_REWARD_SECONDS - diff) / 60);
        await this.answerCallback(callback.id, `⏳ ${minutes} دقیقه تا جایزه بعدی باقی مانده.`, true);
        return { handled: "daily_reward_cooldown" };
      }
      await this.deps.credits.grant(user.userId, 10, "invite_daily_reward", "telegram_bot");
      await this.deps.userState.setBotState(user.userId, { ...state, dailyRewardClaimedAt: nowTs(), updatedAt: nowTs() });
      await this.answerCallback(callback.id, "✅ 10 کردیت روزانه اضافه شد!", true);
      await this.sendInviteMenu(chatId, user.userId);
      return { handled: "daily_reward_claim" };
    }
    if (data === "onboarding:invite") {
      await this.sendInviteMenu(chatId, user.userId);
      await this.answerCallback(callback.id);
      return { handled: "onboarding_invite" };
    }
    if (data === "home:sora2" || data === "sora2:menu") {
      await this.sendSora2Menu(chatId, messageId);
      await this.answerCallback(callback.id);
      return { handled: "sora2_menu" };
    }
    if (data === "sora2:buy") {
      const credits = (await this.deps.credits.getCredits(user.userId)).credits;
      if (credits < SORA2_COST) {
        await this.sendSora2NoCredit(chatId, messageId, credits);
        await this.answerCallback(callback.id, "⚠️ کردیت کافی نیست.", true);
        return { handled: "sora2_no_credit" };
      }
      await this.deps.credits.consume(user.userId, SORA2_COST, "sora2_invite_code", "telegram_bot");
      await this.deps.ownerNotifications.queue({
        userId,
        source: "telegram_bot",
        category: "sora2_request",
        message: `queue_position~${SORA2_QUEUE_START} cost=${SORA2_COST}`,
      });
      await this.sendSora2PurchaseSuccess(chatId, messageId);
      await this.answerCallback(callback.id);
      return { handled: "sora2_buy" };
    }
    if (data.startsWith("credit_admin:")) {
      const parts = data.split(":");
      const action = parts[1];
      const targetUser = Number(parts[2] || 0);
      const planIndex = Number(parts[3] || 0);
      const plan = PAYMENT_PLANS[planIndex];
      if (action === "approve" && plan && targetUser > 0) {
        await this.deps.credits.grant(targetUser, plan.credits, "manual_rial_payment", "telegram_bot");
        await this.sendMessage(targetUser, `✅ <b>پرداخت تأیید شد!</b>\n\n💎 <b>${plan.credits.toLocaleString("en-US")} کردیت</b> به حساب شما اضافه شد.\n💰 مبلغ: ${plan.amount_toman.toLocaleString("en-US")} تومان`, "HTML");
        if (callback.message?.message_id && callback.message?.chat?.id) {
          await fetch(`https://api.telegram.org/bot${this.deps.botToken}/editMessageCaption`, {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({
              chat_id: callback.message.chat.id,
              message_id: callback.message.message_id,
              caption: `${callback.message.caption || ""}\n\n✅ <b>تأیید شده توسط ادمین</b>`,
              parse_mode: "HTML",
            }),
          });
        }
        await this.answerCallback(callback.id, "✅ تایید شد");
        return { handled: "credit_admin_approve" };
      }
      if (action === "reject" && targetUser > 0) {
        await this.sendMessage(targetUser, "❌ <b>پرداخت رد شد</b>\n\nرسید ارسالی تأیید نشد. در صورت اطمینان از صحت پرداخت، مجدداً رسید ارسال کنید یا با پشتیبانی تماس بگیرید.", "HTML");
        if (callback.message?.message_id && callback.message?.chat?.id) {
          await fetch(`https://api.telegram.org/bot${this.deps.botToken}/editMessageCaption`, {
            method: "POST",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({
              chat_id: callback.message.chat.id,
              message_id: callback.message.message_id,
              caption: `${callback.message.caption || ""}\n\n❌ <b>رد شده توسط ادمین</b>`,
              parse_mode: "HTML",
            }),
          });
        }
        await this.answerCallback(callback.id, "❌ رد شد");
        return { handled: "credit_admin_reject" };
      }
      await this.answerCallback(callback.id, "خطا در پردازش", true);
      return { handled: "credit_admin_invalid" };
    }

    if (data.startsWith("owner:")) {
      await this.deps.ownerNotifications.queue({
        userId,
        source: "telegram_bot",
        category: "callback_query",
        message: `Owner callback requested: ${data}`,
      });
    }

    await this.answerCallback(callback.id, "Action received ✅");
    return { handled: "callback_query" };
  }

  private async handleCommand(
    userId: number,
    lang: string,
    chatId: number,
    text: string,
    state: BotConversationState
  ): Promise<{ handled: string }> {
    if (text.startsWith("/start")) {
      await this.handleStart(userId, lang, chatId, text, state);
      return { handled: "start" };
    }
    if (!state.langSelected) {
      await this.sendLanguageMenu(chatId, "en", undefined, true);
      return { handled: "lang_required" };
    }
    if (!(await this.ensureForceSub(chatId, userId, lang))) {
      return { handled: "force_sub_required" };
    }

    switch (text) {
      case "/help":
        await this.sendHelp(chatId);
        return { handled: "help" };
      case "/menu":
        await this.sendMainMenu(chatId, undefined, lang);
        await this.maybeSendLowCreditWarning(chatId, userId, lang, true);
        await this.maybeAdvanceOnboardingMilestones(chatId, userId, lang);
        return { handled: "menu" };
      case "/profile": {
        const credits = await this.deps.credits.getCredits(userId);
        await this.sendMessage(chatId, `نمای کلی حساب\n\n💳 موجودی شما: ${credits.credits} کردیت`);
        return { handled: "profile" };
      }
      case "/credits":
        await this.sendCreditMenu(chatId, lang);
        return { handled: "credits" };
      case "/apitoken": {
        const token = await this.deps.tokens.getOrCreate(userId);
        await this.sendApiTokenMenu(chatId, token);
        return { handled: "api_token" };
      }
      case "/rotatetoken": {
        const token = await this.deps.tokens.rotate(userId);
        await this.sendApiTokenMenu(chatId, token);
        return { handled: "api_rotate" };
      }
      case "/ask":
        await this.deps.userState.setBotState(userId, { mode: "gpt:chat", updatedAt: nowTs() });
        await this.sendMessage(chatId, "<b>GPT-5 mini آماده است 🙂</b>\n<b>پیامت رو پایین بنویس</b>", "HTML", undefined, {
          keyboard: [[{ text: LABELS.gptEnd }]],
          resize_keyboard: true,
        });
        return { handled: "gpt_open" };
      case "/cancel":
        await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
        await this.sendMainMenu(chatId, undefined, lang);
        return { handled: "cancel" };
      default:
        await this.sendMainMenu(chatId, undefined, lang);
        return { handled: "unknown_command" };
    }
  }

  private async handleStateDrivenMessage(userId: number, lang: string, chatId: number, text: string, state: BotConversationState): Promise<boolean> {
    if (state.mode === "gpt:chat") {
      if (!text) return false;
      if (text === LABELS.gptEnd) {
        await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
        await this.sendMessage(chatId, "✅ <b>فعلاً تا همین‌جا! هر وقت خواستی برگرد گپ بزنیم.</b>", "HTML", undefined, {
          remove_keyboard: true,
        });
        await this.sendMainMenu(chatId, undefined, lang);
        return true;
      }

      await this.deps.history.append(userId, "user", text);
      await this.deps.history.append(userId, "assistant", `Received your prompt: ${text.slice(0, 400)}`);
      await this.deps.credits.consume(userId, 1, "gpt_message", "telegram_bot");
      await this.sendMessage(chatId, `🫧 <b>درحال فکر کردن...</b>\n\n${text.slice(0, 400)}`, "HTML", undefined, {
        keyboard: [[{ text: LABELS.gptEnd }]],
        resize_keyboard: true,
      });
      return true;
    }

    if (state.mode === "tts:wait_text") {
      if (!text) return false;
      const cost = Math.max(1, Math.ceil(text.length / 100));
      await this.deps.credits.consume(userId, cost, "tts_message", "telegram_bot");
      await this.deps.ownerNotifications.queue({
        userId,
        source: "telegram_bot",
        category: "tts_request",
        message: `voice=${state.ttsVoice || "alloy"} output=${state.ttsOutput || "mp3"} text=${text.slice(0, 1000)}`,
      });
      const voice = state.ttsVoice || DEFAULT_VOICE_NAME_BY_LANG[lang] || DEFAULT_VOICE_NAME_BY_LANG.fa;
      const output = (state.ttsOutput || "mp3").toUpperCase();
      await this.sendMessage(chatId, t("tts_request_saved", lang).replace("{voice}", voice).replace("{output}", output), "HTML", this.ttsKeyboard(lang, voice, state.ttsOutput || "mp3", state.ttsPage || 0));
      return true;
    }

    if (state.mode === "image:wait_prompt") {
      if (!text) return false;
      await this.deps.credits.consume(userId, 1, "image_prompt", "telegram_bot");
      await this.deps.ownerNotifications.queue({
        userId,
        source: "telegram_bot",
        category: "image_request",
        message: text.slice(0, 1500),
      });
      await this.sendMessage(chatId, "🖼️ درخواست تصویرت ثبت شد و برای پردازش ارسال شد.", undefined, {
        inline_keyboard: [[{ text: LABELS.back, callback_data: "image:back" }]],
      });
      return true;
    }

    if (state.mode === "video:wait_image") {
      if (!text) return false;
      await this.sendMessage(chatId, "🎬 لطفاً یک عکس ارسال کن.", undefined, {
        inline_keyboard: [[{ text: LABELS.back, callback_data: "video_gen4:back" }]],
      });
      return true;
    }

    if (state.mode === "clone:wait_name") {
      if (!text) return false;
      if (!state.cloneFileId) {
        await this.deps.userState.setBotState(userId, { mode: "clone:wait_audio", updatedAt: nowTs() });
        await this.sendMessage(chatId, "⚠️ فایل صوتی پیدا نشد؛ دوباره فایل را ارسال کن.");
        return true;
      }

      await this.deps.credits.consume(userId, 5, "clone_voice", "telegram_bot");
      await this.deps.ownerNotifications.queue({
        userId,
        source: "telegram_bot",
        category: "clone_request",
        message: `name=${text.slice(0, 100)} file_kind=${state.cloneFileKind || "voice"} file_id=${state.cloneFileId}`,
      });
      await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
      await this.sendMessage(chatId, "✅ درخواست ساخت صدای شخصی ثبت شد. بعد از آماده‌شدن اطلاع می‌گیری.", "HTML");
      await this.sendMainMenu(chatId, undefined, lang);
      return true;
    }

    return false;
  }

  private async handleTextNavigation(userId: number, lang: string, chatId: number, text: string): Promise<boolean> {
    switch (text) {
      case t("btn_profile", lang):
        await this.handleCommand(userId, lang, chatId, "/profile", { mode: "idle", updatedAt: nowTs() });
        return true;
      case t("btn_credit", lang):
        await this.sendCreditMenu(chatId, lang);
        return true;
      case t("btn_tts", lang):
        await this.deps.userState.setBotState(userId, { mode: "tts:wait_text", updatedAt: nowTs(), ttsVoice: DEFAULT_VOICE_NAME_BY_LANG[lang] || DEFAULT_VOICE_NAME_BY_LANG.fa, ttsOutput: "mp3", ttsPage: 0 });
        await this.sendMessage(chatId, this.ttsAskText(lang, DEFAULT_VOICE_NAME_BY_LANG[lang] || DEFAULT_VOICE_NAME_BY_LANG.fa), "HTML", this.ttsKeyboard(lang, DEFAULT_VOICE_NAME_BY_LANG[lang] || DEFAULT_VOICE_NAME_BY_LANG.fa, "mp3", 0));
        return true;
      case LABELS.gpt:
        await this.handleCommand(userId, lang, chatId, "/ask", { mode: "idle", updatedAt: nowTs() });
        return true;
      case t("btn_lang", lang):
        await this.sendLanguageMenu(chatId, lang);
        return true;
      case LABELS.apiToken: {
        const token = await this.deps.tokens.getOrCreate(userId);
        await this.sendApiTokenMenu(chatId, token);
        return true;
      }
      default:
        return false;
    }
  }

  private mainMenuKeyboard(lang: string): InlineKeyboard {
    return {
      inline_keyboard: [
        [
          { text: t("btn_profile", lang), callback_data: "home:profile" },
          { text: t("btn_credit", lang), callback_data: "home:credit" },
        ],
        [{ text: t("btn_tts", lang), callback_data: "home:tts" }],
        [{ text: LABELS.gpt, callback_data: "home:gpt_chat" }],
        [
          { text: LABELS.image, callback_data: "home:image" },
          { text: LABELS.video, callback_data: "home:video" },
        ],
        [{ text: "Sora 2 🎬", callback_data: "home:sora2" }],
        [
          { text: t("btn_lang", lang), callback_data: "home:lang" },
          { text: t("btn_invite", lang), callback_data: "home:invite" },
        ],
      ],
    };
  }

  private async sendMainMenu(chatId: number, messageId?: number, lang = "fa") {
    const text = `🏠 <b>${t("home_title", lang)}</b>\n\n${t("home_body", lang)}`;
    await this.sendOrEditMessage(chatId, text, this.mainMenuKeyboard(lang), messageId, "HTML");
  }

  private async sendCreditMenu(chatId: number, lang: string, messageId?: number) {
    const text = `🛒 <b>${t("credit_title", lang)}</b>\n\n${t("credit_header", lang)}`;
    const replyMarkup: InlineKeyboard = {
      inline_keyboard: [
        [{ text: t("credit_pay_stars_btn", lang), callback_data: "credit:stars" }],
        ...(lang === "fa" ? [[{ text: t("credit_pay_rial_btn", lang), callback_data: "credit:payrial" }] as Array<{ text: string; callback_data: string }>] : []),
        [{ text: t("back", lang), callback_data: "home:back" }],
      ],
    };
    await this.sendOrEditMessage(chatId, text, replyMarkup, messageId, "HTML");
  }

  private starsPackagesKeyboard(lang: string): InlineKeyboard {
    const rows: InlineKeyboard["inline_keyboard"] = [];
    for (let i = 0; i < STAR_PACKAGES.length; i += 2) {
      rows.push(
        STAR_PACKAGES.slice(i, i + 2).map((pkg) => ({
          text: pkg.title,
          callback_data: `credit:buy:${pkg.stars}:${pkg.credits}`,
        }))
      );
    }
    rows.push([{ text: t("back", lang), callback_data: "credit:menu" }]);
    return { inline_keyboard: rows };
  }

  private payRialPlansKeyboard(lang: string): InlineKeyboard {
    const rows: InlineKeyboard["inline_keyboard"] = [];
    for (let i = 0; i < PAYMENT_PLANS.length; i += 2) {
      rows.push(
        PAYMENT_PLANS.slice(i, i + 2).map((plan, idx) => ({
          text: plan.title,
          callback_data: `credit:select:${i + idx}`,
        }))
      );
    }
    rows.push([{ text: t("back", lang), callback_data: "credit:menu" }]);
    return { inline_keyboard: rows };
  }

  private async sendInvoice(chatId: number, stars: number, credits: number, lang: string) {
    const payload = JSON.stringify({ credits, stars });
    await fetch(`https://api.telegram.org/bot${this.deps.botToken}/sendInvoice`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        chat_id: chatId,
        title: t("credit_invoice_title", lang),
        description: t("credit_invoice_desc", lang),
        payload,
        provider_token: "",
        currency: "XTR",
        prices: [{ label: t("credit_invoice_label", lang).replace("{credits}", String(credits)), amount: stars }],
      }),
    });
  }

  private async sendLanguageMenu(chatId: number, currentLang: string, messageId?: number, forceNew = false) {
    const rows: Array<Array<{ text: string; callback_data: string }>> = [];
    for (let i = 0; i < LANGS.length; i += 2) {
      const left = LANGS[i]!;
      const right = LANGS[i + 1];
      const row = [{ text: `${left.code === currentLang ? "• " : ""}${left.label}`, callback_data: `lang:set:${left.code}` }];
      if (right) {
        row.push({ text: `${right.code === currentLang ? "• " : ""}${right.label}`, callback_data: `lang:set:${right.code}` });
      }
      rows.push(row);
    }

    const text = `🌐 <b>${t("lang_title", currentLang)}</b>\n\n${t("lang_hint", currentLang)}`;
    if (forceNew || !messageId) {
      await this.sendMessage(chatId, text, "HTML", { inline_keyboard: rows });
      return;
    }
    await this.sendOrEditMessage(chatId, text, { inline_keyboard: rows }, messageId, "HTML");
  }

  private async sendApiTokenMenu(chatId: number, token: string, messageId?: number) {
    const text = [
      "🔐 <b>کلید API مخصوص تو</b>",
      `<code>${token}</code>`,
      "",
      "برای هر درخواست این هدر را اضافه کن:",
      `<code>X-API-Key: ${token}</code>`,
    ].join("\n");
    const replyMarkup: InlineKeyboard = {
      inline_keyboard: [
        [{ text: "♻️ چرخش توکن API", callback_data: "api:rotate" }],
        [{ text: LABELS.homeBack, callback_data: "home:back" }],
      ],
    };
    await this.sendOrEditMessage(chatId, text, replyMarkup, messageId, "HTML");
  }

  private ttsKeyboard(lang: string, selectedVoice: string, selectedOutput: "mp3" | "voice" = "mp3", page = 0): InlineKeyboard {
    const voices = Object.keys(VOICES_BY_LANG[lang] || VOICES_BY_LANG.fa);
    const perPage = voices.length > 10 ? 9 : 10;
    const totalPages = Math.max(1, Math.ceil(voices.length / perPage));
    const current = Math.max(0, Math.min(page, totalPages - 1));
    const slice = voices.slice(current * perPage, current * perPage + perPage);
    const rows: InlineKeyboard["inline_keyboard"] = [];
    for (let i = 0; i < slice.length; i += 2) {
      rows.push(
        slice.slice(i, i + 2).map((name) => ({ text: `${name === selectedVoice ? "✔️ " : ""}${name}`, callback_data: `tts:voice:${name}` }))
      );
    }
    const nav: Array<{ text: string; callback_data: string }> = [];
    if (current > 0) nav.push({ text: t("tts_prev", lang), callback_data: "tts:page:prev" });
    if (current < totalPages - 1) nav.push({ text: t("tts_next", lang), callback_data: "tts:page:next" });
    if (nav.length) rows.push(nav);
    rows.push([{ text: t("tts_demo", lang), callback_data: `tts:demo:${selectedVoice}` }]);
    rows.push([
      { text: `${selectedOutput === "mp3" ? "✔️ " : ""}${t("tts_output_mp3", lang)}`, callback_data: "tts:output:mp3" },
      { text: `${selectedOutput === "voice" ? "✔️ " : ""}${t("tts_output_voice", lang)}`, callback_data: "tts:output:voice" },
    ]);
    rows.push([{ text: t("btn_clone", lang), callback_data: "home:clone" }]);
    rows.push([{ text: t("back", lang), callback_data: "home:back" }]);
    return { inline_keyboard: rows };
  }

  private ttsAskText(lang: string, voiceName: string) {
    return `🎧 <b>${t("tts_title", lang)}</b>\n\n${t("tts_prompt", lang).replace("{credit}", "1")}\n\n🎙 <b>${voiceName}</b>`;
  }

  private getDemoAudio(voiceName: string, lang: string): DemoAudioConfig | null {
    if (!voiceName) return null;
    const raw = this.deps.ttsDemoAudiosJson;
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw) as Record<string, Record<string, { fileId?: string; kind?: DemoAudioKind }> | { fileId?: string; kind?: DemoAudioKind }>;
      const byLang = parsed[lang];
      const global = parsed[voiceName];
      const langVoice = byLang && typeof byLang === "object" && voiceName in byLang ? (byLang as Record<string, { fileId?: string; kind?: DemoAudioKind }>)[voiceName] : undefined;
      const picked = langVoice || (global as { fileId?: string; kind?: DemoAudioKind } | undefined);
      if (!picked?.fileId) return null;
      return { fileId: picked.fileId, kind: picked.kind || "audio" };
    } catch {
      return null;
    }
  }

  private async handleStart(userId: number, lang: string, chatId: number, text: string, state: BotConversationState) {
    const parts = text.split(/\s+/, 2);
    const startParam = parts.length > 1 ? parts[1] : "";
    if (startParam && /^\d+$/.test(startParam) && Number(startParam) !== userId && !state.pendingReferralCode) {
      await this.deps.userState.setBotState(userId, { ...state, pendingReferralCode: startParam, updatedAt: nowTs() });
    }
    if (!state.langSelected) {
      await this.sendLanguageMenu(chatId, "en", undefined, true);
      return;
    }
    if (!state.welcomeSentAt && !state.onboardingPending) {
      await this.deps.userState.setBotState(userId, { ...state, onboardingPending: true, updatedAt: nowTs() });
      state = await this.deps.userState.getBotState(userId);
    }
    await this.maybeSendWelcomeAudio(chatId, userId, lang, state);
    await this.consumePendingReferral(userId, chatId, lang);
    await this.sendMainMenu(chatId, undefined, lang);
    await this.maybeSendLowCreditWarning(chatId, userId, lang, true);
    await this.triggerOnboarding(chatId, userId, lang);
    await this.maybeAdvanceOnboardingMilestones(chatId, userId, lang);
  }

  private async handleMediaDrivenMessage(userId: number, chatId: number, msg: NonNullable<TelegramWebhookUpdate["message"]>, state: BotConversationState): Promise<boolean> {
    if (state.waitingReceipt) {
      const fileId = (msg.photo && msg.photo.length ? msg.photo[msg.photo.length - 1]?.file_id : undefined) || msg.document?.file_id;
      if (!fileId) return false;
      const planIndex = state.selectedPlanIndex ?? 0;
      const plan = PAYMENT_PLANS[planIndex];
      if (this.deps.ownerTelegramChatId) {
        const caption = `🧾 <b>رسید پرداخت جدید</b>\n• User ID: <code>${userId}</code>\n• Username: @${msg.from?.username || "-"}\n• Name: ${(msg.from?.first_name || "").trim() || "-"}\n\n• مبلغ: ${plan?.amount_toman?.toLocaleString("en-US") || "-"} تومان\n• کردیت: ${plan?.credits?.toLocaleString("en-US") || "-"} `;
        await fetch(`https://api.telegram.org/bot${this.deps.botToken}/sendPhoto`, {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({
            chat_id: this.deps.ownerTelegramChatId,
            photo: fileId,
            caption,
            parse_mode: "HTML",
            reply_markup: {
              inline_keyboard: [[
                { text: "✅ تایید", callback_data: `credit_admin:approve:${userId}:${planIndex}` },
                { text: "❌ رد", callback_data: `credit_admin:reject:${userId}:${planIndex}` },
              ]],
            },
          }),
        });
      }
      await this.deps.userState.setBotState(userId, { ...state, waitingReceipt: undefined, selectedPlanIndex: undefined, updatedAt: nowTs() });
      const user = await this.deps.users.getProfile(userId);
      await this.sendMessage(chatId, "✅ رسید دریافت شد\n⏳ <b>لطفاً منتظر تایید باش</b>", "HTML");
      await this.sendMainMenu(chatId, undefined, user.lang || "fa");
      return true;
    }
    if (state.mode === "video:wait_image") {
      const lastPhoto = msg.photo && msg.photo.length ? msg.photo[msg.photo.length - 1] : undefined;
      const imageFile = lastPhoto?.file_id || (msg.document?.mime_type?.startsWith("image/") ? msg.document.file_id : undefined);
      if (!imageFile) return false;
      await this.deps.credits.consume(userId, 1, "video_prompt", "telegram_bot");
      await this.deps.ownerNotifications.queue({
        userId,
        source: "telegram_bot",
        category: "video_request",
        message: `image_file_id=${imageFile} caption=${(msg.caption || "").slice(0, 500)}`,
      });
      await this.sendMessage(chatId, "✅ درخواست ویدیو ثبت شد و برای پردازش ارسال شد.", "HTML", {
        inline_keyboard: [[{ text: LABELS.back, callback_data: "video_gen4:back" }]],
      });
      return true;
    }

    if (state.mode === "clone:wait_audio") {
      const fileId = msg.voice?.file_id || msg.audio?.file_id || msg.document?.file_id;
      if (!fileId) return false;
      const kind: "voice" | "audio" | "document" = msg.voice ? "voice" : msg.audio ? "audio" : "document";
      await this.deps.userState.setBotState(userId, {
        mode: "clone:wait_name",
        updatedAt: nowTs(),
        cloneFileId: fileId,
        cloneFileKind: kind,
      });
      await this.sendMessage(chatId, "✅ فایل صوتی دریافت شد.\nحالا یک اسم برای صدای جدیدت بفرست.", "HTML");
      return true;
    }

    if (!msg.photo && !msg.document?.file_id) {
      return false;
    }

    await this.deps.ownerNotifications.queue({
      userId,
      source: "telegram_bot",
      category: "payment_receipt",
      message: `file_id=${(msg.photo && msg.photo.length ? msg.photo[msg.photo.length - 1]?.file_id : undefined) || msg.document?.file_id || "unknown"} caption=${(msg.caption || "").slice(0, 300)}`,
    });
    await this.sendMessage(chatId, "✅ رسید دریافت شد و برای تایید ادمین ارسال شد.");
    return true;
  }

  private async sendInviteMenu(chatId: number, userId: number) {
    const bonus = REFERRAL_BONUS;
    await this.sendMessage(
      chatId,
      `🎁 <b>${LABELS.inviteTitle}</b>\n\nشناسه عددی شما: <code>${userId}</code>\nتعداد دعوت‌ها تا الان: <b>0</b>\n\nلینک دعوت شما:\n<code>https://t.me/${this.deps.botUsername || "VexaAiBot"}?start=${userId}</code>\n\n<b>به ازای هر دعوت : +${bonus} کردیت</b>`,
      "HTML",
      {
        inline_keyboard: [
          [{ text: LABELS.back, callback_data: "home:back" }],
          [{ text: LABELS.inviteDailyReward, callback_data: "invite:daily_reward" }],
        ],
      }
    );
  }

  private async sendHelp(chatId: number) {
    await this.sendMessage(chatId, LABELS.homeHelp, "HTML", { inline_keyboard: [[{ text: LABELS.homeBack, callback_data: "home:back" }]] });
  }

  private async sendSora2Menu(chatId: number, messageId?: number) {
    const text =
      "<b>🎬 خوش اومدی به بخش Sora 2</b>\n\n<b>✨ با Sora 2 می‌تونی فقط با نوشتن چند جمله، ویدیوهای واقعی و سینمایی بسازی!</b>\n<b>🚀 ساخته شده با هوش مصنوعی پیشرفته OpenAI</b>\n\n<b>🎞 هر ویدیو تا ۲۰ ثانیه و با کیفیت 1080p تولید میشه</b>\n\n<b>💰 برای فعال‌سازی دسترسی، باید «کد دعوت SORA 2» تهیه کنی.</b>\n<b>🔑 هزینه دریافت کد دعوت: 259 کردیت</b>\n\n<b>⚡ پس از پرداخت، کد اختصاصی برات ارسال میشه و می‌تونی وارد دنیای SORA بشی!</b>";
    await this.sendOrEditMessage(chatId, text, { inline_keyboard: [[{ text: "خرید کد دعوت 🎟️", callback_data: "sora2:buy" }], [{ text: LABELS.homeBack, callback_data: "home:back" }]] }, messageId, "HTML");
  }

  private async sendSora2NoCredit(chatId: number, messageId: number | undefined, credits: number) {
    const text = `⚠️ <b>کردیت کافی نیست!</b>\n<b>هزینه خرید کد دعوت: ${SORA2_COST} کردیت</b>\n<b>موجودی فعلی: ${credits} کردیت</b>\n\n<b>برای شارژ دکمه «خرید کردیت» رو بزن.</b>`;
    await this.sendOrEditMessage(
      chatId,
      text,
      { inline_keyboard: [[{ text: LABELS.credit, callback_data: "credit:menu" }], [{ text: LABELS.homeBack, callback_data: "home:back" }]] },
      messageId,
      "HTML"
    );
  }

  private async sendSora2PurchaseSuccess(chatId: number, messageId?: number) {
    const text = `<b>✅ پرداخت موفق!</b>\n<b>${SORA2_COST} کردیت از حسابت کم شد 💳</b>\n<b>⌛ تو صف انتظار هستی (نفر ${SORA2_QUEUE_START})</b>\n<b>🎟 کد دعوت Sora 2 به‌زودی برات ارسال میشه.</b>`;
    await this.sendOrEditMessage(chatId, text, { inline_keyboard: [[{ text: "خرید کد دعوت 🎟️", callback_data: "sora2:buy" }], [{ text: LABELS.homeBack, callback_data: "home:back" }]] }, messageId, "HTML");
  }

  private async maybeSendLowCreditWarning(chatId: number, userId?: number, _lang = "fa", scheduleIfNeeded = false) {
    if (!userId) return;
    const profile = await this.deps.users.getProfile(userId);
    const state = await this.deps.userState.getBotState(userId);
    if (profile.credits >= LOW_CREDIT_THRESHOLD) {
      if (state.lowCreditPromptedAt || state.lowCreditScheduledAt) {
        await this.deps.userState.setBotState(userId, {
          ...state,
          lowCreditPromptedAt: undefined,
          lowCreditScheduledAt: undefined,
          updatedAt: nowTs(),
        });
      }
      return;
    }
    if (state.lowCreditPromptedAt) return;
    const now = nowTs();
    if (scheduleIfNeeded && !state.lowCreditScheduledAt) {
      await this.deps.userState.setBotState(userId, { ...state, lowCreditScheduledAt: now + LOW_CREDIT_DELAY_SECONDS, updatedAt: now });
      return;
    }
    if (state.lowCreditScheduledAt && now < state.lowCreditScheduledAt) return;
    await this.sendMessage(chatId, t("low_credit_warning", _lang), "HTML", { inline_keyboard: [[{ text: t("low_credit_button", _lang), callback_data: "credit:menu" }]] });
    await this.deps.userState.setBotState(userId, {
      ...state,
      lowCreditPromptedAt: now,
      lowCreditScheduledAt: undefined,
      updatedAt: now,
    });
  }

  private async triggerOnboarding(chatId: number, userId: number, _lang: string) {
    const state = await this.deps.userState.getBotState(userId);
    if (!state.onboardingPending || state.welcomeSentAt) return;
    const now = nowTs();
    await this.sendMessage(chatId, LABELS.onboardingWelcome, "HTML");
    await this.deps.userState.setBotState(userId, {
      ...state,
      welcomeSentAt: now,
      onboardingPending: false,
      updatedAt: now,
    });
  }

  private async maybeAdvanceOnboardingMilestones(chatId: number, userId: number, _lang: string) {
    const state = await this.deps.userState.getBotState(userId);
    const now = nowTs();
    if (state.welcomeSentAt && !state.dailyBonusPromptedAt && now - state.welcomeSentAt >= ONBOARDING_DAILY_BONUS_DELAY) {
      await this.sendMessage(chatId, LABELS.onboardingDailyReady, "HTML", {
        inline_keyboard: [[{ text: "🎁", callback_data: "onboarding:daily_reward" }]],
      });
      await this.deps.userState.setBotState(userId, { ...state, dailyBonusPromptedAt: now, updatedAt: now });
      return;
    }

    if (state.dailyBonusPromptedAt && !state.dailyBonusUnlockedAt && now - state.dailyBonusPromptedAt >= ONBOARDING_DAILY_BONUS_UNLOCK_DELAY) {
      await this.sendMessage(chatId, LABELS.onboardingDailyUnlocked, "HTML", {
        inline_keyboard: [[{ text: "🎁", callback_data: "onboarding:invite" }]],
      });
      await this.deps.userState.setBotState(userId, { ...state, dailyBonusUnlockedAt: now, updatedAt: now });
    }
  }

  private async maybeSendWelcomeAudio(chatId: number, userId: number, _lang: string, state: BotConversationState) {
    if (!this.deps.welcomeAudioFileId || state.welcomeAudioSentAt || !state.onboardingPending) return;
    const method = this.deps.welcomeAudioKind === "voice" ? "sendVoice" : this.deps.welcomeAudioKind === "document" ? "sendDocument" : "sendAudio";
    const mediaKey = this.deps.welcomeAudioKind === "voice" ? "voice" : this.deps.welcomeAudioKind === "document" ? "document" : "audio";
    const body: Record<string, unknown> = { chat_id: chatId, [mediaKey]: this.deps.welcomeAudioFileId };
    await fetch(`https://api.telegram.org/bot${this.deps.botToken}/${method}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
    await this.deps.userState.setBotState(userId, { ...state, welcomeAudioSentAt: nowTs(), updatedAt: nowTs() });
  }

  private async consumePendingReferral(userId: number, chatId: number, _lang: string) {
    const state = await this.deps.userState.getBotState(userId);
    const refCode = (state.pendingReferralCode || "").trim();
    if (!refCode || !/^[0-9]+$/.test(refCode) || Number(refCode) === userId) return;
    await this.deps.credits.grant(Number(refCode), REFERRAL_BONUS, "invite_referral", "telegram_bot");
    await this.sendMessage(chatId, "🎉 <b>خوش اومدی! 45 کردیت رایگان گرفتی</b>", "HTML");
    await this.deps.ownerNotifications.queue({
      userId: Number(refCode),
      source: "telegram_bot",
      category: "ref_notify",
      message: `👥 یک کاربر با لینک تو عضو شد\n🎁 <b>${REFERRAL_BONUS}</b> کردیت بهت اضافه شد`,
    });
    await this.deps.userState.setBotState(userId, { ...state, pendingReferralCode: undefined, updatedAt: nowTs() });
  }

  private async ensureForceSub(chatId: number, userId: number, _lang: string, messageId?: number): Promise<boolean> {
    const mode = (this.deps.forceSubMode || "none").trim();
    if (mode === "none") return true;
    const tgChannel = (this.deps.forceSubChannel || "").trim();
    const igUrl = (this.deps.forceSubInstagramUrl || "").trim();
    const normalized = tgChannel.replace(/^https?:\/\/t\.me\//, "").replace(/^t\.me\//, "").replace(/^@/, "");
    const hasTg = normalized.length > 0;
    const hasIg = igUrl.length > 0;
    let needsTgCheck = hasTg;
    if (mode === "instagram") needsTgCheck = false;
    if (mode === "telegram") needsTgCheck = hasTg;

    if (needsTgCheck) {
      const channelRef = `@${normalized}`;
      const response = await fetch(`https://api.telegram.org/bot${this.deps.botToken}/getChatMember`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ chat_id: channelRef, user_id: userId }),
      });
      if (response.ok) {
        const data = (await response.json()) as { result?: { status?: string; is_member?: boolean } };
        const status = data.result?.status || "";
        const isMember = status === "creator" || status === "administrator" || status === "member" || (status === "restricted" && data.result?.is_member);
        if (isMember) return true;
      } else {
        const failed = (await response.json().catch(() => ({}))) as { description?: string };
        const description = (failed.description || "").toLowerCase();
        const isPermissionBlocked =
          description.includes("chat not found") ||
          description.includes("bot is not a member") ||
          description.includes("not enough rights") ||
          description.includes("chat_admin_required") ||
          description.includes("have no rights");
        if (isPermissionBlocked) return true;
      }
    } else if (!hasIg) {
      return true;
    }

    const keyboard: InlineKeyboard = {
      inline_keyboard: [
        ...(hasTg ? [[{ text: "عضویت در کانال 🚀", url: `https://t.me/${normalized}` }]] : []),
        ...(hasIg ? [[{ text: "دنبال‌کردن اینستاگرام 📸", url: igUrl }]] : []),
        [{ text: "عضو شدم ✅", callback_data: "fs:recheck" }],
      ],
    };
    const lines = ["<b>برای ادامه عضو کانال شو</b>"];
    if (hasTg) lines.push("• کانال تلگرام");
    if (hasIg) lines.push("• اینستاگرام");
    lines.push("", "بعد از عضویت روی دکمه «عضو شدم» بزن.");
    const text = lines.join("\n");
    if (messageId) await this.sendOrEditMessage(chatId, text, keyboard, messageId, "HTML");
    else await this.sendMessage(chatId, text, "HTML", keyboard);
    return false;
  }

  private async handleForceSubCallback(
    callbackId: string,
    chatId: number,
    messageId: number | undefined,
    userId: number,
    lang: string,
    data: string
  ): Promise<{ handled: string }> {
    if (await this.ensureForceSub(chatId, userId, lang, messageId)) {
      await this.sendMainMenu(chatId, messageId, lang);
      await this.consumePendingReferral(userId, chatId, lang);
      const state = await this.deps.userState.getBotState(userId);
      await this.maybeSendWelcomeAudio(chatId, userId, lang, state);
      await this.triggerOnboarding(chatId, userId, lang);
      await this.maybeAdvanceOnboardingMilestones(chatId, userId, lang);
      await this.maybeSendLowCreditWarning(chatId, userId, lang, true);
      await this.answerCallback(callbackId, t("force_sub_confirmed", lang));
      return { handled: "force_sub_confirmed" };
    }
    await this.answerCallback(callbackId, t("force_sub_not_joined", lang));
    return { handled: "force_sub_not_joined" };
  }

  private async markProcessed(update: TelegramWebhookUpdate, telegramUserId: number | null, eventType: string) {
    if (typeof update.update_id === "number") {
      await this.deps.telegramEvents.markProcessed(update.update_id, telegramUserId, eventType);
    }
  }

  private async sendOrEditMessage(
    chatId: number,
    text: string,
    replyMarkup: InlineKeyboard,
    messageId?: number,
    parseMode: ParseMode = "HTML"
  ) {
    if (messageId) {
      const edited = await fetch(`https://api.telegram.org/bot${this.deps.botToken}/editMessageText`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          chat_id: chatId,
          message_id: messageId,
          text,
          parse_mode: parseMode,
          reply_markup: replyMarkup,
        }),
      });
      if (edited.ok) return;
    }

    await this.sendMessage(chatId, text, parseMode, replyMarkup);
  }

  private async sendMessage(
    chatId: number,
    text: string,
    parse_mode?: ParseMode,
    reply_markup?: InlineKeyboard,
    replyKeyboardExtra?: ReplyKeyboard | { remove_keyboard: true }
  ) {
    const body: Record<string, unknown> = { chat_id: chatId, text, parse_mode };
    if (reply_markup) body.reply_markup = reply_markup;
    if (replyKeyboardExtra) body.reply_markup = replyKeyboardExtra;

    await fetch(`https://api.telegram.org/bot${this.deps.botToken}/sendMessage`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  private async answerCallback(callbackQueryId: string, text?: string, showAlert = false) {
    await fetch(`https://api.telegram.org/bot${this.deps.botToken}/answerCallbackQuery`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ callback_query_id: callbackQueryId, text, show_alert: showAlert }),
    });
  }
}
