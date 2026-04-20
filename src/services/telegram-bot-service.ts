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
  db: D1Database;
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

const ADMIN_FEATURE_TOGGLES: Array<{ label: string; key: string }> = [
  { label: "✅/❌ GPT", key: "GPT_ENABLED" },
  { label: "✅/❌ تصویر", key: "IMAGE_ENABLED" },
  { label: "✅/❌ ویدیو", key: "VIDEO_ENABLED" },
  { label: "✅/❌ Voice Clone", key: "CLONE_ENABLED" },
  { label: "✅/❌ Sora2", key: "SORA2_ENABLED" },
];


const I18N: Record<string, Record<string, string>> = {
  home_title: { fa: "/help   منوی اصلی", en: "Main Menu", ar: "القائمة الرئيسية", tr: "Ana Menü", ru: "Главное меню", es: "Menú principal", de: "Hauptmenü", fr: "Menu principal" },
  home_body: { fa: "یکی از گزینه‌های زیر را انتخاب کنید:", en: "Choose an option:", ar: "اختر خياراً:", tr: "Bir seçenek seçin:", ru: "Выберите опцию:", es: "Elige una opción:", de: "Wähle eine Option:", fr: "Choisissez une option :" },
  btn_profile: { fa: "موجودی شما", en: "Your Balance", ar: "رصيدك", tr: "Bakiyeniz", ru: "Ваш баланс", es: "Tu saldo", de: "Dein Guthaben", fr: "Ton solde" },
  btn_credit: { fa: "خرید کردیـت 🛒", en: "Buy Credit 🛒", ar: "شراء الرصيد 🛒", tr: "Kredi Satın Al 🛒", ru: "Купить кредит 🛒", es: "Comprar crédito 🛒", de: "Guthaben kaufen 🛒", fr: "Acheter du crédit 🛒" },
  btn_tts: { fa: "تبدیل متن به صدا 🎧", en: "Text to Speech 🎧", ar: "تحويل النص إلى صوت 🎧", tr: "Metinden Sese 🎧", ru: "Текст в речь 🎧", es: "Texto a voz 🎧", de: "Text zu Sprache 🎧", fr: "Texte en voix 🎧" },
  btn_gpt: { fa: "GPT-5 mini 🫧", en: "GPT-5 mini 🫧", ar: "GPT-5 mini 🫧", tr: "GPT-5 mini 🫧", ru: "GPT-5 mini 🫧", es: "GPT-5 mini 🫧", de: "GPT-5 mini 🎪", fr: "GPT-5 mini 🎪" },
  btn_image: { fa: "تولید تصویر 🍌", en: "Generate Image 🖼️", ar: "توليد صورة 🖼️", tr: "Görsel Oluştur 🖼️", ru: "Создать изображение 🖼️", es: "Generar imagen 🖼️", de: "Bild erzeugen 🖼️", fr: "Générer une image 🖼️" },
  btn_video: { fa: "تولید ویدیو 🎬", en: "Generate Video 🎬", ar: "توليد فيديو 🎬", tr: "Video Oluştur 🎬", ru: "Создать видео 🎬", es: "Generar video 🎬", de: "Video erstellen 🎬", fr: "Créer une vidéo 🎬" },
  btn_sora2: { fa: "Sora 2 🎪", en: "Sora 2 🎪", ar: "Sora 2 🎪", tr: "Sora 2 🎪", ru: "Sora 2 🎪", es: "Sora 2 🎪", de: "Sora 2 🎪", fr: "Sora 2 🎪" },
  btn_api_token: { fa: "API Token 🔑", en: "API Token 🔑", ar: "رمز API 🔑", tr: "API Anahtarı 🔑", ru: "API токен 🔑", es: "Token API 🔑", de: "API-Token 🔑", fr: "Jeton API 🔑" },
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
  tts_delete_voice: { fa: "🗑 حذف این صدا", en: "🗑 Delete this voice", ar: "🗑 حذف هذا الصوت", tr: "🗑 Bu sesi sil", ru: "🗑 Удалить этот голос", es: "🗑 Eliminar esta voz", de: "🗑 Diese Stimme löschen", fr: "🗑 Supprimer cette voix" },
  tts_delete_success: { fa: "✅ صدای '{voice}' حذف شد", en: "✅ '{voice}' was deleted", ar: "✅ تم حذف الصوت «{voice}»", tr: "✅ '{voice}' silindi", ru: "✅ Голос «{voice}» удалён", es: "✅ Se eliminó «{voice}»", de: "✅ „{voice}“ wurde gelöscht", fr: "✅ «{voice}» a été supprimée" },
  tts_delete_error: { fa: "❌ خطا در حذف صدا", en: "❌ Error deleting the voice", ar: "❌ حدث خطأ أثناء حذف الصوت", tr: "❌ Ses silinirken hata oluştu", ru: "❌ Ошибка при удалении голоса", es: "❌ Error al eliminar la voz", de: "❌ Fehler beim Löschen der Stimme", fr: "❌ Erreur lors de la suppression de la voix" },
  tts_voice_not_found: { fa: "صدا یافت نشد", en: "Voice not found", ar: "لم يتم العثور على الصوت", tr: "Ses bulunamadı", ru: "Голос не найден", es: "Voz no encontrada", de: "Stimme nicht gefunden", fr: "Voix introuvable" },
  tts_voice_disabled: { fa: "این صدا برای شما غیرفعال است.", en: "This voice is disabled for you.", ar: "هذا الصوت معطّل لك.", tr: "Bu ses sizin için devre dışı.", ru: "Этот голос для вас отключён.", es: "Esta voz está desactivada para ti.", de: "Diese Stimme ist für dich deaktiviert.", fr: "Cette voix est désactivée pour vous." },
  tts_processing: { fa: "👀 <b>در حال تبدیل...</b>", en: "⏳ Converting...", ar: "⏳ جارٍ التحويل...", tr: "⏳ Dönüştürülüyor...", ru: "⏳ Конвертация...", es: "⏳ Convirtiendo...", de: "⏳ Wird konvertiert...", fr: "⏳ Conversion..." },
  tts_no_credit: {
    fa: "⚠️ <b>کردیت کافی نیست</b>\n<b>موجودی شما: {credits} کردیت</b>\n<b>کردیت لازم: {required}</b>\n<b>می‌تونی کردیت بخری یا متن رو کوتاه‌تر کنی /help</b>",
    en: "⚠️ <b>Not enough credits</b>\n<b>Your balance: {credits} credits</b>\n<b>Required: {required} credits</b>\n<b>You can buy credits or send a shorter text /help</b>",
    ar: "⚠️ <b>الرصيد غير كافٍ</b>\n<b>رصيدك الحالي: {credits} رصيد</b>\n<b>المطلوب: {required} رصيد</b>\n<b>يمكنك شراء رصيد أو إرسال نص أقصر /help</b>",
    tr: "⚠️ <b>Yetersiz kredi</b>\n<b>Mevcut bakiyen: {credits} kredi</b>\n<b>Gerekli: {required} kredi</b>\n<b>Kredi satın alabilir veya daha kısa metin gönderebilirsin /help</b>",
    ru: "⚠️ <b>Недостаточно кредитов</b>\n<b>Текущий баланс: {credits} кредитов</b>\n<b>Нужно: {required} кредитов</b>\n<b>Можно пополнить баланс или отправить более короткий текст /help</b>",
    es: "⚠️ <b>Créditos insuficientes</b>\n<b>Saldo actual: {credits} créditos</b>\n<b>Requerido: {required} créditos</b>\n<b>Puedes comprar créditos o enviar un texto más corto /help</b>",
    de: "⚠️ <b>Nicht genug Guthaben</b>\n<b>Dein Kontostand: {credits} Credits</b>\n<b>Benötigt: {required} Credits</b>\n<b>Du kannst Guthaben kaufen oder einen kürzeren Text senden /help</b>",
    fr: "⚠️ <b>Crédits insuffisants</b>\n<b>Solde actuel : {credits} crédits</b>\n<b>Requis : {required} crédits</b>\n<b>Tu peux acheter des crédits ou envoyer un texte plus court /help</b>",
  },
  tts_error: { fa: "⚠️ <b>خطا در تبدیل٫ دوباره تلاش کن</b>", en: "⚠️ Conversion failed. Try again.", ar: "⚠️ فشل التحويل. جرب مرة أخرى.", tr: "⚠️ Dönüşüm hatası. Tekrar dene.", ru: "⚠️ Ошибка конвертации. Попробуйте снова.", es: "⚠️ Error de conversión. Inténtalo de nuevo.", de: "⚠️ Umwandlung fehlgeschlagen. Versuch's nochmal.", fr: "⚠️ Échec de conversion. Réessayez." },
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
  credit_invalid_plan: { fa: "بسته نامعتبر است.", en: "Invalid package.", ar: "الباقة غير صالحة.", tr: "Geçersiz paket.", ru: "Недействительный пакет.", es: "Paquete no válido.", de: "Ungültiges Paket.", fr: "Pack invalide." },
  credit_stars_menu: { fa: "🌟 شارژ آنی با Telegram Stars\n\nیکی از بسته‌های زیر را انتخاب کن:", en: "🌟 Instant top-up with Telegram Stars\n\nPick one of the packages below:", ar: "🌟 شحن فوري عبر Telegram Stars\n\nاختر إحدى الباقات أدناه:", tr: "🌟 Telegram Stars ile anında yükleme\n\nAşağıdaki paketlerden birini seç:", ru: "🌟 Мгновенное пополнение через Telegram Stars\n\nВыберите один из пакетов ниже:", es: "🌟 Recarga instantánea con Telegram Stars\n\nElige uno de los paquetes a continuación:", de: "🌟 Sofort aufladen mit Telegram Stars\n\nWähle eines der Pakete unten:", fr: "🌟 Recharge instantanée via Telegram Stars\n\nChoisis l'un des packs ci-dessous :" },
  credit_invoice_label: { fa: "{credits} کردیت", en: "{credits} credits", ar: "{credits} رصيداً", tr: "{credits} kredi", ru: "{credits} кредитов", es: "{credits} créditos", de: "{credits} Guthaben", fr: "{credits} crédits" },
  credit_invoice_title: { fa: "Vexa — خرید کردیت", en: "Vexa — Buy Credits", ar: "Vexa — شراء الرصيد", tr: "Vexa — Kredi Satın Al", ru: "Vexa — Покупка кредитов", es: "Vexa — Comprar créditos", de: "Vexa — Guthaben kaufen", fr: "Vexa — Acheter des crédits" },
  credit_invoice_desc: { fa: "شارژ موجودی با Telegram Stars.", en: "Top up your balance with Telegram Stars.", ar: "اشحن رصيدك عبر Telegram Stars.", tr: "Bakiyeni Telegram Stars ile doldur.", ru: "Пополните баланс через Telegram Stars.", es: "Recarga tu saldo con Telegram Stars.", de: "Lade dein Guthaben mit Telegram Stars auf.", fr: "Recharge ton solde avec Telegram Stars." },
  credit_pay_success: { fa: "✅ پرداخت موفق: ⭐{stars}\n🎉 {credits} کردیت اضافه شد.\n💳 موجودی فعلی: <b>{balance}</b>", en: "✅ Payment successful: ⭐{stars}\n🎉 Added {credits} credits.\n💳 Current balance: <b>{balance}</b>", ar: "✅ تم الدفع: ⭐{stars}\n🎉 تمت إضافة {credits} رصيدًا.\n💳 الرصيد الحالي: <b>{balance}</b>", tr: "✅ Ödeme başarılı: ⭐{stars}\n🎉 {credits} kredi eklendi.\n💳 Güncel bakiye: <b>{balance}</b>", ru: "✅ Оплата прошла: ⭐{stars}\n🎉 Добавлено {credits} кредитов.\n💳 Текущий баланс: <b>{balance}</b>", es: "✅ Pago exitoso: ⭐{stars}\n🎉 {credits} créditos añadidos.\n💳 Saldo actual: <b>{balance}</b>", de: "✅ Zahlung erfolgreich: ⭐{stars}\n🎉 {credits} Guthaben gutgeschrieben.\n💳 Aktueller Stand: <b>{balance}</b>", fr: "✅ Paiement réussi : ⭐{stars}\n🎉 {credits} crédits ajoutés.\n💳 Solde actuel : <b>{balance}</b>" },
  low_credit_warning: { fa: "کردیت‌ت رو به اتمامه.\nهر وقت خواستی شارژ کن تا راحت‌تر ادامه بدی.", en: "Your credits are running low.\nTop up anytime to keep going.", ar: "رصيدك على وشك النفاد.\nيمكنك الشحن في أي وقت للمتابعة.", tr: "Kredin bitmek üzere.\nDevam etmek için istediğin zaman yükleyebilirsin.", ru: "Кредиты заканчиваются.\nПополните баланс в любое время, чтобы продолжить.", es: "Tus créditos están por agotarse.\nRecarga cuando quieras para seguir.", de: "Deine Credits gehen zur Neige.\nLade jederzeit auf, um weiterzumachen.", fr: "Tes crédits sont presque épuisés.\nRecharge quand tu veux pour continuer." },
  low_credit_button: { fa: "خرید کردیت", en: "Buy credits", ar: "شراء الرصيد", tr: "Kredi satın al", ru: "Купить кредиты", es: "Comprar créditos", de: "Credits kaufen", fr: "Acheter des crédits" },
  force_sub_confirmed: { fa: "✅ عضویت تایید شد!", en: "✅ Subscription confirmed!", ar: "✅ تم تأكيد الاشتراك!", tr: "✅ Üyelik doğrulandı!", ru: "✅ Подписка подтверждена!", es: "✅ Suscripción confirmada.", de: "✅ Mitgliedschaft bestätigt!", fr: "✅ Inscription confirmée !" },
  force_sub_not_joined: { fa: "❌ هنوز عضو نشدی!", en: "❌ You're not a member yet!", ar: "❌ لم تنضم بعد!", tr: "❌ Henüz katılmadın!", ru: "❌ Вы ещё не подписались!", es: "❌ Aún no te has unido.", de: "❌ Du bist noch nicht beigetreten!", fr: "❌ Tu n'as pas encore rejoint !" },
  error_banned: { fa: "⛔️ دسترسی شما مسدود است.", en: "⛔️ Your access is blocked.", ar: "⛔️ تم حظر وصولك.", tr: "⛔️ Erişimin engellendi.", ru: "⛔️ Доступ заблокирован.", es: "⛔️ Tu acceso está bloqueado.", de: "⛔️ Dein Zugriff ist gesperrt.", fr: "⛔️ Ton accès est bloqué." },
  home_help: {
    fa: "<b>📖 راهنمای استفاده از Vexa</b>\n\n🔹 <b>کردیت یعنی چی؟</b>\nهر حرف، فاصله یا علامت = ۱ کردیت.\n\n🔹 <b>کردیت رایگان شروع</b>\nبعد از /start، <b>۴۵ کردیت</b> هدیه می‌گیری؛ برای تست کوتاه مثل «سلام، من Vexa هستم».\n\n🔹 <b>اگر پیام «موجودی کافی نیست» دیدی</b>\nمتن رو کوتاه‌تر کن یا اول موجودی رو شارژ کن.\n\n🔹 <b>نکات صداگیری طبیعی</b>\nاز علائم نگارشی استفاده کن:\n• جمله‌ها رو با نقطه جدا کن.\n• برای مکث کوتاه از ویرگول استفاده کن.\n• سوال‌ها رو با ؟ ببند.\n• برای هیجان از ! کمک بگیر.\n\n✍️ <b>مثال</b>\n• ❌ «سلام خوبی امیدوارم حالت خوب باشه»\n• ✅ «سلام! خوبی؟ امیدوارم حالت خوب باشه.»",
    en: "<b>📖 Using Vexa</b>\n\n🔹 <b>What are credits?</b>\nEach letter, space or symbol = 1 credit.\n\n🔹 <b>Free starter credits</b>\nAfter /start you receive <b>45 credits</b>; enough to try “Hi, I'm Vexa.”\n\n🔹 <b>Not enough credit?</b>\nSend a shorter text or top up first.\n\n🔹 <b>Tips for a natural voice</b>\nUse punctuation for better pauses:\n• Separate sentences with periods.\n• Add commas for short breaks.\n• Finish questions with ?.\n• Add ! for excitement.\n\n✍️ <b>Example</b>\n• ❌ \"hi hope you are well\"\n• ✅ \"Hi! How are you? Hope you're well.\"",
  },
  profile_title: { fa: "پروفایل", en: "Profile", ar: "الملف الشخصي", tr: "Profil", ru: "Профиль", es: "Perfil", de: "Profil", fr: "Profil" },
  profile_body: { fa: "👤 <b>ID : <code>{uid}</code></b>\n💳 <b>Credit : {credits}</b>", en: "👤 ID: {uid}\n💳 Credits: {credits}", ar: "👤 المعرف: {uid}\n💳 الرصيد: {credits}", tr: "👤 ID: {uid}\n💳 Kredi: {credits}", ru: "👤 ID: {uid}\n💳 Кредиты: {credits}", es: "👤 ID: {uid}\n💳 Créditos: {credits}", de: "👤 ID: {uid}\n💳 Guthaben: {credits}", fr: "👤 ID : {uid}\n💳 Crédits : {credits}" },
  api_token_body: {
    fa: "🔐 <b>کلید API مخصوص تو</b>\n<code>{token}</code>\n\nبرای هر درخواست این هدر را اضافه کن:\n<code>X-API-Key: {token}</code>\n\n✅ اندپوینت‌های فعال:\n• <b>POST /v1/image</b> → تولید عکس (۵ کردیت)\n• <b>POST /v1/tts</b> → تبدیل متن به صدا (۰٫۰۵ کردیت به ازای هر کاراکتر)\n\nخروجی تولید عکس لینک مستقیم است و صدای TTS به صورت base64 برمی‌گردد. مصرف کردیت از همان موجودی ربات انجام می‌شود.",
    en: "🔐 <b>Your API token</b>\n<code>{token}</code>\n\nAdd this header to every request:\n<code>X-API-Key: {token}</code>\n\n✅ Available endpoints:\n• <b>POST /v1/image</b> – generate an image (5 credits)\n• <b>POST /v1/tts</b> – text to speech (0.05 credit per character)\n\nImage responses return a direct URL and TTS responses include base64 audio. Credits are deducted from your bot balance.",
  },
  api_token_rotate: { fa: "تولید کلید جدید ♻️", en: "Generate new token ♻️", ar: "تجديد الرمز ♻️", tr: "Yeni anahtar üret ♻️", ru: "Сгенерировать новый токен ♻️", es: "Generar nuevo token ♻️", de: "Neuen Token erzeugen ♻️", fr: "Générer un nouveau jeton ♻️" },
  api_token_rotated: { fa: "🔄 کلید جدید ساخته شد", en: "🔄 New token generated", ar: "🔄 تم إنشاء رمز جديد", tr: "🔄 Yeni anahtar oluşturuldu", ru: "🔄 Создан новый токен", es: "🔄 Nuevo token generado", de: "🔄 Neuer Token erstellt", fr: "🔄 Nouveau jeton créé" },
  invite_title: { fa: "دعوت دوستان 🎁", en: "Invite Friends 🎁", ar: "دعوة الأصدقاء 🎁", tr: "Arkadaş Davet Et 🎁", ru: "Пригласить друзей 🎁", es: "Invitar amigos 🎁", de: "Freunde einladen 🎁", fr: "Inviter des amis 🎁" },
  invite_body: { fa: "شناسه عددی شما: <code>{user_id}</code>\nتعداد دعوت‌ها تا الان: <b>{invited}</b>\n\nلینک دعوت شما:\n<code>{ref}</code>\n\n<b>به ازای هر دعوت : +{bonus} کردیت</b>", en: "Your numeric ID: <code>{user_id}</code>\nInvites so far: <b>{invited}</b>\n\nYour invite link:\n<code>{ref}</code>\nPer invite: {bonus} credits", ar: "معرّفك الرقمي: <code>{user_id}</code>\nعدد الدعوات حتى الآن: <b>{invited}</b>\n\nرابط دعوتك:\n<code>{ref}</code>\nلكل دعوة: {bonus} رصيد", tr: "Sayısal kimliğin: <code>{user_id}</code>\nŞu ana kadar davet: <b>{invited}</b>\n\nDavet bağlantın:\n<code>{ref}</code>\nDavet başına: {bonus} kredi", ru: "Ваш числовой ID: <code>{user_id}</code>\nПриглашений на данный момент: <b>{invited}</b>\n\nВаша ссылка:\n<code>{ref}</code>\nЗа приглашение: {bonus} кредитов", es: "Tu ID numérico: <code>{user_id}</code>\nInvitaciones hasta ahora: <b>{invited}</b>\n\nTu enlace de invitación:\n<code>{ref}</code>\nPor invitación: {bonus} créditos", de: "Deine numerische ID: <code>{user_id}</code>\nEinladungen bisher: <b>{invited}</b>\n\nDein Einladungslink:\n<code>{ref}</code>\nPro Einladung: {bonus} Guthaben", fr: "Ton ID numérique : <code>{user_id}</code>\nInvitations jusqu’à présent : <b>{invited}</b>\n\nTon lien d'invitation :\n<code>{ref}</code>\nPar invitation : {bonus} crédits" },
  invite_daily_reward: { fa: "دریافت پاداش روزانه 🎁", en: "Claim daily reward 🎁", ar: "استلام مكافأة يومية 🎁", tr: "Günlük ödülü al 🎁", ru: "Получить дневной бонус 🎁", es: "Reclamar recompensa diaria 🎁", de: "Tägliche Belohnung holen 🎁", fr: "Obtenir la récompense quotidienne 🎁" },
  invite_daily_reward_success: { fa: "🎉 امروز {amount} کردیت به عنوان پاداش روزانه گرفتی!", en: "🎉 You received {amount} credits as today's daily reward!", ar: "🎉 حصلت اليوم على {amount} رصيد كمكافأة يومية!", tr: "🎉 Bugünkü günlük ödül olarak {amount} kredi kazandın!", ru: "🎉 Ты получил сегодня {amount} кредитов как ежедневный бонус!", es: "🎉 ¡Recibiste {amount} créditos como recompensa diaria de hoy!", de: "🎉 Du hast heute {amount} Credits als tägliche Belohnung erhalten!", fr: "🎉 Tu as reçu {amount} crédits comme récompense quotidienne d'aujourd'hui !" },
  invite_daily_reward_cooldown: { fa: "⏳ قبلاً پاداش امروز رو گرفتی. بعد از {time} دوباره تلاش کن.", en: "⏳ You've already claimed today's reward. Try again in {time}.", ar: "⏳ لقد استلمت مكافأة اليوم بالفعل. جرّب بعد {time}.", tr: "⏳ Bugünkü ödülü zaten aldın. {time} sonra tekrar dene.", ru: "⏳ Ты уже получил сегодняшний бонус. Попробуй снова через {time}.", es: "⏳ Ya reclamaste la recompensa de hoy. Vuelve en {time}.", de: "⏳ Du hast die heutige Belohnung schon erhalten. Versuche es in {time} erneut.", fr: "⏳ Tu as déjà récupéré la récompense d'aujourd'hui. Réessaie dans {time}." },
  onboarding_welcome: { fa: "🎁 {credits} کردیت رایگان گرفتی\n≈ ۱۵ ثانیه صدای هوش مصنوعی\nالان امتحانش کن 👇", en: "🎁 You’ve received {credits} free credits\n≈ 15 Seconds of AI voice\nTry it now 👇", ar: "🎁 لقد حصلت على {credits} رصيد مجاني\n≈ 15 ثوانٍ من صوت الذكاء الاصطناعي\nجرّبه الآن 👇", tr: "🎁 {credits} ücretsiz kredi kazandın\n≈ 15 saniye yapay zekâ sesi\nHemen dene 👇", ru: "🎁 Вы получили {credits} бесплатных кредитов\n≈ 15 секунд AI-голоса\nПопробуйте сейчас 👇", es: "🎁 Recibiste {credits} créditos gratis\n≈ 15 segundos de voz con IA\nPruébalo ahora 👇", de: "🎁 Du hast {credits} kostenlose Credits erhalten\n≈ 15 Sekunden KI-Stimme\nJetzt ausprobieren 👇", fr: "🎁 Tu as reçu {credits} crédits gratuits\n≈ 15 secondes de voix IA\nEssaie maintenant 👇" },
  onboarding_daily_bonus_ready: { fa: "🎁 پاداش روزانه آماده است!\nبرای دریافت کردیت رایگان روی دکمه زیر بزن.", en: "🎁 Daily bonus is ready!\nTap below to claim your free credits.", ar: "🎁 المكافأة اليومية جاهزة!\nاضغط بالأسفل لتحصل على رصيدك المجاني.", tr: "🎁 Günlük bonus hazır!\nÜcretsiz kredini almak için aşağıya dokun.", ru: "🎁 Ежедневный бонус готов!\nНажмите ниже, чтобы получить бесплатные кредиты.", es: "🎁 ¡La bonificación diaria está lista!\nToca abajo para reclamar tus créditos gratis.", de: "🎁 Die tägliche Belohnung ist bereit!\nTippe unten, um deine Gratis-Credits zu erhalten.", fr: "🎁 Le bonus quotidien est prêt !\nAppuie ci-dessous pour récupérer tes crédits gratuits." },
  onboarding_daily_bonus_unlocked: { fa: "🎁 پاداش روزانه باز شد 🙂\nکردیت رایگان منتظرته.\nبرای دریافت بزن.", en: "🎁 Daily bonus unlocked 🙂\nFree credits are waiting for you.\nTap to collect.", ar: "🎁 تم فتح المكافأة اليومية 🙂\nالرصيد المجاني بانتظارك.\nاضغط للتحصيل.", tr: "🎁 Günlük bonus açıldı 🙂\nÜcretsiz krediler seni bekliyor.\nAlmak için dokun.", ru: "🎁 Ежедневный бонус открыт 🙂\nБесплатные кредиты ждут тебя.\nНажми, чтобы получить.", es: "🎁 Bono diario desbloqueado 🙂\nHay créditos gratis esperándote.\nToca para recoger.", de: "🎁 Täglicher Bonus freigeschaltet 🙂\nGratis-Credits warten auf dich.\nTippe zum Einsammeln.", fr: "🎁 Bonus quotidien débloqué 🙂\nDes crédits gratuits t’attendent.\nAppuie pour récupérer." },
  onboarding_bonus_button: { fa: "🎁", en: "🎁", ar: "🎁", tr: "🎁", ru: "🎁", es: "🎁", de: "🎁", fr: "🎁" },
  gpt_open: { fa: "<b>GPT-5 mini آماده است 🙂</b>\n<b>پیامت رو پایین بنویس</b>", en: "<b>GPT-5 mini is ready 🙂</b>\n<b>Send your message below</b>", ar: "<b>GPT-5 mini جاهز 🙂</b>\n<b>اكتب رسالتك بالأسفل</b>", tr: "<b>GPT-5 mini hazır 🙂</b>\n<b>Mesajını aşağıya yaz</b>", ru: "<b>GPT-5 mini готов 🙂</b>\n<b>Напиши сообщение ниже</b>", es: "<b>GPT-5 mini está listo 🙂</b>\n<b>Escribe tu mensaje abajo</b>", de: "<b>GPT-5 mini ist bereit 🙂</b>\n<b>Schreibe deine Nachricht unten</b>", fr: "<b>GPT-5 mini est prêt 🙂</b>\n<b>Écris ton message ci-dessous</b>" },
  gpt_end: { fa: "✅ <b>فعلاً تا همین‌جا! هر وقت خواستی برگرد گپ بزنیم.</b>", en: "✅ <b>Chat ended for now. Come back anytime.</b>", ar: "✅ <b>تم إنهاء الدردشة حالياً. عد في أي وقت.</b>", tr: "✅ <b>Sohbet şimdilik bitti. İstediğin zaman dön.</b>", ru: "✅ <b>Чат завершён. Возвращайся в любое время.</b>", es: "✅ <b>Chat finalizado por ahora. Vuelve cuando quieras.</b>", de: "✅ <b>Chat vorerst beendet. Komm jederzeit zurück.</b>", fr: "✅ <b>Discussion terminée pour le moment. Reviens quand tu veux.</b>" },
  gpt_end_button: { fa: "✅ اتمام چت", en: "✅ End chat", ar: "✅ إنهاء الدردشة", tr: "✅ Sohbeti bitir", ru: "✅ Завершить чат", es: "✅ Finalizar chat", de: "✅ Chat beenden", fr: "✅ Terminer le chat" },
  gpt_wait: { fa: "🫧 <b>درحال فکر کردن...</b>", en: "🫧 <b>Thinking...</b>", ar: "🫧 <b>جارٍ التفكير...</b>", tr: "🫧 <b>Düşünüyor...</b>", ru: "🫧 <b>Думаю...</b>", es: "🫧 <b>Pensando...</b>", de: "🫧 <b>Denke nach...</b>", fr: "🫧 <b>Je réfléchis...</b>" },
  image_intro: { fa: "🖼️ <b>هرچی میخوای بنویس تا برات بسازمش.</b>\nهر تصویر 1 کردیت از حسابت کم میشه.", en: "🖼️ <b>Describe anything you want and I'll make it.</b>\nEach image costs 1 credit.", ar: "🖼️ <b>اكتب أي شيء تريده وسأصنعه لك.</b>\nكل صورة تخصم 1 رصيد.", tr: "🖼️ <b>Ne istersen yaz, senin için oluşturayım.</b>\nHer görsel için 1 kredi düşer.", ru: "🖼️ <b>Опиши всё, что хочешь — я создам это.</b>\nЗа каждое изображение списывается 1 кредит.", es: "🖼️ <b>Describe lo que quieras y lo crearé para ti.</b>\nCada imagen cuesta 1 crédito.", de: "🖼️ <b>Beschreibe, was du willst, und ich setze es um.</b>\nFür jedes Bild wird 1 Credit abgezogen.", fr: "🖼️ <b>Décris ce que tu veux et je le créerai pour toi.</b>\nChaque image coûte 1 crédit." },
  image_processing: { fa: "🎨 <b>در حال ساخت تصویر...</b>", en: "🎨 <b>Generating the image...</b>", ar: "🎨 <b>جارٍ توليد الصورة...</b>", tr: "🎨 <b>Görsel oluşturuluyor...</b>", ru: "🎨 <b>Создаю изображение...</b>", es: "🎨 <b>Generando la imagen...</b>", de: "🎨 <b>Bild wird erstellt...</b>", fr: "🎨 <b>Génération de l'image...</b>" },
  image_need_prompt: { fa: "⚠️ لطفاً برای این عکس یه توضیح متنی هم بنویس تا بدونم چه تغییری می‌خوای.", en: "⚠️ Please add a short caption describing the change you want.", ar: "⚠️ أضف وصفاً نصياً للصورة حتى أعرف التعديل المطلوب.", tr: "⚠️ Lütfen istediğin değişikliği anlatan kısa bir açıklama yaz.", ru: "⚠️ Добавьте текстовое описание, чтобы понять, что изменить.", es: "⚠️ Añade un texto que describa el cambio que quieres.", de: "⚠️ Bitte füge eine kurze Beschreibung hinzu, welche Änderung du möchtest.", fr: "⚠️ Ajoute une courte description de la modification souhaitée." },
  video_gen4_intro: { fa: "🎬 <b>عکس بفرست تا برات ویدیو بسازم.</b>\nهر ویدیو 1 کردیت هزینه دارد.\nمی‌تونی همراه عکس کپشن هم بفرستی تا حرکت رو توضیح بدی.", en: "🎬 <b>Send a photo and I'll turn it into a video.</b>\nEach video costs 1 credit.\nYou can add a caption to guide the motion.", ar: "🎬 <b>أرسل صورة وسأحوّلها إلى فيديو.</b>\nكل فيديو يكلف 1 رصيد.\nيمكنك إضافة تعليق لشرح الحركة.", tr: "🎬 <b>Bir fotoğraf gönder, senin için videoya çevireyim.</b>\nHer video 1 krediye mal olur.\nHareketi yönlendirmek için açıklama ekleyebilirsin.", ru: "🎬 <b>Пришли фото — я превращу его в видео.</b>\nКаждое видео стоит 1 кредит.\nМожешь добавить подпись, чтобы задать движение.", es: "🎬 <b>Envía una foto y la convertiré en video.</b>\nCada video cuesta 1 crédito.\nPuedes añadir una leyenda para guiar el movimiento.", de: "🎬 <b>Sende ein Foto und ich mache daraus ein Video.</b>\nJedes Video kostet 1 Credit.\nDu kannst eine Bildunterschrift hinzufügen, um die Bewegung zu steuern.", fr: "🎬 <b>Envoie une photo et je la transforme en vidéo.</b>\nChaque vidéo coûte 1 crédit.\nTu peux ajouter une légende pour guider le mouvement." },
  video_gen4_processing: { fa: "🎥 <b>در حال ساخت ویدیو...</b>", en: "🎥 <b>Generating the video...</b>", ar: "🎥 <b>جارٍ إنشاء الفيديو...</b>", tr: "🎥 <b>Video oluşturuluyor...</b>", ru: "🎥 <b>Создаю видео...</b>", es: "🎥 <b>Generando el video...</b>", de: "🎥 <b>Video wird erstellt...</b>", fr: "🎥 <b>Génération de la vidéo...</b>" },
  video_gen4_need_image: { fa: "⚠️ لطفاً یک عکس بفرست تا ویدیو بسازم.", en: "⚠️ Please send a photo so I can create a video.", ar: "⚠️ أرسل صورة من فضلك ليتم إنشاء الفيديو.", tr: "⚠️ Lütfen video oluşturmak için bir fotoğraf gönder.", ru: "⚠️ Пожалуйста, пришлите фото, чтобы я сделал видео.", es: "⚠️ Por favor envía una foto para crear el video.", de: "⚠️ Bitte sende ein Foto, damit ich ein Video erstellen kann.", fr: "⚠️ Merci d'envoyer une photo pour que je puisse créer la vidéo." },
  clone_menu: { fa: "🧬 <b>ساخت صدای شخصی – Voice Clone</b>\n\n<b>یک ویس کوتاه به‌صورت فایل (۱۵–۳۰ ثانیه) ارسال کن تا همان صدا را بسازیم.</b>", en: "🧬 <b>Create your personal voice – Voice Clone</b>\n\n<b>Send a short voice message (15–30 seconds) to start.</b>", ar: "🧬 <b>أنشئ صوتك الشخصي – استنساخ الصوت</b>\n\n<b>أرسل رسالة صوتية قصيرة (15–30 ثانية) للبدء.</b>", tr: "🧬 <b>Kişisel sesini oluştur – Voice Clone</b>\n\n<b>Başlamak için 15–30 saniyelik kısa bir ses mesajı gönder.</b>", ru: "🧬 <b>Создай свой голос – Voice Clone</b>\n\n<b>Отправь короткое голосовое сообщение (15–30 секунд), чтобы начать.</b>", es: "🧬 <b>Crea tu voz personal – Voice Clone</b>\n\n<b>Envía un mensaje de voz corto (15–30 segundos) para comenzar.</b>", de: "🧬 <b>Erstelle deine eigene Stimme – Voice Clone</b>\n\n<b>Sende eine kurze Sprachnachricht (15–30 Sekunden), um zu starten.</b>", fr: "🧬 <b>Crée ta voix personnelle – Voice Clone</b>\n\n<b>Envoie un court message vocal (15–30 secondes) pour commencer.</b>" },
  clone_ask_name: { fa: "➕ <b>حالا یک اسم برای صدای جدیدت بفرست.</b>", en: "➕ <b>Now send a name for your new voice.</b>", ar: "➕ <b>أرسل اسماً للصوت الجديد.</b>", tr: "➕ <b>Yeni sesin için bir isim gönder.</b>", ru: "➕ <b>Теперь отправьте имя для нового голоса.</b>", es: "➕ <b>Ahora envía un nombre para tu nueva voz.</b>", de: "➕ <b>Sende jetzt einen Namen für deine neue Stimme.</b>", fr: "➕ <b>Envoie maintenant un nom pour ta nouvelle voix.</b>" },
  clone_audio_missing: { fa: "⚠️ فایل صوتی پیدا نشد؛ دوباره فایل را ارسال کن.", en: "⚠️ Audio file not found. Please send it again.", ar: "⚠️ لم يتم العثور على الملف الصوتي. أرسله مرة أخرى.", tr: "⚠️ Ses dosyası bulunamadı; lütfen tekrar gönder.", ru: "⚠️ Аудиофайл не найден. Пожалуйста, отправьте его снова.", es: "⚠️ No se encontró el archivo de audio. Envíalo de nuevo.", de: "⚠️ Audiodatei nicht gefunden. Bitte sende sie erneut.", fr: "⚠️ Fichier audio introuvable. Merci de le renvoyer." },
  clone_success: { fa: "✅ درخواست ساخت صدای شخصی ثبت شد. بعد از آماده‌شدن اطلاع می‌گیری.", en: "✅ Your voice-clone request has been submitted. You’ll be notified when it’s ready.", ar: "✅ تم تسجيل طلب استنساخ الصوت. سنبلغك عند الجاهزية.", tr: "✅ Ses klonlama isteğin kaydedildi. Hazır olunca bilgilendirileceksin.", ru: "✅ Запрос на создание персонального голоса отправлен. Мы сообщим, когда будет готово.", es: "✅ Tu solicitud de clon de voz fue enviada. Te avisaremos cuando esté lista.", de: "✅ Deine Voice-Clone-Anfrage wurde eingereicht. Du wirst benachrichtigt, sobald sie fertig ist.", fr: "✅ Ta demande de clonage vocal a été enregistrée. Tu seras notifié quand ce sera prêt." },
  tts_banned_words: { fa: "❌ این کلمات قابل تبدیل نیستند. لطفاً متن دیگری استفاده کن.", en: "❌ This text contains blocked words. Please use different wording.", ar: "❌ هذا النص يحتوي على كلمات محظورة. الرجاء استخدام نص آخر.", tr: "❌ Bu metin yasaklı kelimeler içeriyor. Lütfen farklı bir metin kullan.", ru: "❌ В тексте есть запрещённые слова. Пожалуйста, сформулируйте иначе.", es: "❌ Este texto contiene palabras bloqueadas. Usa otro texto, por favor.", de: "❌ Dieser Text enthält gesperrte Wörter. Bitte formuliere ihn anders.", fr: "❌ Ce texte contient des mots interdits. Merci d'utiliser un autre texte." },
  force_sub_title: { fa: "<b>برای ادامه عضو کانال شو</b>", en: "<b>Join our channel to continue</b>", ar: "<b>انضم إلى القناة للمتابعة</b>", tr: "<b>Devam etmek için kanala katıl</b>", ru: "<b>Чтобы продолжить, вступи в канал</b>", es: "<b>Únete al canal para continuar</b>", de: "<b>Tritt dem Kanal bei, um weiterzumachen</b>", fr: "<b>Rejoins la chaîne pour continuer</b>" },
  force_sub_join_channel: { fa: "• کانال تلگرام", en: "• Telegram channel", ar: "• قناة تيليجرام", tr: "• Telegram kanalı", ru: "• Канал в Telegram", es: "• Canal de Telegram", de: "• Telegram-Kanal", fr: "• Chaîne Telegram" },
  force_sub_join_instagram: { fa: "• صفحه اینستاگرام", en: "• Instagram page", ar: "• صفحة إنستغرام", tr: "• Instagram sayfası", ru: "• Страница в Instagram", es: "• Página de Instagram", de: "• Instagram-Seite", fr: "• Page Instagram" },
  force_sub_hint: { fa: "بعد از عضویت روی دکمه «عضو شدم» بزن.", en: "After joining, tap \"I joined\" to continue.", ar: "بعد الانضمام اضغط زر \"انضممت\" للمتابعة.", tr: "Katıldıktan sonra \"Katıldım\" düğmesine bas.", ru: "После вступления нажми «Я вступил(а)».", es: "Después de unirte, toca \"Ya me uní\" para continuar.", de: "Nach dem Beitritt tippe auf \"Ich bin beigetreten\".", fr: "Après avoir rejoint, appuie sur \"Je me suis abonné\" pour continuer." },
  force_sub_btn_join_channel: { fa: "عضویت در کانال 🚀", en: "Join channel 🚀", ar: "انضمام إلى القناة 🚀", tr: "Kanala katıl 🚀", ru: "Вступить в канал 🚀", es: "Unirme al canal 🚀", de: "Kanal beitreten 🚀", fr: "Rejoindre la chaîne 🚀" },
  force_sub_btn_follow_instagram: { fa: "دنبال کردن اینستاگرام 📱", en: "Follow on Instagram 📱", ar: "متابعة إنستغرام 📱", tr: "Instagram'ı takip et 📱", ru: "Подписаться в Instagram 📱", es: "Seguir en Instagram 📱", de: "Instagram folgen 📱", fr: "Suivre sur Instagram 📱" },
  force_sub_btn_joined: { fa: "عضو شدم ✅", en: "I joined ✅", ar: "انضممت ✅", tr: "Katıldım ✅", ru: "Я вступил ✅", es: "Ya me uní ✅", de: "Ich bin beigetreten ✅", fr: "Je me suis abonné ✅" },
  receipt_waiting_confirm: { fa: "✅ رسید دریافت شد\n⏳ <b>...درحال بررسـی</b>", en: "✅ Receipt received\n⏳ <b>Under review...</b>", ar: "✅ تم استلام الإيصال\n⏳ <b>جارٍ المراجعة...</b>", tr: "✅ Dekont alındı\n⏳ <b>İnceleniyor...</b>", ru: "✅ Чек получен\n⏳ <b>Проверяем...</b>", es: "✅ Recibo recibido\n⏳ <b>En revisión...</b>", de: "✅ Beleg erhalten\n⏳ <b>Wird geprüft...</b>", fr: "✅ Reçu reçu\n⏳ <b>En cours de vérification...</b>" },
  sora2_btn_buy: { fa: "خرید کد دعوت 🎟️", en: "Buy invite code 🎟️", ar: "شراء رمز الدعوة 🎟️", tr: "Davet kodu satın al 🎟️", ru: "Купить код-приглашение 🎟️", es: "Comprar código de invitación 🎟️", de: "Einladungscode kaufen 🎟️", fr: "Acheter un code d'invitation 🎟️" },
  sora2_no_credit_alert: { fa: "⚠️ کردیت کافی نیست.", en: "⚠️ Not enough credits.", ar: "⚠️ لا يوجد رصيد كافٍ.", tr: "⚠️ Yeterli kredin yok.", ru: "⚠️ Недостаточно кредитов.", es: "⚠️ Créditos insuficientes.", de: "⚠️ Nicht genug Credits.", fr: "⚠️ Crédits insuffisants." },
};
const t = (key: string, lang: string) => I18N[key]?.[lang] || I18N[key]?.fa || key;
const ADMIN_TITLE = "🛠 پنل ادمین";
const ADMIN_MENU_TEXT = `از دکمه‌های زیر استفاده کنید:
• آمار، کاربران، پیام‌رسانی
• افزایش/کسر کردیت
• تنظیمات و خروجی‌ها`;
const ADMIN_DENY_TEXT = "⛔️ شما دسترسی به پنل ادمین ندارید.";
const ADMIN_DONE_TEXT = "✅ انجام شد.";
const BANNED_WORDS = ["کوص"];
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
    if (user.banned) {
      await this.sendMessage(msg.chat.id, t("error_banned", lang));
      await this.markProcessed(update, user.userId, "banned");
      return { handled: "banned" };
    }

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
    if (user.banned) {
      await this.answerCallback(callback.id, t("error_banned", lang), true);
      return { handled: "banned" };
    }

    if (data.startsWith("admin:")) {
      return this.handleAdminCallback(callback.id, chatId, messageId, user.userId, data);
    }

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
    if (data === "lang:back" || data === "profile:back" || data === "video:back") {
      await this.sendMainMenu(chatId, messageId, lang);
      await this.answerCallback(callback.id);
      return { handled: "legacy_back" };
    }
    if (data === "home:profile") {
      const credits = (await this.deps.credits.getCredits(user.userId)).credits;
      await this.answerCallback(callback.id, `${t("profile_title", lang)}\n\n${t("profile_body", lang).replace(/<[^>]+>/g, "").replace("{uid}", String(user.userId)).replace("{credits}", String(credits))}`, true);
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
      await this.sendApiTokenMenu(chatId, token, lang, messageId);
      await this.answerCallback(callback.id);
      return { handled: "api_token" };
    }
    if (data === "api:rotate") {
      const token = await this.deps.tokens.rotate(user.userId);
      await this.sendApiTokenMenu(chatId, token, lang, messageId);
      await this.answerCallback(callback.id, t("api_token_rotated", lang));
      return { handled: "api_rotate" };
    }
    if (data === "home:lang") {
      await this.sendLanguageMenu(chatId, lang, messageId, false, true);
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
      await this.sendMessage(chatId, t("gpt_open", lang), "HTML", undefined, {
        keyboard: [[{ text: t("gpt_end_button", lang) }]],
        resize_keyboard: true,
      });
      await this.answerCallback(callback.id);
      return { handled: "gpt_open" };
    }
    if (data === "home:tts") {
      const selected = await this.resolveTtsVoiceSelection(user.userId, lang, state.ttsVoice || DEFAULT_VOICE_NAME_BY_LANG[lang] || DEFAULT_VOICE_NAME_BY_LANG.fa);
      await this.deps.userState.setBotState(user.userId, { ...state, mode: "tts:wait_text", updatedAt: nowTs(), ttsVoice: selected, ttsOutput: state.ttsOutput || "mp3", ttsPage: state.ttsPage || 0 });
      await this.sendMessage(chatId, this.ttsAskText(lang, selected), "HTML", await this.ttsKeyboard(lang, user.userId, selected, state.ttsOutput || "mp3", state.ttsPage || 0));
      await this.answerCallback(callback.id);
      return { handled: "tts_open" };
    }
    if (data.startsWith("tts:voice:")) {
      const name = data.split(":").slice(2).join(":");
      const selected = await this.resolveTtsVoiceSelection(user.userId, lang, name);
      if (selected !== name) {
        const exists = await this.ttsVoiceExists(user.userId, lang, name);
        await this.answerCallback(callback.id, t(exists ? "tts_voice_disabled" : "tts_voice_not_found", lang));
        return { handled: exists ? "tts_voice_disabled" : "tts_voice_missing" };
      }
      const st = await this.deps.userState.getBotState(user.userId);
      await this.deps.userState.setBotState(user.userId, { ...st, mode: "tts:wait_text", updatedAt: nowTs(), ttsVoice: selected });
      await this.sendOrEditMessage(chatId, this.ttsAskText(lang, selected), await this.ttsKeyboard(lang, user.userId, selected, st.ttsOutput || "mp3", st.ttsPage || 0), messageId, "HTML");
      await this.answerCallback(callback.id, selected);
      return { handled: "tts_voice" };
    }
    if (data.startsWith("tts:page:")) {
      const st = await this.deps.userState.getBotState(user.userId);
      const step = data.endsWith(":next") ? 1 : -1;
      const nextPage = Math.max(0, (st.ttsPage || 0) + step);
      await this.deps.userState.setBotState(user.userId, { ...st, ttsPage: nextPage, updatedAt: nowTs() });
      const selected = await this.resolveTtsVoiceSelection(user.userId, lang, st.ttsVoice || DEFAULT_VOICE_NAME_BY_LANG[lang] || DEFAULT_VOICE_NAME_BY_LANG.fa);
      await this.sendOrEditMessage(chatId, this.ttsAskText(lang, selected), await this.ttsKeyboard(lang, user.userId, selected, st.ttsOutput || "mp3", nextPage), messageId, "HTML");
      await this.answerCallback(callback.id);
      return { handled: "tts_page" };
    }
    if (data.startsWith("tts:demo:")) {
      const voice = data.split(":").slice(2).join(":") || "";
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
      const voice = await this.resolveTtsVoiceSelection(user.userId, lang, state.ttsVoice || DEFAULT_VOICE_NAME_BY_LANG[lang] || DEFAULT_VOICE_NAME_BY_LANG.fa);
      await this.deps.userState.setBotState(user.userId, { ...state, mode: "tts:wait_text", updatedAt: nowTs(), ttsOutput: output });
      await this.sendOrEditMessage(chatId, this.ttsAskText(lang, voice), await this.ttsKeyboard(lang, user.userId, voice, output, state.ttsPage || 0), messageId, "HTML");
      await this.answerCallback(callback.id);
      return { handled: "tts_output" };
    }
    if (data.startsWith("tts:delete:")) {
      const voiceName = data.split(":").slice(2).join(":");
      try {
        const customVoices = await this.listUserCustomVoices(user.userId);
        if (!customVoices.some((voice) => voice.name === voiceName)) {
          await this.answerCallback(callback.id, t("tts_voice_not_found", lang));
          return { handled: "tts_delete_missing" };
        }
        await this.deleteUserCustomVoice(user.userId, voiceName);
        const st = await this.deps.userState.getBotState(user.userId);
        const selected = await this.resolveTtsVoiceSelection(user.userId, lang, DEFAULT_VOICE_NAME_BY_LANG[lang] || DEFAULT_VOICE_NAME_BY_LANG.fa);
        await this.deps.userState.setBotState(user.userId, { ...st, mode: "tts:wait_text", ttsVoice: selected, updatedAt: nowTs() });
        await this.sendOrEditMessage(chatId, this.ttsAskText(lang, selected), await this.ttsKeyboard(lang, user.userId, selected, st.ttsOutput || "mp3", st.ttsPage || 0), messageId, "HTML");
        await this.answerCallback(callback.id, t("tts_delete_success", lang).replace("{voice}", voiceName));
      } catch {
        await this.answerCallback(callback.id, t("tts_delete_error", lang));
      }
      return { handled: "tts_delete" };
    }
    if (data === "home:clone") {
      await this.deps.userState.setBotState(user.userId, { mode: "clone:wait_audio", updatedAt: nowTs() });
      await this.sendMessage(
        chatId,
        t("clone_menu", lang),
        "HTML",
        { inline_keyboard: [[{ text: t("back", lang), callback_data: "home:back" }]] }
      );
      await this.answerCallback(callback.id);
      return { handled: "clone_open" };
    }
    if (data === "home:image") {
      await this.deps.userState.setBotState(user.userId, { mode: "image:wait_prompt", updatedAt: nowTs() });
      await this.sendMessage(chatId, t("image_intro", lang), "HTML", {
        inline_keyboard: [[{ text: t("back", lang), callback_data: "image:back" }]],
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
      await this.sendMessage(chatId, t("video_gen4_intro", lang), "HTML", {
        inline_keyboard: [[{ text: t("back", lang), callback_data: "video_gen4:back" }]],
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
        await this.answerCallback(callback.id, t("invite_daily_reward_cooldown", lang).replace("{time}", `${minutes} min`), true);
        return { handled: "daily_reward_cooldown" };
      }
      await this.deps.credits.grant(user.userId, 10, "invite_daily_reward", "telegram_bot");
      await this.deps.userState.setBotState(user.userId, { ...state, dailyRewardClaimedAt: nowTs(), updatedAt: nowTs() });
      await this.answerCallback(callback.id, t("invite_daily_reward_success", lang).replace("{amount}", "10"), true);
      await this.sendInviteMenu(chatId, user.userId);
      return { handled: "daily_reward_claim" };
    }
    if (data === "onboarding:invite") {
      await this.sendInviteMenu(chatId, user.userId);
      await this.answerCallback(callback.id);
      return { handled: "onboarding_invite" };
    }
    if (data === "home:sora2" || data === "sora2:menu") {
      await this.sendSora2Menu(chatId, lang, messageId);
      await this.answerCallback(callback.id);
      return { handled: "sora2_menu" };
    }
    if (data === "sora2:buy") {
      const credits = (await this.deps.credits.getCredits(user.userId)).credits;
      if (credits < SORA2_COST) {
        await this.sendSora2NoCredit(chatId, lang, messageId, credits);
        await this.answerCallback(callback.id, t("sora2_no_credit_alert", lang), true);
        return { handled: "sora2_no_credit" };
      }
      await this.deps.credits.consume(user.userId, SORA2_COST, "sora2_invite_code", "telegram_bot");
      await this.deps.ownerNotifications.queue({
        userId,
        source: "telegram_bot",
        category: "sora2_request",
        message: `queue_position~${SORA2_QUEUE_START} cost=${SORA2_COST}`,
      });
      await this.sendSora2PurchaseSuccess(chatId, lang, messageId);
      await this.answerCallback(callback.id);
      return { handled: "sora2_buy" };
    }
    if (data.startsWith("credit_admin:")) {
      const parts = data.split(":");
      const action = parts[1];
      const ownerId = Number(this.deps.ownerTelegramChatId || 0);
      if (ownerId > 0 && ownerId !== userId) {
        await this.answerCallback(callback.id, "⛔️", true);
        return { handled: "credit_admin_denied" };
      }
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
        await this.sendHelp(chatId, lang);
        return { handled: "help" };
      case "/language":
        await this.sendLanguageMenu(chatId, lang, undefined, false, true);
        return { handled: "language_menu" };
      case "/admin":
        if (!this.isOwner(userId)) {
          await this.sendMessage(chatId, ADMIN_DENY_TEXT);
          return { handled: "admin_denied" };
        }
        await this.sendAdminMenu(chatId);
        return { handled: "admin_menu" };
      case "/menu":
        await this.sendMainMenu(chatId, undefined, lang);
        await this.maybeSendLowCreditWarning(chatId, userId, lang, true);
        await this.maybeAdvanceOnboardingMilestones(chatId, userId, lang);
        return { handled: "menu" };
      case "/profile": {
        const credits = await this.deps.credits.getCredits(userId);
        await this.sendMessage(
          chatId,
          `🙋🏼‍♂️ <b>${t("profile_title", lang)}</b>\n\n${t("profile_body", lang).replace("{uid}", String(userId)).replace("{credits}", String(credits.credits))}`,
          "HTML"
        );
        return { handled: "profile" };
      }
      case "/credits":
        await this.sendCreditMenu(chatId, lang);
        return { handled: "credits" };
      case "/apitoken": {
        const token = await this.deps.tokens.getOrCreate(userId);
        await this.sendApiTokenMenu(chatId, token, lang);
        return { handled: "api_token" };
      }
      case "/rotatetoken": {
        const token = await this.deps.tokens.rotate(userId);
        await this.sendApiTokenMenu(chatId, token, lang);
        return { handled: "api_rotate" };
      }
      case "/ask":
      case "/gpt":
        await this.deps.userState.setBotState(userId, { mode: "gpt:chat", updatedAt: nowTs() });
        await this.sendMessage(chatId, t("gpt_open", lang), "HTML", undefined, {
          keyboard: [[{ text: t("gpt_end_button", lang) }]],
          resize_keyboard: true,
        });
        return { handled: "gpt_open" };
      case "/endgpt":
      case "/stopgpt":
        await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
        await this.sendMessage(chatId, t("gpt_end", lang), "HTML", undefined, { remove_keyboard: true });
        await this.sendMainMenu(chatId, undefined, lang);
        return { handled: "gpt_end" };
      case "/img":
        await this.deps.userState.setBotState(userId, { mode: "image:wait_prompt", updatedAt: nowTs() });
        await this.sendMessage(chatId, t("image_intro", lang), "HTML", {
          inline_keyboard: [[{ text: t("back", lang), callback_data: "image:back" }]],
        });
        return { handled: "image_open" };
      case "/video":
        await this.deps.userState.setBotState(userId, { mode: "video:wait_image", updatedAt: nowTs() });
        await this.sendMessage(chatId, t("video_gen4_intro", lang), "HTML", {
          inline_keyboard: [[{ text: t("back", lang), callback_data: "video_gen4:back" }]],
        });
        return { handled: "video_open" };
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
      if (text === t("gpt_end_button", lang)) {
        await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
        await this.sendMessage(chatId, t("gpt_end", lang), "HTML", undefined, {
          remove_keyboard: true,
        });
        await this.sendMainMenu(chatId, undefined, lang);
        return true;
      }

      await this.deps.history.append(userId, "user", text);
      await this.deps.history.append(userId, "assistant", `Received your prompt: ${text.slice(0, 400)}`);
      await this.deps.credits.consume(userId, 1, "gpt_message", "telegram_bot");
      await this.sendMessage(chatId, `${t("gpt_wait", lang)}\n\n${text.slice(0, 400)}`, "HTML", undefined, {
        keyboard: [[{ text: t("gpt_end_button", lang) }]],
        resize_keyboard: true,
      });
      return true;
    }

    if (state.mode === "tts:wait_text") {
      if (!text) return false;
      await this.deps.userState.setBotState(userId, { ...state, mode: "tts:processing", updatedAt: nowTs() });
      if (this.hasBannedWord(text)) {
        const currentVoice = await this.resolveTtsVoiceSelection(userId, lang, state.ttsVoice || DEFAULT_VOICE_NAME_BY_LANG[lang] || DEFAULT_VOICE_NAME_BY_LANG.fa);
        await this.deps.userState.setBotState(userId, { ...state, mode: "tts:wait_text", updatedAt: nowTs(), ttsVoice: currentVoice });
        await this.sendMessage(chatId, t("tts_banned_words", lang), "HTML", await this.ttsKeyboard(lang, userId, currentVoice, state.ttsOutput || "mp3", state.ttsPage || 0));
        return true;
      }
      try {
        const voice = await this.resolveTtsVoiceSelection(userId, lang, state.ttsVoice || DEFAULT_VOICE_NAME_BY_LANG[lang] || DEFAULT_VOICE_NAME_BY_LANG.fa);
        if (!(await this.ttsVoiceExists(userId, lang, voice))) {
          await this.deps.userState.setBotState(userId, { ...state, mode: "tts:wait_text", updatedAt: nowTs(), ttsVoice: voice });
          await this.sendMessage(chatId, t("tts_voice_disabled", lang), "HTML");
          return true;
        }
        const isCustom = await this.isCustomVoice(userId, voice);
        const cost = Math.max(1, text.length * (isCustom ? 2 : 1));
        const credits = await this.deps.credits.getCredits(userId);
        if (credits.credits < cost) {
          await this.deps.userState.setBotState(userId, { ...state, mode: "tts:wait_text", updatedAt: nowTs(), ttsVoice: voice });
          await this.sendMessage(
            chatId,
            t("tts_no_credit", lang).replace("{credits}", String(credits.credits)).replace("{required}", String(cost)),
            "HTML",
            { inline_keyboard: [[{ text: t("btn_credit", lang), callback_data: "credit:menu" }]] }
          );
          return true;
        }
        await this.sendMessage(chatId, t("tts_processing", lang), "HTML");
        await this.deps.credits.consume(userId, cost, "tts_message", "telegram_bot");
        await this.deps.ownerNotifications.queue({
          userId,
          source: "telegram_bot",
          category: "tts_request",
          message: `voice=${voice} output=${state.ttsOutput || "mp3"} text=${text.slice(0, 1000)}`,
        });
        const output = (state.ttsOutput || "mp3").toUpperCase();
        await this.deps.userState.setBotState(userId, { ...state, mode: "tts:wait_text", updatedAt: nowTs(), ttsVoice: voice });
        await this.sendMessage(chatId, t("tts_request_saved", lang).replace("{voice}", voice).replace("{output}", output), "HTML", await this.ttsKeyboard(lang, userId, voice, state.ttsOutput || "mp3", state.ttsPage || 0));
      } catch {
        await this.deps.userState.setBotState(userId, { ...state, mode: "idle", updatedAt: nowTs() });
        await this.sendMessage(chatId, t("tts_error", lang), "HTML");
      }
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
      await this.sendMessage(chatId, t("image_processing", lang), "HTML", {
        inline_keyboard: [[{ text: t("back", lang), callback_data: "image:back" }]],
      });
      return true;
    }

    if (state.mode === "video:wait_image") {
      if (!text) return false;
      await this.sendMessage(chatId, t("video_gen4_need_image", lang), "HTML", {
        inline_keyboard: [[{ text: t("back", lang), callback_data: "video_gen4:back" }]],
      });
      return true;
    }

    if (state.mode === "clone:wait_name") {
      if (!text) return false;
      if (!state.cloneFileId) {
        await this.deps.userState.setBotState(userId, { mode: "clone:wait_audio", updatedAt: nowTs() });
        await this.sendMessage(chatId, t("clone_audio_missing", lang), "HTML");
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
      await this.sendMessage(chatId, t("clone_success", lang), "HTML");
      await this.sendMainMenu(chatId, undefined, lang);
      return true;
    }

    if (this.isOwner(userId) && text) {
      if (state.mode === "admin:lookup_user") {
        const uid = await this.resolveUserId(text);
        if (!uid) {
          await this.sendMessage(chatId, "❌ آی‌دی/یوزرنیم معتبر نیست.");
          return true;
        }
        await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
        const u = await this.deps.db
          .prepare(`SELECT user_id, username, lang, banned, credits FROM users WHERE user_id = ?1`)
          .bind(uid)
          .first<{ user_id: number; username: string | null; lang: string; banned: number; credits: number }>();
        if (!u) {
          await this.sendMessage(chatId, "❌ کاربر یافت نشد.");
          return true;
        }
        const txt = `👤 <b>${u.user_id}</b>\n@${u.username || "-"} | 💳 ${Math.round(Number(u.credits || 0))} | ${u.banned ? "🚫 بن" : "✅ مجاز"}\n🌐 زبان: <b>${u.lang || "fa"}</b>`;
        const keyboard: InlineKeyboard = {
          inline_keyboard: [
            [{ text: "➕ افزودن", callback_data: `admin:uadd:${u.user_id}` }, { text: "➖ کسر", callback_data: `admin:usub:${u.user_id}` }],
            [{ text: "✉️ پیام تکی", callback_data: `admin:dm:${u.user_id}` }, { text: u.banned ? "✅ آن‌بن" : "🚫 بن", callback_data: `admin:${u.banned ? "unban" : "ban"}:${u.user_id}` }],
            [{ text: "⬅️ بازگشت", callback_data: "admin:users" }],
          ],
        };
        await this.sendMessage(chatId, txt, "HTML", keyboard);
        return true;
      }
      if (state.mode === "admin:add_user" || state.mode === "admin:sub_user" || state.mode === "admin:dm_user") {
        const uid = await this.resolveUserId(text);
        if (!uid) {
          await this.sendMessage(chatId, "❌ آی‌دی/یوزرنیم معتبر نیست.");
          return true;
        }
        const mode = state.mode === "admin:add_user" ? "admin:add_amount" : state.mode === "admin:sub_user" ? "admin:sub_amount" : "admin:dm_content";
        await this.deps.userState.setBotState(userId, { mode, updatedAt: nowTs(), adminTargetUserId: uid });
        await this.sendMessage(chatId, state.mode === "admin:dm_user" ? "✍️ متن پیام تکی را بفرستید." : state.mode === "admin:add_user" ? "➕ مقدار کردیتی که باید اضافه شود را بفرستید (فقط عدد)." : "➖ مقدار کردیتی که باید کم شود را بفرستید (فقط عدد).");
        return true;
      }
      if (state.mode === "admin:add_amount" || state.mode === "admin:sub_amount") {
        const uid = Number(state.adminTargetUserId || 0);
        const amount = Number(text.trim());
        if (!uid || !Number.isFinite(amount)) {
          await this.sendMessage(chatId, "❌ فقط عدد.");
          return true;
        }
        const delta = state.mode === "admin:add_amount" ? Math.abs(amount) : -Math.abs(amount);
        await this.deps.db.prepare(`UPDATE users SET credits = credits + ?1 WHERE user_id = ?2`).bind(delta, uid).run();
        const row = await this.deps.db.prepare(`SELECT credits FROM users WHERE user_id = ?1`).bind(uid).first<{ credits: number }>();
        await this.sendMessage(chatId, `${ADMIN_DONE_TEXT}\n👤 <code>${uid}</code>\n${delta > 0 ? "➕" : "➖"} ${delta > 0 ? "+" : ""}${Math.abs(delta)}💳\n💼 موجودی: <b>${Math.round(Number(row?.credits || 0))}</b>`, "HTML");
        await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
        return true;
      }
      if (state.mode === "admin:reset_user") {
        const uid = await this.resolveUserId(text);
        if (!uid) {
          await this.sendMessage(chatId, "❌ آی‌دی/یوزرنیم معتبر نیست.");
          return true;
        }
        await this.deps.db.batch([
          this.deps.db.prepare(`DELETE FROM gpt_messages WHERE user_id = ?1`).bind(uid),
          this.deps.db.prepare(`DELETE FROM generated_assets WHERE user_id = ?1`).bind(uid),
          this.deps.db.prepare(`DELETE FROM credit_ledger WHERE user_id = ?1`).bind(uid),
          this.deps.db.prepare(`DELETE FROM users WHERE user_id = ?1`).bind(uid),
        ]);
        await this.sendMessage(chatId, `${ADMIN_DONE_TEXT}\n👤 <code>${uid}</code>\n♻️ اطلاعات کاربر حذف شد و باید دوباره استارت کند.`, "HTML");
        await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
        return true;
      }
      if (state.mode === "admin:dm_content") {
        const uid = Number(state.adminTargetUserId || 0);
        if (!uid) return true;
        await this.sendMessage(uid, text);
        await this.sendMessage(chatId, ADMIN_DONE_TEXT);
        await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
        return true;
      }
      if (state.mode === "admin:cast_content") {
        const langCode = state.adminCastLang || "all";
        const query = langCode === "all" ? `SELECT user_id FROM users` : `SELECT user_id FROM users WHERE lang = ?1`;
        const rs = langCode === "all" ? await this.deps.db.prepare(query).all<{ user_id: number }>() : await this.deps.db.prepare(query).bind(langCode).all<{ user_id: number }>();
        let sent = 0;
        for (const row of rs.results || []) {
          try {
            await this.sendMessage(Number(row.user_id), text);
            sent++;
          } catch {}
        }
        await this.sendMessage(chatId, `${ADMIN_DONE_TEXT}\n📣 ارسال شد به ${sent} کاربر.`);
        await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
        return true;
      }
      if (state.mode === "admin:set_setting") {
        await this.setSetting(state.adminSettingKey || "GENERIC", text.trim());
        await this.sendMessage(chatId, ADMIN_DONE_TEXT);
        await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
        return true;
      }
      if (state.mode === "admin:formula") {
        const expr = text.trim();
        const { results } = await this.deps.db.prepare(`SELECT user_id, credits FROM users`).all<{ user_id: number; credits: number }>();
        let affected = 0;
        for (const row of results || []) {
          const old = Number(row.credits || 0);
          let next = old;
          try {
            // Legacy parity keeps formula evaluation behavior.
            next = Number(Function("old", `return (${expr});`)(old));
          } catch {
            await this.sendMessage(chatId, "❌ خطا در فرمول.");
            return true;
          }
          if (Number.isFinite(next)) {
            await this.deps.db.prepare(`UPDATE users SET credits = ?1 WHERE user_id = ?2`).bind(Math.round(next), row.user_id).run();
            affected++;
          }
        }
        await this.sendMessage(chatId, `✅ کردیت ${affected} کاربر به‌روزرسانی شد.`);
        await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
        return true;
      }
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
        const selected = await this.resolveTtsVoiceSelection(userId, lang, DEFAULT_VOICE_NAME_BY_LANG[lang] || DEFAULT_VOICE_NAME_BY_LANG.fa);
        await this.deps.userState.setBotState(userId, { mode: "tts:wait_text", updatedAt: nowTs(), ttsVoice: selected, ttsOutput: "mp3", ttsPage: 0 });
        await this.sendMessage(chatId, this.ttsAskText(lang, selected), "HTML", await this.ttsKeyboard(lang, userId, selected, "mp3", 0));
        return true;
      case t("btn_gpt", lang):
        await this.handleCommand(userId, lang, chatId, "/ask", { mode: "idle", updatedAt: nowTs() });
        return true;
      case t("btn_lang", lang):
        await this.sendLanguageMenu(chatId, lang, undefined, false, true);
        return true;
      case t("btn_api_token", lang): {
        const token = await this.deps.tokens.getOrCreate(userId);
        await this.sendApiTokenMenu(chatId, token, lang);
        return true;
      }
      default:
        return false;
    }
  }

  private isOwner(userId: number): boolean {
    const ownerId = Number(this.deps.ownerTelegramChatId || 0);
    return ownerId > 0 && ownerId === userId;
  }

  private async getOrCreateAdminSettingsTable() {
    await this.deps.db
      .prepare(`CREATE TABLE IF NOT EXISTS bot_settings (key TEXT PRIMARY KEY, value TEXT, updated_at INTEGER NOT NULL)`)
      .run();
  }

  private async getSetting(key: string, fallback = ""): Promise<string> {
    await this.getOrCreateAdminSettingsTable();
    const row = await this.deps.db.prepare(`SELECT value FROM bot_settings WHERE key = ?1`).bind(key).first<{ value: string }>();
    return row?.value ?? fallback;
  }

  private async setSetting(key: string, value: string): Promise<void> {
    await this.getOrCreateAdminSettingsTable();
    await this.deps.db
      .prepare(`INSERT INTO bot_settings(key, value, updated_at) VALUES(?1, ?2, ?3) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at`)
      .bind(key, value, nowTs())
      .run();
  }

  private async resolveUserId(raw: string): Promise<number | null> {
    const text = (raw || "").trim();
    if (!text) return null;
    if (/^\d+$/.test(text)) return Number(text);
    const username = text.replace(/^@/, "");
    const row = await this.deps.db.prepare(`SELECT user_id FROM users WHERE username = ?1 LIMIT 1`).bind(username).first<{ user_id: number }>();
    return row ? Number(row.user_id) : null;
  }

  private adminMenuKeyboard(): InlineKeyboard {
    return {
      inline_keyboard: [
        [
          { text: "📊 آمار", callback_data: "admin:stats" },
          { text: "👥 کاربران", callback_data: "admin:users" },
        ],
        [{ text: "🌐 کاربران بر اساس زبان", callback_data: "admin:lang_users" }],
        [
          { text: "🖼️ کاربران تصویر", callback_data: "admin:image_users" },
          { text: "🤖 کاربران GPT", callback_data: "admin:gpt_users" },
        ],
        [{ text: "🧬 کاربران Voice Clone", callback_data: "admin:clone" }],
        [{ text: "🎁 پاداش روزانه", callback_data: "admin:daily_reward_users" }],
        [
          { text: "➕ افزودن کردیت", callback_data: "admin:add" },
          { text: "➖ کسر کردیت", callback_data: "admin:sub" },
        ],
        [{ text: "🧮 فرمول کردیت همگانی", callback_data: "admin:bulk_credit" }],
        [{ text: "♻️ ریست کاربر", callback_data: "admin:reset" }],
        [
          { text: "✉️ پیام تکی", callback_data: "admin:dm" },
          { text: "📣 پیام همگانی", callback_data: "admin:cast" },
        ],
        [
          { text: "⚙️ تنظیمات", callback_data: "admin:settings" },
          { text: "📤 خروجی‌ها", callback_data: "admin:exports" },
        ],
        [{ text: "⬅️ بازگشت", callback_data: "admin:back" }],
      ],
    };
  }

  private adminSettingsKeyboard(): InlineKeyboard {
    const forceSubRaw = (this.deps.forceSubMode || "none").toLowerCase();
    const forceSubLabel = forceSubRaw === "all" ? "همه" : forceSubRaw === "new" ? "فقط جدیدها" : "خاموش";
    const soundEnabled = (this.deps.welcomeAudioFileId || "").trim() ? "✅ فعال" : "❌ غیرفعال";
    return {
      inline_keyboard: [
        [
          { text: "🎁 بونوس رفرال", callback_data: "admin:set:bonus" },
          { text: "🎉 کردیت شروع", callback_data: "admin:set:free" },
        ],
        [
          { text: "📢 کانال تلگرام", callback_data: "admin:set:tg" },
          { text: "📷 لینک اینستاگرام", callback_data: "admin:set:ig" },
        ],
        [{ text: `🔐 عضویت اجباری: ${forceSubLabel}`, callback_data: "admin:toggle:fs" }],
        [{ text: "🧩 دسترسی بخش‌ها", callback_data: "admin:features" }],
        [{ text: "🔐 عضویت اجباری بر اساس زبان", callback_data: "admin:fs_lang:list" }],
        [{ text: "🎛 مدیریت صداهای ربات", callback_data: "admin:global_voices" }],
        [{ text: "🎧 دموهای صدا", callback_data: "admin:demo" }],
        [{ text: "🎙 پیام صوتی خوش‌آمد", callback_data: "admin:welcome_audio" }],
        [{ text: `🔊 صدای ربات: ${soundEnabled}`, callback_data: "admin:toggle:sound" }],
        [{ text: "⬅️ بازگشت", callback_data: "admin:menu" }],
      ],
    };
  }

  private adminExportsKeyboard(): InlineKeyboard {
    return {
      inline_keyboard: [
        [
          { text: "👥 کاربران", callback_data: "admin:exp:users" },
          { text: "🪙 خریدها", callback_data: "admin:exp:buy" },
        ],
        [{ text: "💬 پیام‌ها", callback_data: "admin:exp:msg" }],
        [{ text: "⬅️ بازگشت", callback_data: "admin:menu" }],
      ],
    };
  }

  private adminCastLangKeyboard(): InlineKeyboard {
    const rows: InlineKeyboard["inline_keyboard"] = [[{ text: "🌍 همه زبان‌ها", callback_data: "admin:cast_lang:all" }]];
    for (let i = 0; i < LANGS.length; i += 2) {
      const left = LANGS[i]!;
      const right = LANGS[i + 1];
      const row = [{ text: left.label, callback_data: `admin:cast_lang:${left.code}` }];
      if (right) row.push({ text: right.label, callback_data: `admin:cast_lang:${right.code}` });
      rows.push(row);
    }
    rows.push([{ text: "⬅️ بازگشت", callback_data: "admin:menu" }]);
    return { inline_keyboard: rows };
  }

  private adminLangListKeyboard(prefix: string, backTo = "admin:settings"): InlineKeyboard {
    const rows: InlineKeyboard["inline_keyboard"] = [];
    for (let i = 0; i < LANGS.length; i += 2) {
      const left = LANGS[i]!;
      const right = LANGS[i + 1];
      const row = [{ text: left.label, callback_data: `${prefix}${left.code}` }];
      if (right) row.push({ text: right.label, callback_data: `${prefix}${right.code}` });
      rows.push(row);
    }
    rows.push([{ text: "⬅️ بازگشت", callback_data: backTo }]);
    return { inline_keyboard: rows };
  }

  private async sendAdminMenu(chatId: number, messageId?: number) {
    await this.sendOrEditMessage(chatId, `${ADMIN_TITLE}

${ADMIN_MENU_TEXT}`, this.adminMenuKeyboard(), messageId);
  }

  private async adminFeatureAccessKeyboard(): Promise<InlineKeyboard> {
    const rows: InlineKeyboard["inline_keyboard"] = [];
    for (const item of ADMIN_FEATURE_TOGGLES) {
      const raw = (await this.getSetting(item.key, "1")).trim().toLowerCase();
      const enabled = ["1", "true", "yes", "on", "enabled"].includes(raw);
      rows.push([{ text: `${item.label}: ${enabled ? "✅ فعال" : "❌ غیرفعال"}`, callback_data: `admin:feature:toggle:${item.key}` }]);
    }
    rows.push([{ text: "⬅️ بازگشت", callback_data: "admin:settings" }]);
    return { inline_keyboard: rows };
  }

  private csvEscape(value: unknown): string {
    const text = String(value ?? "");
    if (/[",\n]/.test(text)) return `"${text.replaceAll(`"`, `""`)}"`;
    return text;
  }

  private csvFromRows(headers: string[], rows: Array<Array<unknown>>): string {
    const lines: string[] = [];
    lines.push(headers.map((h) => this.csvEscape(h)).join(","));
    for (const row of rows) {
      lines.push(row.map((v) => this.csvEscape(v)).join(","));
    }
    return `${lines.join("\n")}\n`;
  }

  private async sendDocumentFromText(chatId: number, filename: string, content: string, caption: string): Promise<void> {
    const form = new FormData();
    form.append("chat_id", String(chatId));
    form.append("caption", caption);
    form.append("document", new Blob([content], { type: "text/csv;charset=utf-8" }), filename);
    await fetch(`https://api.telegram.org/bot${this.deps.botToken}/sendDocument`, {
      method: "POST",
      body: form,
    });
  }

  private async handleAdminCallback(callbackId: string, chatId: number, messageId: number | undefined, userId: number, data: string): Promise<{ handled: string }> {
    if (!this.isOwner(userId)) {
      await this.answerCallback(callbackId, "⛔️", true);
      return { handled: "admin_denied" };
    }

    if (data === "admin:back") {
      await this.sendMainMenu(chatId, messageId, "fa");
      await this.answerCallback(callbackId);
      return { handled: "admin_back" };
    }

    if (data === "admin:menu") {
      await this.sendAdminMenu(chatId, messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_menu" };
    }

    if (data === "admin:settings") {
      await this.sendOrEditMessage(chatId, "⚙️ تنظیمات ربات:", this.adminSettingsKeyboard(), messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_settings" };
    }

    if (data === "admin:exports") {
      await this.sendOrEditMessage(chatId, "📤 خروجی‌ها:", this.adminExportsKeyboard(), messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_exports" };
    }
    if (data.startsWith("admin:ban:") || data.startsWith("admin:unban:")) {
      const uid = Number(data.split(":")[2] || 0);
      await this.deps.db.prepare(`UPDATE users SET banned = ?1 WHERE user_id = ?2`).bind(data.startsWith("admin:ban:") ? 1 : 0, uid).run();
      return this.handleAdminCallback(callbackId, chatId, messageId, userId, `admin:user:${uid}`);
    }

    const legacyPrompts: Record<string, string> = {
      "admin:add": "➕ آیدی عددی یا یوزرنیم کاربر برای «افزایش کردیت» را بفرستید.",
      "admin:sub": "➖ آیدی عددی یا یوزرنیم کاربر برای «کسر کردیت» را بفرستید.",
      "admin:bulk_credit": "🧮 فرمول محاسبه کردیت جدید را بفرستید.\nمی‌توانید از متغیر <code>old</code> (کردیت فعلی) استفاده کنید، مثلا: <code>old * 0.045</code>.",
      "admin:reset": "♻️ آیدی عددی یا یوزرنیم کاربری که باید ریست شود را بفرستید.",
      "admin:dm": "✉️ آیدی عددی یا یوزرنیم کاربری که باید پیام تکی بگیرد را بفرستید.",
      "admin:cast": "🌐 زبان پیام همگانی را انتخاب کنید.",
      "admin:users": "👥 لیست کاربران:",
      "admin:stats": "📊 آمار:",
      "admin:clone": "🧬 کاربران Voice Clone:",
      "admin:image_users": "🖼️ کاربران تصویر:",
      "admin:gpt_users": "🤖 کاربران GPT:",
      "admin:daily_reward_users": "🎁 کاربران پاداش روزانه:",
      "admin:lang_users": "🌐 کاربران بر اساس زبان:",
      "admin:demo": "🎧 زبان دمو را انتخاب کنید.",
      "admin:welcome_audio": "🎙 زبان پیام صوتی خوش‌آمد را انتخاب کنید.",
      "admin:features": "🧩 مدیریت دسترسی بخش‌ها:",
      "admin:global_voices": "🎛 مدیریت صداهای ربات:",
      "admin:fs_lang:list": "🔐 تنظیمات عضویت اجباری بر اساس زبان:",
      "admin:set:bonus": "🎁 مقدار بونوس رفرال را بفرستید (عدد).",
      "admin:set:free": "🎉 مقدار «کردیت شروع برای ورود اول» را بفرستید (عدد).",
      "admin:set:tg": "📢 لینک/یوزرنیم کانال تلگرام (برای عضویت اجباری) را بفرستید.",
      "admin:set:ig": "📷 لینک پیج اینستاگرام (برای عضویت اجباری) را بفرستید.",
    };

    if (data === "admin:stats") {
      const total = await this.deps.db.prepare(`SELECT COUNT(*) as c FROM users`).first<{ c: number }>();
      const active24 = await this.deps.db.prepare(`SELECT COUNT(*) as c FROM users WHERE last_seen_at >= ?1`).bind(nowTs() - 86400).first<{ c: number }>();
      const imageUsers = await this.deps.db.prepare(`SELECT COUNT(DISTINCT user_id) as c FROM generated_assets WHERE asset_type='image'`).first<{ c: number }>();
      const gptUsers = await this.deps.db.prepare(`SELECT COUNT(DISTINCT user_id) as c FROM gpt_messages`).first<{ c: number }>();
      const txt = `📊 <b>آمار</b>\n\n👥 کل کاربران: <b>${Number(total?.c || 0)}</b>\n⚡️ فعال ۲۴ساعت: <b>${Number(active24?.c || 0)}</b>\n🖼️ کاربران تولید تصویر: <b>${Number(imageUsers?.c || 0)}</b>\n🤖 کاربران GPT: <b>${Number(gptUsers?.c || 0)}</b>`;
      await this.sendOrEditMessage(chatId, txt, this.adminMenuKeyboard(), messageId, "HTML");
      await this.answerCallback(callbackId);
      return { handled: "admin_stats" };
    }

    if (data === "admin:users") {
      const { results } = await this.deps.db
        .prepare(`SELECT user_id, username, credits, banned FROM users ORDER BY user_id DESC LIMIT 10`)
        .all<{ user_id: number; username: string | null; credits: number; banned: number }>();
      const rows: InlineKeyboard["inline_keyboard"] = (results || []).map((u) => [
        { text: `${u.banned ? "🚫" : "✅"} ${u.user_id}${u.username ? ` · @${u.username}` : ""} · 💳 ${Math.round(Number(u.credits || 0))}`, callback_data: `admin:user:${u.user_id}` },
      ]);
      rows.push([{ text: "🔎 جستجوی کاربر", callback_data: "admin:user:lookup" }], [{ text: "⬅️ بازگشت", callback_data: "admin:menu" }]);
      await this.sendOrEditMessage(chatId, "👥 لیست کاربران:", { inline_keyboard: rows }, messageId, "HTML");
      await this.answerCallback(callbackId);
      return { handled: "admin_users" };
    }

    const prompt = legacyPrompts[data];
    if (prompt) {
      const keyboard = data === "admin:cast" ? this.adminCastLangKeyboard() : this.adminMenuKeyboard();
      await this.sendOrEditMessage(chatId, prompt, keyboard, messageId, "HTML");
      if (data === "admin:add") await this.deps.userState.setBotState(userId, { mode: "admin:add_user", updatedAt: nowTs() });
      if (data === "admin:sub") await this.deps.userState.setBotState(userId, { mode: "admin:sub_user", updatedAt: nowTs() });
      if (data === "admin:reset") await this.deps.userState.setBotState(userId, { mode: "admin:reset_user", updatedAt: nowTs() });
      if (data === "admin:dm") await this.deps.userState.setBotState(userId, { mode: "admin:dm_user", updatedAt: nowTs() });
      if (data === "admin:bulk_credit") await this.deps.userState.setBotState(userId, { mode: "admin:formula", updatedAt: nowTs() });
      if (data === "admin:set:bonus") await this.deps.userState.setBotState(userId, { mode: "admin:set_setting", updatedAt: nowTs(), adminSettingKey: "BONUS_REFERRAL" });
      if (data === "admin:set:free") await this.deps.userState.setBotState(userId, { mode: "admin:set_setting", updatedAt: nowTs(), adminSettingKey: "FREE_CREDIT" });
      if (data === "admin:set:tg") await this.deps.userState.setBotState(userId, { mode: "admin:set_setting", updatedAt: nowTs(), adminSettingKey: "TG_CHANNEL" });
      if (data === "admin:set:ig") await this.deps.userState.setBotState(userId, { mode: "admin:set_setting", updatedAt: nowTs(), adminSettingKey: "IG_URL" });
      await this.answerCallback(callbackId);
      return { handled: "admin_prompt" };
    }

    if (data === "admin:user:lookup" || data.startsWith("admin:user:")) {
      if (data === "admin:user:lookup") {
        await this.deps.userState.setBotState(userId, { mode: "admin:lookup_user", updatedAt: nowTs() });
      }
      if (data.startsWith("admin:user:") && data !== "admin:user:lookup") {
        const uid = Number(data.split(":")[2] || 0);
        const u = await this.deps.db
          .prepare(`SELECT user_id, username, lang, banned, credits FROM users WHERE user_id = ?1`)
          .bind(uid)
          .first<{ user_id: number; username: string | null; lang: string; banned: number; credits: number }>();
        if (u) {
          const txt = `👤 <b>${u.user_id}</b>\n@${u.username || "-"} | 💳 ${Math.round(Number(u.credits || 0))} | ${u.banned ? "🚫 بن" : "✅ مجاز"}\n🌐 زبان: <b>${u.lang || "fa"}</b>`;
          const keyboard: InlineKeyboard = {
            inline_keyboard: [
              [{ text: "➕ افزودن", callback_data: `admin:uadd:${u.user_id}` }, { text: "➖ کسر", callback_data: `admin:usub:${u.user_id}` }],
              [{ text: "✉️ پیام تکی", callback_data: `admin:dm:${u.user_id}` }, { text: u.banned ? "✅ آن‌بن" : "🚫 بن", callback_data: `admin:${u.banned ? "unban" : "ban"}:${u.user_id}` }],
              [
                { text: "📥 متن‌های TTS کاربر", callback_data: `admin:exp_user_tts:${u.user_id}` },
                { text: "💬 پیام‌های کاربر", callback_data: `admin:exp_user_msgs:${u.user_id}` },
              ],
              [
                { text: "🤖 GPT کاربر", callback_data: `admin:exp_user_gpt:${u.user_id}` },
                { text: "🖼️ تصاویر کاربر", callback_data: `admin:exp_user_images:${u.user_id}` },
              ],
              [{ text: "⬅️ بازگشت", callback_data: "admin:users" }],
            ],
          };
          await this.sendOrEditMessage(chatId, txt, keyboard, messageId, "HTML");
          await this.answerCallback(callbackId);
          return { handled: "admin_user_profile" };
        }
      }
      await this.sendOrEditMessage(chatId, "🔎 آیدی عددی یا یوزرنیم کاربر را بفرستید (مثل @user یا 123456789).", this.adminMenuKeyboard(), messageId, "HTML");
      await this.answerCallback(callbackId);
      return { handled: "admin_user_lookup" };
    }

    if (data.startsWith("admin:users:") || data.startsWith("admin:image_users:") || data.startsWith("admin:gpt_users:") || data.startsWith("admin:daily_reward_users:")) {
      await this.sendOrEditMessage(chatId, "📄 صفحه بعد/قبل کاربران انتخاب شد.", this.adminMenuKeyboard(), messageId, "HTML");
      await this.answerCallback(callbackId);
      return { handled: "admin_paging" };
    }

    if (data.startsWith("admin:cast_lang:")) {
      const selected = data.split(":")[2] || "all";
      const label = selected === "all" ? "همه زبان‌ها" : selected;
      await this.sendOrEditMessage(chatId, `📣 زبان پیام همگانی روی <b>${label}</b> انتخاب شد.\nحالا متن پیام همگانی را ارسال کنید.`, this.adminMenuKeyboard(), messageId, "HTML");
      await this.deps.userState.setBotState(userId, { mode: "admin:cast_content", updatedAt: nowTs(), adminCastLang: selected });
      await this.answerCallback(callbackId);
      return { handled: "admin_cast_lang" };
    }

    if (data === "admin:demo") {
      await this.sendOrEditMessage(chatId, "🎧 زبان دمو را انتخاب کنید.", this.adminLangListKeyboard("admin:demo:lang:", "admin:settings"), messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_demo_langs" };
    }
    if (data.startsWith("admin:demo:lang:")) {
      const langCode = data.split(":")[3] || "fa";
      const voices = Object.keys(VOICES_BY_LANG[langCode] || VOICES_BY_LANG.fa);
      const rows: InlineKeyboard["inline_keyboard"] = [];
      for (let i = 0; i < voices.length; i += 3) {
        rows.push(voices.slice(i, i + 3).map((name) => ({ text: name, callback_data: `admin:demo:voice:${langCode}:${name}` })));
      }
      rows.push([{ text: "⬅️ بازگشت", callback_data: "admin:demo" }]);
      await this.sendOrEditMessage(chatId, "🎧 یک صدا را برای ثبت دمو انتخاب کنید.", { inline_keyboard: rows }, messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_demo_voice_list" };
    }
    if (data.startsWith("admin:demo:voice:")) {
      const [, , , langCode, ...voiceParts] = data.split(":");
      const voiceName = voiceParts.join(":");
      await this.sendOrEditMessage(
        chatId,
        `🎧 دمو برای صدا <b>${voiceName}</b> (${langCode})\nفایل audio/voice/document را ارسال کنید.`,
        {
          inline_keyboard: [
            [{ text: "🗑 حذف دمو", callback_data: `admin:demo:delete:${langCode}:${voiceName}` }],
            [{ text: "⬅️ بازگشت", callback_data: `admin:demo:lang:${langCode}` }],
          ],
        },
        messageId,
        "HTML"
      );
      await this.answerCallback(callbackId);
      return { handled: "admin_demo_voice" };
    }
    if (data.startsWith("admin:demo:delete:")) {
      await this.sendOrEditMessage(chatId, "✅ دمو حذف شد.", this.adminSettingsKeyboard(), messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_demo_delete" };
    }

    if (data === "admin:welcome_audio") {
      await this.sendOrEditMessage(chatId, "🎙 زبان پیام صوتی خوش‌آمد را انتخاب کنید.", this.adminLangListKeyboard("admin:welcome_audio:lang:", "admin:settings"), messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_welcome_audio_langs" };
    }
    if (data.startsWith("admin:welcome_audio:lang:")) {
      const langCode = data.split(":")[3] || "fa";
      await this.sendOrEditMessage(
        chatId,
        `🎙 فایل صوتی خوش‌آمد را برای <b>${langCode}</b> ارسال کنید (audio/voice/document).`,
        {
          inline_keyboard: [
            [{ text: "🗑 حذف پیام خوش‌آمد", callback_data: `admin:welcome_audio:delete:${langCode}` }],
            [{ text: "⬅️ بازگشت", callback_data: "admin:welcome_audio" }],
          ],
        },
        messageId,
        "HTML"
      );
      await this.answerCallback(callbackId);
      return { handled: "admin_welcome_audio_lang" };
    }
    if (data.startsWith("admin:welcome_audio:delete:")) {
      await this.sendOrEditMessage(chatId, "✅ پیام خوش‌آمد حذف شد.", this.adminSettingsKeyboard(), messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_welcome_audio_delete" };
    }

    if (data === "admin:fs_lang:list") {
      await this.sendOrEditMessage(chatId, "🔐 تنظیمات عضویت اجباری بر اساس زبان:", this.adminLangListKeyboard("admin:fs_lang:open:", "admin:settings"), messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_fs_lang_list" };
    }
    if (data.startsWith("admin:fs_lang:open:")) {
      const langCode = data.split(":")[3] || "fa";
      const mode = (await this.getSetting(`FORCE_SUB_MODE_${langCode}`, "none")).toLowerCase();
      const modeLabel = mode === "all" ? "همه" : mode === "new" ? "فقط جدیدها" : "خاموش";
      const tgChannel = (await this.getSetting(`TG_CHANNEL_${langCode}`, "")).trim() || "—";
      await this.sendOrEditMessage(
        chatId,
        `🔐 تنظیمات عضویت اجباری برای <b>${langCode}</b>`,
        {
          inline_keyboard: [
            [{ text: `🔐 عضویت اجباری: ${modeLabel}`, callback_data: `admin:fs_lang:toggle:${langCode}` }],
            [{ text: `📢 کانال تلگرام: ${tgChannel}`, callback_data: `admin:fs_lang:set_tg:${langCode}` }],
            [{ text: "⬅️ بازگشت", callback_data: "admin:fs_lang:list" }],
          ],
        },
        messageId,
        "HTML"
      );
      await this.answerCallback(callbackId);
      return { handled: "admin_fs_lang_open" };
    }
    if (data.startsWith("admin:fs_lang:toggle:")) {
      const langCode = data.split(":")[3] || "fa";
      const key = `FORCE_SUB_MODE_${langCode}`;
      const cur = (await this.getSetting(key, "none")).toLowerCase();
      const order = ["none", "new", "all"];
      const idx = Math.max(0, order.indexOf(cur));
      const next = order[(idx + 1) % order.length]!;
      await this.setSetting(key, next);
      return this.handleAdminCallback(callbackId, chatId, messageId, userId, `admin:fs_lang:open:${langCode}`);
    }
    if (data.startsWith("admin:fs_lang:set_tg:")) {
      const langCode = data.split(":")[3] || "fa";
      await this.deps.userState.setBotState(userId, { mode: "admin:set_setting", updatedAt: nowTs(), adminSettingKey: `TG_CHANNEL_${langCode}` });
      await this.sendOrEditMessage(chatId, `📢 لینک/یوزرنیم کانال تلگرام برای زبان <b>${langCode}</b> را ارسال کنید.`, this.adminSettingsKeyboard(), messageId, "HTML");
      await this.answerCallback(callbackId);
      return { handled: "admin_fs_lang_set_tg_prompt" };
    }

    if (data === "admin:features") {
      await this.sendOrEditMessage(chatId, "🧩 مدیریت دسترسی بخش‌ها:", await this.adminFeatureAccessKeyboard(), messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_features" };
    }

    if (data.startsWith("admin:feature:toggle:") || data === "admin:toggle:fs" || data === "admin:toggle:sound") {
      if (data.startsWith("admin:feature:toggle:")) {
        const key = data.split(":")[3] || "";
        const cur = await this.getSetting(key, "1");
        await this.setSetting(key, cur === "1" ? "0" : "1");
        await this.sendOrEditMessage(chatId, "✅ وضعیت با موفقیت تغییر کرد.", await this.adminFeatureAccessKeyboard(), messageId);
        await this.answerCallback(callbackId);
        return { handled: "admin_feature_toggle" };
      } else if (data === "admin:toggle:fs") {
        const cur = await this.getSetting("FORCE_SUB_MODE", "none");
        const order = ["none", "new", "all"];
        const idx = Math.max(0, order.indexOf(cur));
        await this.setSetting("FORCE_SUB_MODE", order[(idx + 1) % order.length]!);
      } else {
        const cur = await this.getSetting("SOUND_ENABLED", "1");
        await this.setSetting("SOUND_ENABLED", cur === "1" ? "0" : "1");
      }
      await this.sendOrEditMessage(chatId, "✅ وضعیت با موفقیت تغییر کرد.", this.adminSettingsKeyboard(), messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_toggle" };
    }

    if (data === "admin:global_voices" || data === "admin:global_voices:lang:openai") {
      await this.sendOrEditMessage(chatId, "🎛 زبان مدیریت صداها را انتخاب کنید.", this.adminLangListKeyboard("admin:global_voices:lang:", "admin:settings"), messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_global_voices" };
    }
    if (data.startsWith("admin:global_voices:lang:")) {
      const langCode = data.split(":")[3] || "fa";
      const voices = Object.keys(VOICES_BY_LANG[langCode] || VOICES_BY_LANG.fa).slice(0, 18);
      const rows: InlineKeyboard["inline_keyboard"] = [];
      for (let i = 0; i < voices.length; i += 2) {
        rows.push(voices.slice(i, i + 2).map((voice) => ({ text: voice, callback_data: `admin:global_voices:toggle:${langCode}:${voice}` })));
      }
      rows.push([{ text: "⬅️ بازگشت", callback_data: "admin:global_voices" }]);
      await this.sendOrEditMessage(chatId, "🎛 صدای موردنظر را برای فعال/غیرفعال‌سازی انتخاب کنید.", { inline_keyboard: rows }, messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_global_voices_lang" };
    }
    if (data.startsWith("admin:global_voices:toggle:") || data.startsWith("admin:global_voices:page:")) {
      await this.sendOrEditMessage(chatId, "✅ وضعیت صدا به‌روزرسانی شد.", this.adminSettingsKeyboard(), messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_global_voices_toggle" };
    }

    if (data.startsWith("admin:exp:")) {
      if (data === "admin:exp:users") {
        const { results } = await this.deps.db
          .prepare(`SELECT user_id, username, first_name, lang, banned, credits, joined_at, last_seen_at FROM users ORDER BY user_id ASC`)
          .all<{ user_id: number; username: string | null; first_name: string | null; lang: string; banned: number; credits: number; joined_at: number; last_seen_at: number }>();
        const csv = this.csvFromRows(
          ["user_id", "username", "first_name", "lang", "banned", "credits", "joined_at", "last_seen_at"],
          (results || []).map((r) => [r.user_id, r.username || "", r.first_name || "", r.lang || "", r.banned, r.credits, r.joined_at, r.last_seen_at])
        );
        await this.sendDocumentFromText(chatId, "users.csv", csv, "📤 خروجی کاربران");
      } else if (data === "admin:exp:buy") {
        const { results } = await this.deps.db
          .prepare(`SELECT user_id, amount, reason, source, created_at FROM credit_ledger WHERE reason IN ('telegram_stars_purchase','manual_rial_payment') ORDER BY created_at DESC`)
          .all<{ user_id: number; amount: number; reason: string; source: string; created_at: number }>();
        const csv = this.csvFromRows(
          ["user_id", "amount", "reason", "source", "created_at"],
          (results || []).map((r) => [r.user_id, r.amount, r.reason, r.source, r.created_at])
        );
        await this.sendDocumentFromText(chatId, "purchases.csv", csv, "📤 خروجی خریدها");
      } else if (data === "admin:exp:msg") {
        const { results } = await this.deps.db
          .prepare(`SELECT user_id, role, content, created_at FROM gpt_messages ORDER BY created_at DESC LIMIT 50000`)
          .all<{ user_id: number; role: string; content: string; created_at: number }>();
        const csv = this.csvFromRows(
          ["user_id", "role", "content", "created_at"],
          (results || []).map((r) => [r.user_id, r.role, r.content, r.created_at])
        );
        await this.sendDocumentFromText(chatId, "messages.csv", csv, "📤 خروجی پیام‌ها");
      }
      await this.sendOrEditMessage(chatId, "📤 خروجی ارسال شد.", this.adminExportsKeyboard(), messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_export" };
    }

    if (data.startsWith("admin:clone:")) {
      await this.sendOrEditMessage(chatId, "🧬 عملیات Voice Clone مدیریت شد.", this.adminMenuKeyboard(), messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_clone_action" };
    }

    if (data === "admin:noop") {
      await this.answerCallback(callbackId);
      return { handled: "admin_noop" };
    }

    if (data.startsWith("admin:uadd:") || data.startsWith("admin:usub:") || data.startsWith("admin:dm:")) {
      const uid = Number(data.split(":")[2] || 0);
      if (data.startsWith("admin:uadd:")) await this.deps.userState.setBotState(userId, { mode: "admin:add_amount", updatedAt: nowTs(), adminTargetUserId: uid });
      if (data.startsWith("admin:usub:")) await this.deps.userState.setBotState(userId, { mode: "admin:sub_amount", updatedAt: nowTs(), adminTargetUserId: uid });
      if (data.startsWith("admin:dm:")) await this.deps.userState.setBotState(userId, { mode: "admin:dm_content", updatedAt: nowTs(), adminTargetUserId: uid });
      await this.sendOrEditMessage(chatId, data.startsWith("admin:dm:") ? "✍️ متن پیام تکی را بفرستید." : "➕/➖ مقدار را به‌صورت عدد ارسال کنید.", this.adminMenuKeyboard(), messageId, "HTML");
      await this.answerCallback(callbackId);
      return { handled: "admin_user_action_shortcut" };
    }

    if (data.startsWith("admin:exp_user_")) {
      const parts = data.split(":");
      const action = parts[1] || "";
      const uid = Number(parts[2] || 0);
      if (!uid) {
        await this.answerCallback(callbackId, "❌ آی‌دی نامعتبر", true);
        return { handled: "admin_export_user_invalid_uid" };
      }
      if (action === "exp_user_tts") {
        const { results } = await this.deps.db
          .prepare(`SELECT user_id, amount, reason, source, created_at FROM credit_ledger WHERE user_id = ?1 AND reason = 'tts_message' ORDER BY created_at DESC`)
          .bind(uid)
          .all<{ user_id: number; amount: number; reason: string; source: string; created_at: number }>();
        const csv = this.csvFromRows(
          ["user_id", "amount", "reason", "source", "created_at"],
          (results || []).map((r) => [r.user_id, r.amount, r.reason, r.source, r.created_at])
        );
        await this.sendDocumentFromText(chatId, `user_${uid}_tts.csv`, csv, `📥 خروجی TTS کاربر ${uid}`);
      } else if (action === "exp_user_msgs") {
        const { results } = await this.deps.db
          .prepare(`SELECT user_id, role, content, created_at FROM gpt_messages WHERE user_id = ?1 ORDER BY created_at DESC`)
          .bind(uid)
          .all<{ user_id: number; role: string; content: string; created_at: number }>();
        const csv = this.csvFromRows(
          ["user_id", "role", "content", "created_at"],
          (results || []).map((r) => [r.user_id, r.role, r.content, r.created_at])
        );
        await this.sendDocumentFromText(chatId, `user_${uid}_messages.csv`, csv, `📥 پیام‌های کاربر ${uid}`);
      } else if (action === "exp_user_gpt") {
        const { results } = await this.deps.db
          .prepare(`SELECT user_id, role, content, created_at FROM gpt_messages WHERE user_id = ?1 ORDER BY created_at DESC`)
          .bind(uid)
          .all<{ user_id: number; role: string; content: string; created_at: number }>();
        const csv = this.csvFromRows(
          ["user_id", "role", "content", "created_at"],
          (results || []).map((r) => [r.user_id, r.role, r.content, r.created_at])
        );
        await this.sendDocumentFromText(chatId, `user_${uid}_gpt.csv`, csv, `📥 GPT کاربر ${uid}`);
      } else if (action === "exp_user_images") {
        const { results } = await this.deps.db
          .prepare(`SELECT user_id, asset_type, source_prompt, storage_url, status, provider, created_at FROM generated_assets WHERE user_id = ?1 ORDER BY created_at DESC`)
          .bind(uid)
          .all<{ user_id: number; asset_type: string; source_prompt: string | null; storage_url: string | null; status: string; provider: string | null; created_at: number }>();
        const csv = this.csvFromRows(
          ["user_id", "asset_type", "source_prompt", "storage_url", "status", "provider", "created_at"],
          (results || []).map((r) => [r.user_id, r.asset_type, r.source_prompt || "", r.storage_url || "", r.status, r.provider || "", r.created_at])
        );
        await this.sendDocumentFromText(chatId, `user_${uid}_images.csv`, csv, `📥 تصاویر کاربر ${uid}`);
      }
      await this.sendOrEditMessage(chatId, "📤 خروجی جزئی کاربر ارسال شد.", this.adminExportsKeyboard(), messageId);
      await this.answerCallback(callbackId);
      return { handled: "admin_export_user" };
    }

    await this.deps.ownerNotifications.queue({
      userId,
      source: "telegram_bot",
      category: "admin_callback",
      message: `Unhandled legacy admin callback: ${data}`,
    });
    await this.answerCallback(callbackId, "Action received ✅");
    return { handled: "admin_callback" };
  }

  private mainMenuKeyboard(lang: string): InlineKeyboard {
    return {
      inline_keyboard: [
        [
          { text: t("btn_profile", lang), callback_data: "home:profile" },
          { text: t("btn_credit", lang), callback_data: "home:credit" },
        ],
        [{ text: t("btn_tts", lang), callback_data: "home:tts" }],
        [{ text: t("btn_gpt", lang), callback_data: "home:gpt_chat" }],
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

  private async sendLanguageMenu(chatId: number, currentLang: string, messageId?: number, forceNew = false, showBack = false) {
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

    if (showBack) rows.push([{ text: t("back", currentLang), callback_data: "home:back" }]);
    const text = `🌐 <b>${t("lang_title", currentLang)}</b>\n\n${t("lang_hint", currentLang)}`;
    if (forceNew || !messageId) {
      await this.sendMessage(chatId, text, "HTML", { inline_keyboard: rows });
      return;
    }
    await this.sendOrEditMessage(chatId, text, { inline_keyboard: rows }, messageId, "HTML");
  }

  private async sendApiTokenMenu(chatId: number, token: string, lang: string, messageId?: number) {
    const text = t("api_token_body", lang).split("{token}").join(token);
    const replyMarkup: InlineKeyboard = {
      inline_keyboard: [
        [{ text: t("api_token_rotate", lang), callback_data: "api:rotate" }],
        [{ text: t("home_back_to_menu", lang), callback_data: "home:back" }],
      ],
    };
    await this.sendOrEditMessage(chatId, text, replyMarkup, messageId, "HTML");
  }

  private async ttsKeyboard(lang: string, userId: number, selectedVoice: string, selectedOutput: "mp3" | "voice" = "mp3", page = 0): Promise<InlineKeyboard> {
    const voices = await this.getAvailableTtsVoices(userId, lang);
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
    if (await this.isCustomVoice(userId, selectedVoice)) {
      rows.push([{ text: t("tts_delete_voice", lang), callback_data: `tts:delete:${selectedVoice}` }]);
    }
    rows.push([{ text: t("tts_demo", lang), callback_data: `tts:demo:${selectedVoice}` }]);
    rows.push([
      { text: `${selectedOutput === "mp3" ? "✔️ " : ""}${t("tts_output_mp3", lang)}`, callback_data: "tts:output:mp3" },
      { text: `${selectedOutput === "voice" ? "✔️ " : ""}${t("tts_output_voice", lang)}`, callback_data: "tts:output:voice" },
    ]);
    rows.push([{ text: t("btn_clone", lang), callback_data: "home:clone" }]);
    rows.push([{ text: t("back", lang), callback_data: "home:back" }]);
    return { inline_keyboard: rows };
  }

  private async getAvailableTtsVoices(userId: number, lang: string): Promise<string[]> {
    const defaultVoices = Object.keys(VOICES_BY_LANG[lang] || VOICES_BY_LANG.fa);
    const disabledDefault = await this.listDisabledVoices(userId, lang);
    const globalDisabled = await this.listGlobalDisabledVoices(lang);
    const customVoices = await this.listUserCustomVoices(userId);
    const disabledCustom = await this.listDisabledVoices(userId, "custom");
    return [
      ...defaultVoices.filter((name) => !disabledDefault.has(name) && !globalDisabled.has(name)),
      ...customVoices.map((voice) => voice.name).filter((name) => !disabledCustom.has(name)),
    ];
  }

  private async resolveTtsVoiceSelection(userId: number, lang: string, desiredVoice: string): Promise<string> {
    const voices = await this.getAvailableTtsVoices(userId, lang);
    if (voices.includes(desiredVoice)) return desiredVoice;
    return voices[0] || desiredVoice;
  }

  private async ttsVoiceExists(userId: number, lang: string, voiceName: string): Promise<boolean> {
    const defaultVoices = VOICES_BY_LANG[lang] || VOICES_BY_LANG.fa;
    if (voiceName in defaultVoices) return true;
    const customVoices = await this.listUserCustomVoices(userId);
    return customVoices.some((voice) => voice.name === voiceName);
  }

  private async isCustomVoice(userId: number, voiceName: string): Promise<boolean> {
    const voices = await this.listUserCustomVoices(userId);
    return voices.some((voice) => voice.name === voiceName);
  }

  private async listUserCustomVoices(userId: number): Promise<Array<{ name: string; id: string }>> {
    const raw = await this.getSetting(`TTS_USER_VOICES_${userId}`);
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw) as Record<string, string>;
      return Object.entries(parsed)
        .map(([name, id]) => ({ name, id: String(id || "") }))
        .filter((voice) => voice.name.trim().length > 0 && voice.id.trim().length > 0);
    } catch {
      return [];
    }
  }

  private async deleteUserCustomVoice(userId: number, voiceName: string): Promise<void> {
    const voices = await this.listUserCustomVoices(userId);
    const next = Object.fromEntries(voices.filter((voice) => voice.name !== voiceName).map((voice) => [voice.name, voice.id]));
    await this.setSetting(`TTS_USER_VOICES_${userId}`, JSON.stringify(next));
  }

  private async listDisabledVoices(userId: number, lang: string): Promise<Set<string>> {
    const raw = await this.getSetting(`TTS_DISABLED_USER_${userId}_${lang}`);
    if (!raw) return new Set();
    try {
      const parsed = JSON.parse(raw) as string[];
      return new Set(parsed.map((item) => String(item)));
    } catch {
      return new Set();
    }
  }

  private async listGlobalDisabledVoices(lang: string): Promise<Set<string>> {
    const raw = await this.getSetting(`TTS_DISABLED_GLOBAL_${lang}`);
    if (!raw) return new Set();
    try {
      const parsed = JSON.parse(raw) as string[];
      return new Set(parsed.map((item) => String(item)));
    } catch {
      return new Set();
    }
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
      await this.sendMessage(chatId, t("receipt_waiting_confirm", user.lang || "fa"), "HTML");
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
      const profile = await this.deps.users.getProfile(userId);
      const userLang = profile.lang || "fa";
      await this.sendMessage(chatId, t("video_gen4_processing", userLang), "HTML", {
        inline_keyboard: [[{ text: t("back", userLang), callback_data: "video_gen4:back" }]],
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
      await this.sendMessage(chatId, `✅ فایل صوتی دریافت شد.\n${t("clone_ask_name", (await this.deps.users.getProfile(userId)).lang || "fa")}`, "HTML");
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
    const user = await this.deps.users.getProfile(userId);
    const lang = user.lang || "fa";
    const refUrl = `https://t.me/${this.deps.botUsername || "VexaAiBot"}?start=${userId}`;
    await this.sendMessage(
      chatId,
      `🎁 <b>${t("invite_title", lang)}</b>\n\n${t("invite_body", lang).replace("{user_id}", String(userId)).replace("{invited}", "0").replace("{ref}", refUrl).replace("{bonus}", String(bonus))}`,
      "HTML",
      {
        inline_keyboard: [
          [{ text: t("back", lang), callback_data: "home:back" }],
          [{ text: t("invite_daily_reward", lang), callback_data: "invite:daily_reward" }],
        ],
      }
    );
  }

  private async sendHelp(chatId: number, lang = "fa") {
    await this.sendMessage(chatId, t("home_help", lang), "HTML", { inline_keyboard: [[{ text: t("home_back_to_menu", lang), callback_data: "home:back" }]] });
  }

  private async sendSora2Menu(chatId: number, lang: string, messageId?: number) {
    const text =
      "<b>🎬 خوش اومدی به بخش Sora 2</b>\n\n<b>✨ با Sora 2 می‌تونی فقط با نوشتن چند جمله، ویدیوهای واقعی و سینمایی بسازی!</b>\n<b>🚀 ساخته شده با هوش مصنوعی پیشرفته OpenAI</b>\n\n<b>🎞 هر ویدیو تا ۲۰ ثانیه و با کیفیت 1080p تولید میشه</b>\n\n<b>💰 برای فعال‌سازی دسترسی، باید «کد دعوت SORA 2» تهیه کنی.</b>\n<b>🔑 هزینه دریافت کد دعوت: 259 کردیت</b>\n\n<b>⚡ پس از پرداخت، کد اختصاصی برات ارسال میشه و می‌تونی وارد دنیای SORA بشی!</b>";
    await this.sendOrEditMessage(chatId, text, { inline_keyboard: [[{ text: t("sora2_btn_buy", lang), callback_data: "sora2:buy" }], [{ text: t("home_back_to_menu", lang), callback_data: "home:back" }]] }, messageId, "HTML");
  }

  private async sendSora2NoCredit(chatId: number, lang: string, messageId: number | undefined, credits: number) {
    const text = `⚠️ <b>کردیت کافی نیست!</b>\n<b>هزینه خرید کد دعوت: ${SORA2_COST} کردیت</b>\n<b>موجودی فعلی: ${credits} کردیت</b>\n\n<b>برای شارژ دکمه «خرید کردیت» رو بزن.</b>`;
    await this.sendOrEditMessage(
      chatId,
      text,
      { inline_keyboard: [[{ text: t("btn_credit", lang), callback_data: "credit:menu" }], [{ text: t("home_back_to_menu", lang), callback_data: "home:back" }]] },
      messageId,
      "HTML"
    );
  }

  private async sendSora2PurchaseSuccess(chatId: number, lang: string, messageId?: number) {
    const text = `<b>✅ پرداخت موفق!</b>\n<b>${SORA2_COST} کردیت از حسابت کم شد 💳</b>\n<b>⌛ تو صف انتظار هستی (نفر ${SORA2_QUEUE_START})</b>\n<b>🎟 کد دعوت Sora 2 به‌زودی برات ارسال میشه.</b>`;
    await this.sendOrEditMessage(chatId, text, { inline_keyboard: [[{ text: t("sora2_btn_buy", lang), callback_data: "sora2:buy" }], [{ text: t("home_back_to_menu", lang), callback_data: "home:back" }]] }, messageId, "HTML");
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
    await this.sendMessage(chatId, t("onboarding_welcome", _lang).replace("{credits}", "45"), "HTML");
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
      await this.sendMessage(chatId, t("onboarding_daily_bonus_ready", _lang), "HTML", {
        inline_keyboard: [[{ text: t("onboarding_bonus_button", _lang), callback_data: "onboarding:daily_reward" }]],
      });
      await this.deps.userState.setBotState(userId, { ...state, dailyBonusPromptedAt: now, updatedAt: now });
      return;
    }

    if (state.dailyBonusPromptedAt && !state.dailyBonusUnlockedAt && now - state.dailyBonusPromptedAt >= ONBOARDING_DAILY_BONUS_UNLOCK_DELAY) {
      await this.sendMessage(chatId, t("onboarding_daily_bonus_unlocked", _lang), "HTML", {
        inline_keyboard: [[{ text: t("onboarding_bonus_button", _lang), callback_data: "onboarding:invite" }]],
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
        ...(hasTg ? [[{ text: t("force_sub_btn_join_channel", _lang), url: `https://t.me/${normalized}` }]] : []),
        ...(hasIg ? [[{ text: t("force_sub_btn_follow_instagram", _lang), url: igUrl }]] : []),
        [{ text: t("force_sub_btn_joined", _lang), callback_data: "fs:recheck" }],
      ],
    };
    const lines = [t("force_sub_title", _lang)];
    if (hasTg) lines.push(t("force_sub_join_channel", _lang));
    if (hasIg) lines.push(t("force_sub_join_instagram", _lang));
    lines.push("", t("force_sub_hint", _lang));
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

  private hasBannedWord(text: string): boolean {
    const replacements: Record<string, string> = { ك: "ک", ي: "ی", ى: "ی", ؤ: "و", إ: "ا", أ: "ا", آ: "ا", ة: "ه", "ۀ": "ه" };
    let normalized = (text || "").toLowerCase();
    for (const [src, dst] of Object.entries(replacements)) normalized = normalized.split(src).join(dst);
    normalized = normalized.split("ـ").join("").split("\u200c").join(" ").split("\u200d").join("");
    return BANNED_WORDS.some((word) => {
      const normalizedWord = word.toLowerCase();
      return normalizedWord.length > 0 && normalized.includes(normalizedWord);
    });
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
