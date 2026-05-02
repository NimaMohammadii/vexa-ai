import type { OwnerNotificationService, TelegramWebhookService } from "./user-services";
import type { BotConversationState, UserStateRepository } from "../storage/user-state-repository";
import type { ApiTokenService, CreditService, GptHistoryService, UserService } from "./user-services";

interface TelegramUser {
  id: number;
  username?: string;
  first_name?: string;
  last_name?: string;
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
  openAiApiKey?: string;
  elevenLabsApiKey?: string;
  users: UserService;
  credits: CreditService;
  tokens: ApiTokenService;
  history: GptHistoryService;
  userState: UserStateRepository;
  telegramEvents: TelegramWebhookService;
  ownerNotifications: OwnerNotificationService;
}

type InlineKeyboard = { inline_keyboard: Array<Array<{ text: string; callback_data?: string; url?: string }>> };
type ReplyKeyboard = { keyboard: Array<Array<{ text: string }>>; resize_keyboard?: boolean; one_time_keyboard?: boolean };
type ParseMode = "HTML" | "Markdown";

const nowTs = () => Math.floor(Date.now() / 1000);
const CREDIT_PER_CHAR = 1;
const GPT_MESSAGE_COST = 5;
const GPT_HISTORY_LIMIT = 20;
const TTS_DEMO_AUTO_DELETE_SECONDS = 50;

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

const STAR_PACKAGES = [
  { stars: 250, credits: 8000, title: "• Starter " },
  { stars: 1000, credits: 40000, title: "🎯 Creator " },
  { stars: 3000, credits: 120000, title: "⚡️ Pro " },
  { stars: 5500, credits: 300000, title: "👑 Studio" },
];

const PAYMENT_PLANS = [
  { title: " 800 → 150,000T", amountToman: 150000, credits: 800 },
  { title: " 2899 → 340,000T", amountToman: 340000, credits: 2899 },
  { title: " 6100 → 550,000T", amountToman: 550000, credits: 6100 },
  { title: " 9200 → 770,000T", amountToman: 770000, credits: 9200 },
  { title: " 12K + 1k → 999,000T", amountToman: 999000, credits: 13000 },
  { title: " 21K → 1,650,000T", amountToman: 1650000, credits: 21000 },
  { title: " 46K → 3,420,000T", amountToman: 3420000, credits: 46000 },
  { title: " 88K → 5,990,000T", amountToman: 5990000, credits: 88000 },
  { title: " 120K → 8,100,000T", amountToman: 8100000, credits: 120000 },
  { title: " 150K → 9,999,000T", amountToman: 9999000, credits: 150000 },
];

const DEFAULT_VOICE_BY_LANG: Record<string, string> = { fa: "Liam", en: "Ava", ar: "Liam", tr: "Arda", ru: "Алина", es: "Valeria", de: "Lena", fr: "Léa" };
const VOICES_BY_LANG: Record<string, Record<string, string>> = {
  fa: { Liam: "TX3LPaxmHKxFdv7VOQHJ", Amir: "1SM7GgM6IMuvQlz2BwM3", Nazy: "tnSpp4vdxKPjI9w0GnoV", Sarah: "BIvP0GN1cAtSRTxNHnWS", Alex: "GFGuOkimbpNkTEOVDkqX", Noushin: "NZiuR1C6kVMSWHG27sIM", Paniz: "BZgkqPqms7Kj9ulSkVzn", Alexandra: "kdmDKE6EkgrWrrykO9Qt", Laura: "7piC4m7q8WrpEAnMj5xC", Maxon: "0dPqNXnhg2bmxQv1WKDp", Jessica: "cgSgspJ2msm6clMCkdW9", Austin: "Bj9UqZbhQsanLzgalpEG", priyanka: "BpjGufoPiobT79j2vtj4", horatius: "qXpMhyvQqiRxWQs4qSSB", anika: "Sm1seazb4gs7RSlUVw7c", brock: "DGzg6RaUqxGRTHSBjfgF", Xavier: "YOq2y2Up4RgXP2HyXjE5", Bradford: "NNl6r8mD7vthiJatiJt1" },
  en: { Liam: "TX3LPaxmHKxFdv7VOQHJ", Noah: "1SM7GgM6IMuvQlz2BwM3", Ava: "tnSpp4vdxKPjI9w0GnoV", Nora: "BIvP0GN1cAtSRTxNHnWS", Alex: "GFGuOkimbpNkTEOVDkqX", Ella: "NZiuR1C6kVMSWHG27sIM", Chloe: "BZgkqPqms7Kj9ulSkVzn", Alexandra: "kdmDKE6EkgrWrrykO9Qt", Laura: "7piC4m7q8WrpEAnMj5xC", Maxon: "0dPqNXnhg2bmxQv1WKDp", Jessica: "cgSgspJ2msm6clMCkdW9", Austin: "Bj9UqZbhQsanLzgalpEG", Lucas: "NNl6r8mD7vthiJatiJt1" },
  ar: { Liam: "TX3LPaxmHKxFdv7VOQHJ", Amir: "1SM7GgM6IMuvQlz2BwM3", Nazy: "tnSpp4vdxKPjI9w0GnoV", Sarah: "BIvP0GN1cAtSRTxNHnWS", Alex: "GFGuOkimbpNkTEOVDkqX", Noushin: "NZiuR1C6kVMSWHG27sIM", Paniz: "BZgkqPqms7Kj9ulSkVzn" },
  tr: { Arda: "TX3LPaxmHKxFdv7VOQHJ", Emre: "1SM7GgM6IMuvQlz2BwM3", Deniz: "tnSpp4vdxKPjI9w0GnoV", Sarah: "BIvP0GN1cAtSRTxNHnWS", Burak: "GFGuOkimbpNkTEOVDkqX", Selin: "NZiuR1C6kVMSWHG27sIM" },
  ru: { "Илья": "TX3LPaxmHKxFdv7VOQHJ", "Никита": "1SM7GgM6IMuvQlz2BwM3", "Алина": "tnSpp4vdxKPjI9w0GnoV", "Милана": "BIvP0GN1cAtSRTxNHnWS" },
  es: { Mateo: "TX3LPaxmHKxFdv7VOQHJ", Leo: "1SM7GgM6IMuvQlz2BwM3", Valeria: "tnSpp4vdxKPjI9w0GnoV", "Sofía": "BIvP0GN1cAtSRTxNHnWS" },
  de: { Leon: "TX3LPaxmHKxFdv7VOQHJ", Luca: "1SM7GgM6IMuvQlz2BwM3", Lena: "tnSpp4vdxKPjI9w0GnoV", Mia: "BIvP0GN1cAtSRTxNHnWS" },
  fr: { Hugo: "TX3LPaxmHKxFdv7VOQHJ", Noah: "1SM7GgM6IMuvQlz2BwM3", "Léa": "tnSpp4vdxKPjI9w0GnoV", "Inès": "BIvP0GN1cAtSRTxNHnWS" },
};

const I18N: Record<string, Record<string, string>> = {
  home_title: { fa: "/help   منوی اصلی", en: "Main Menu", ar: "القائمة الرئيسية", tr: "Ana Menü", ru: "Главное меню", es: "Menú principal", de: "Hauptmenü", fr: "Menu principal" },
  home_body: { fa: "یکی از گزینه‌های زیر را انتخاب کنید:", en: "Choose an option:", ar: "اختر خياراً:", tr: "Bir seçenek seçin:", ru: "Выберите опцию:", es: "Elige una opción:", de: "Wähle eine Option:", fr: "Choisissez une option :" },
  btn_profile: { fa: "موجودی شما", en: "Your Balance", ar: "رصيدك", tr: "Bakiyeniz", ru: "Ваш баланс", es: "Tu saldo", de: "Dein Guthaben", fr: "Ton solde" },
  btn_credit: { fa: "خرید کردیـت 🛒", en: "Buy Credit 🛒", ar: "شراء الرصيد 🛒", tr: "Kredi Satın Al 🛒", ru: "Купить кредит 🛒", es: "Comprar crédito 🛒", de: "Guthaben kaufen 🛒", fr: "Acheter du crédit 🛒" },
  btn_tts: { fa: "تبدیل متن به صدا 🎧", en: "Text to Speech 🎧", ar: "تحويل النص إلى صوت 🎧", tr: "Metinden Sese 🎧", ru: "Текст в речь 🎧", es: "Texto a voz 🎧", de: "Text zu Sprache 🎧", fr: "Texte en voix 🎧" },
  btn_gpt: { fa: "GPT-5 mini 🫧", en: "GPT-5 mini 🫧", ar: "GPT-5 mini 🫧", tr: "GPT-5 mini 🫧", ru: "GPT-5 mini 🫧", es: "GPT-5 mini 🫧", de: "GPT-5 mini 🎪", fr: "GPT-5 mini 🎪" },
  btn_lang: { fa: "Language 📚", en: "Language 📚", ar: "اللغة 📚", tr: "Dil 📚", ru: "Язык 📚", es: "Idioma 📚", de: "Sprache 📚", fr: "Langue 📚" },
  btn_invite: { fa: "🎁", en: "🎁", ar: "دعوة الأصدقاء 🎁", tr: "🎁", ru: "🎁", es: "🎁", de: "🎁", fr: "🎁" },
  back: { fa: "🔙 بازگشت", en: "🔙 Back", ar: "🔙 رجوع", tr: "🔙 Geri", ru: "🔙 Назад", es: "🔙 Volver", de: "🔙 Zurück", fr: "🔙 Retour" },
  home_back_to_menu: { fa: "🏠 منوی اصلی", en: "🏠 Main menu", ar: "🏠 القائمة الرئيسية", tr: "🏠 Ana menü", ru: "🏠 Главное меню", es: "🏠 Menú principal", de: "🏠 Hauptmenü", fr: "🏠 Menu principal" },
  lang_title: { fa: "انتخاب زبان", en: "Choose language", ar: "اختر اللغة", tr: "Dil seç", ru: "Выберите язык", es: "Elige idioma", de: "Sprache wählen", fr: "Choisir la langue" },
  lang_hint: { fa: "یکی از زبان‌های زیر را انتخاب کن.", en: "Select one of the languages below.", ar: "اختر إحدى اللغات أدناه.", tr: "Aşağıdaki dillerden birini seç.", ru: "Выберите один из языков ниже.", es: "Elige uno de los idiomas de abajo.", de: "Wähle eine der folgenden Sprachen.", fr: "Choisis l'une des langues ci-dessous." },
  lang_saved: { fa: "✅ زبان ذخیره شد.", en: "✅ Language saved.", ar: "✅ تم حفظ اللغة.", tr: "✅ Dil kaydedildi.", ru: "✅ Язык сохранён.", es: "✅ Idioma guardado.", de: "✅ Sprache gespeichert.", fr: "✅ Langue enregistrée." },
  tts_prompt: { fa: "✨ <b>متن رو بفرست (هر کاراکتر = {credit} Credit)</b>", en: "✍🏼 Send your text (1 character = {credit} credit)", ar: "✍🏼 أرسل النص (كل حرف = {credit} رصيد)", tr: "✍🏼 Metni gönder (her karakter = {credit} kredi)", ru: "✍🏼 Отправьте текст (каждый символ = {credit} кредит)", es: "✍🏼 Envía tu texto (cada carácter = {credit} crédito)", de: "✍🏼 Sende deinen Text (jedes Zeichen = {credit} Kredit)", fr: "✍🏼 Envoie ton texte (chaque caractère = {credit} crédit)" },
  tts_demo: { fa: "▶︎ دمو", en: "▶︎ Demo", ar: "▶︎ عرض تجريبي", tr: "▶︎ Demo", ru: "▶︎ Демо", es: "▶︎ Demo", de: "▶︎ Demo", fr: "▶︎ Démo" },
  tts_processing: { fa: "👀 <b>در حال تبدیل...</b>", en: "⏳ Converting..." },
  tts_no_credit: { fa: "⚠️ <b>کردیت کافی نیست</b>\n<b>موجودی شما: {credits} کردیت</b>\n<b>کردیت لازم: {required}</b>\n<b>می‌تونی کردیت بخری یا متن رو کوتاه‌تر کنی /help</b>", en: "⚠️ <b>Not enough credits</b>\n<b>Your balance: {credits}</b>\n<b>Required: {required}</b>" },
  tts_error: { fa: "⚠️ <b>خطا در تبدیل٫ دوباره تلاش کن</b>", en: "⚠️ Conversion failed. Try again." },
  tts_demo_missing: { fa: "❌ دموی این صدا هنوز تنظیم نشده است.", en: "❌ Demo for this voice is not available yet." },
  tts_demo_wait: { fa: "⏳ دموی این صدا ارسال شده. لطفاً تا حذف شدنش صبر کنید.", en: "⏳ Demo already sent. Please wait for it to be deleted." },
  tts_output_mp3: { fa: "MP3 📁", en: "MP3 📁" },
  tts_output_voice: { fa: "Voice 🎙️", en: "Voice 🎙️" },
  tts_next: { fa: "بعدی ➜", en: "Next ➜" },
  tts_prev: { fa: "⬅︎ قبل", en: "⬅︎ Previous" },
  credit_title: { fa: "خرید کردیت", en: "Buy credits" },
  credit_header: { fa: "برای استفاده از ربات، کردیت لازم دارید", en: "Pick a package below to top up your balance." },
  credit_pay_stars_btn: { fa: "خرید با Telegram Stars 🌟", en: "Buy with Telegram Stars 🌟" },
  credit_pay_rial_btn: { fa: "پرداخت به تومان", en: "Pay in Toman" },
  credit_cancel: { fa: "لغو ❌", en: "Cancel ❌" },
  credit_unavailable: { fa: "پرداخت به تومان فقط برای کاربران فارسی فعال است.", en: "Payments in tomans are only available in the Persian language." },
  credit_stars_menu: { fa: "🌟 شارژ آنی با Telegram Stars\n\nیکی از بسته‌های زیر را انتخاب کن:", en: "🌟 Instant top-up with Telegram Stars\n\nPick one of the packages below:" },
  credit_invoice_label: { fa: "{credits} کردیت", en: "{credits} credits" },
  credit_invoice_title: { fa: "Vexa — خرید کردیت", en: "Vexa — Buy Credits" },
  credit_invoice_desc: { fa: "شارژ موجودی با Telegram Stars.", en: "Top up your balance with Telegram Stars." },
  credit_invoice_sent: { fa: "فاکتور ارسال شد", en: "Invoice sent" },
  credit_pay_success: { fa: "✅ پرداخت موفق: ⭐{stars}\n🎉 {credits} کردیت اضافه شد.\n💳 موجودی: {balance}", en: "✅ Payment successful: ⭐{stars}\n🎉 {credits} credits added.\n💳 Balance: {balance}" },
  invite_title: { fa: "🎁 دعوت دوستان", en: "🎁 Invite friends" },
  invite_body: { fa: "لینک اختصاصی دعوت شما:\n{link}\n\nبا هر دعوت موفق، دوستت وارد Vexa میشه و شما هم پاداش می‌گیرید.", en: "Your personal invite link:\n{link}" },
  gpt_open: { fa: "🤖 <b>چت GPT آماده است.</b>\nهر پیام {cost} کردیت هزینه دارد. سوالت را بفرست.\nبرای خروج دکمه پایان چت را بزن.", en: "🤖 <b>GPT chat is ready.</b>\nEach message costs {cost} credits. Send your question." },
  gpt_end_button: { fa: "پایان چت GPT", en: "End GPT chat" },
  gpt_end: { fa: "✅ چت GPT تمام شد.", en: "✅ GPT chat ended." },
  gpt_wait: { fa: "در حال فکر کردن...", en: "Thinking..." },
  gpt_no_credit: { fa: "⚠️ <b>کردیت کافی نیست</b>\n<b>موجودی: {balance}</b>\n<b>هزینه پیام: {cost}</b>", en: "⚠️ Not enough credits. Balance: {balance}, cost: {cost}" },
  gpt_not_configured: { fa: "⚠️ GPT هنوز روی Worker تنظیم نشده است. OPENAI_API_KEY را به secrets اضافه کن.", en: "⚠️ GPT is not configured. Add OPENAI_API_KEY to Worker secrets." },
  gpt_error: { fa: "⚠️ خطا در پاسخ GPT: {error}", en: "⚠️ GPT error: {error}" },
};

function t(key: string, lang = "fa"): string {
  return I18N[key]?.[lang] ?? I18N[key]?.fa ?? I18N[key]?.en ?? key;
}
function fmt(template: string, values: Record<string, string | number>) {
  return Object.entries(values).reduce((text, [key, value]) => text.replaceAll(`{${key}}`, String(value)), template);
}
function mainText(lang: string) { return `🏠 <b>${t("home_title", lang)}</b>\n\n${t("home_body", lang)}`; }
function mainMenu(lang: string): InlineKeyboard {
  return { inline_keyboard: [
    [{ text: t("btn_profile", lang), callback_data: "home:profile" }, { text: t("btn_credit", lang), callback_data: "home:credit" }],
    [{ text: t("btn_tts", lang), callback_data: "home:tts" }],
    [{ text: t("btn_gpt", lang), callback_data: "home:gpt_chat" }],
    [{ text: t("btn_lang", lang), callback_data: "home:lang" }, { text: t("btn_invite", lang), callback_data: "home:invite" }],
  ] };
}
function backMenu(lang: string): InlineKeyboard { return { inline_keyboard: [[{ text: t("home_back_to_menu", lang), callback_data: "home:back" }]] }; }
function langMenu(): InlineKeyboard { return { inline_keyboard: LANGS.map((l) => [{ text: l.label, callback_data: `lang:set:${l.code}` }]) }; }
function creditMenu(lang: string): InlineKeyboard { return { inline_keyboard: [[{ text: t("credit_pay_stars_btn", lang), callback_data: "credit:stars" }], [{ text: t("credit_pay_rial_btn", lang), callback_data: "credit:payrial" }], [{ text: t("home_back_to_menu", lang), callback_data: "home:back" }]] }; }
function starsMenu(lang: string): InlineKeyboard { return { inline_keyboard: [...STAR_PACKAGES.map((p) => [{ text: `${p.title} — ⭐${p.stars} / ${p.credits} Credit`, callback_data: `credit:buy:${p.stars}:${p.credits}` }]), [{ text: t("back", lang), callback_data: "credit:menu" }]] }; }
function rialMenu(lang: string): InlineKeyboard { return { inline_keyboard: [...PAYMENT_PLANS.map((p, i) => [{ text: p.title, callback_data: `credit:select:${i}` }]), [{ text: t("back", lang), callback_data: "credit:menu" }]] }; }
function receiptMenu(lang: string): InlineKeyboard { return { inline_keyboard: [[{ text: t("credit_cancel", lang), callback_data: "credit:cancel" }]] }; }
function adminReceiptMenu(userId: number, planIndex: number): InlineKeyboard { return { inline_keyboard: [[{ text: "✅ تایید", callback_data: `credit_admin:approve:${userId}:${planIndex}` }, { text: "❌ رد", callback_data: `credit_admin:reject:${userId}:${planIndex}` }]] }; }
function gptReplyMenu(lang: string): ReplyKeyboard { return { keyboard: [[{ text: t("gpt_end_button", lang) }]], resize_keyboard: true }; }

function getVoices(lang: string) { return VOICES_BY_LANG[lang] ?? VOICES_BY_LANG.fa; }
function defaultVoice(lang: string) { return DEFAULT_VOICE_BY_LANG[lang] ?? "Liam"; }
function ttsText(lang: string, voice: string) { return `${fmt(t("tts_prompt", lang), { credit: CREDIT_PER_CHAR })}\n\n🎙 صدا: <b>${voice}</b>`; }
function ttsMenu(lang: string, voice: string, page = 0, output: "mp3" | "voice" = "mp3"): InlineKeyboard {
  const voices = Object.keys(getVoices(lang));
  const pageSize = 6;
  const maxPage = Math.max(0, Math.ceil(voices.length / pageSize) - 1);
  const safePage = Math.min(Math.max(0, page), maxPage);
  const visible = voices.slice(safePage * pageSize, safePage * pageSize + pageSize);
  const rows = visible.map((name) => [{ text: name === voice ? `✅ ${name}` : name, callback_data: `tts:voice:${name}` }]);
  rows.push([{ text: t("tts_demo", lang), callback_data: `tts:demo:${voice}` }]);
  rows.push([{ text: output === "mp3" ? `✅ ${t("tts_output_mp3", lang)}` : t("tts_output_mp3", lang), callback_data: "tts:output:mp3" }, { text: output === "voice" ? `✅ ${t("tts_output_voice", lang)}` : t("tts_output_voice", lang), callback_data: "tts:output:voice" }]);
  rows.push([{ text: t("tts_prev", lang), callback_data: "tts:page:prev" }, { text: t("tts_next", lang), callback_data: "tts:page:next" }]);
  rows.push([{ text: t("back", lang), callback_data: "tts:back" }]);
  return { inline_keyboard: rows };
}

export class TelegramBotFlowService {
  constructor(private deps: TelegramBotFlowDeps) {}

  async handleWebhook(update: TelegramWebhookUpdate) {
    const userId = update.message?.from?.id ?? update.callback_query?.from?.id ?? update.pre_checkout_query?.from?.id ?? null;
    const eventType = update.pre_checkout_query ? "pre_checkout_query" : update.callback_query ? "callback_query" : update.message?.successful_payment ? "successful_payment" : "message";
    if (await this.deps.telegramEvents.shouldSkipUpdate(update.update_id)) return { ok: true, skipped: true };
    if (update.pre_checkout_query) await this.answerPreCheckoutQuery(update.pre_checkout_query.id, true);
    else if (update.callback_query) await this.handleCallback(update.callback_query);
    else if (update.message) await this.handleMessage(update.message);
    if (update.update_id !== undefined) await this.deps.telegramEvents.markProcessed(update.update_id, userId, eventType);
    return { ok: true };
  }

  private async handleMessage(msg: NonNullable<TelegramWebhookUpdate["message"]>) {
    if (!msg.from || !msg.chat) return;
    const user = await this.bootstrap(msg.from);
    const lang = user.lang || "fa";
    const text = (msg.text || "").trim();
    if (msg.successful_payment) return this.handleSuccessfulPayment(msg, user.userId, lang);
    const state = await this.deps.userState.getBotState(user.userId);
    if (text.startsWith("/start")) return this.start(msg, user.userId, lang, text);
    if (text === "/menu") return this.showHome(msg.chat.id, user.userId, lang, msg.message_id);
    if (text === "/help") return this.editOrSend(msg.chat.id, msg.message_id, "<b>📖 راهنمای استفاده از Vexa</b>\n\nاز منو برای تبدیل متن به صدا، GPT، خرید کردیت، دعوت دوستان و تغییر زبان استفاده کن.", backMenu(lang));
    if (text === "/gpt") return this.openGpt(msg.chat.id, msg.message_id, user.userId, lang);
    if (state.waitingReceipt && msg.photo?.length) return this.handleReceipt(msg, user.userId, lang, state);
    if (state.mode === "tts:wait_text" && text) return this.handleTtsText(msg, user.userId, lang, state, text);
    if (state.mode === "gpt:chat" && text) return this.handleGptText(msg.chat.id, user.userId, lang, text);
    return this.showHome(msg.chat.id, user.userId, lang, msg.message_id);
  }

  private async handleCallback(cq: NonNullable<TelegramWebhookUpdate["callback_query"]>) {
    if (!cq.from || !cq.message?.chat) return;
    const user = await this.bootstrap(cq.from);
    const lang = user.lang || "fa";
    const data = cq.data || "";
    const chatId = cq.message.chat.id;
    const msgId = cq.message.message_id;
    if (data === "home:back") { await this.answerCallbackQuery(cq.id); return this.showHome(chatId, user.userId, lang, msgId); }
    if (data === "home:tts") { await this.answerCallbackQuery(cq.id); return this.openTts(chatId, msgId, user.userId, lang); }
    if (data === "home:credit" || data === "credit:menu") { await this.answerCallbackQuery(cq.id); return this.openCredit(chatId, msgId, lang); }
    if (data === "home:gpt_chat") { await this.answerCallbackQuery(cq.id); return this.openGpt(chatId, msgId, user.userId, lang); }
    if (data === "home:invite") { await this.answerCallbackQuery(cq.id); return this.openInvite(chatId, msgId, user.userId, lang); }
    if (data === "home:lang") { await this.answerCallbackQuery(cq.id); return this.openLang(chatId, msgId, lang); }
    if (data.startsWith("lang:set:")) { await this.answerCallbackQuery(cq.id, t("lang_saved", data.split(":")[2] || lang)); return this.setLang(chatId, msgId, user.userId, data.split(":")[2] || "fa"); }
    if (data.startsWith("tts:")) { await this.answerCallbackQuery(cq.id); return this.handleTtsCallback(chatId, msgId, user.userId, lang, data); }
    if (data.startsWith("credit:")) { await this.answerCallbackQuery(cq.id); return this.handleCreditCallback(chatId, msgId, user.userId, lang, data); }
    if (data.startsWith("credit_admin:")) return this.handleCreditAdmin(cq.id, chatId, msgId, data);
    await this.answerCallbackQuery(cq.id);
  }

  private async bootstrap(from: TelegramUser) {
    const user = await this.deps.users.bootstrapTelegramUser({ userId: from.id, username: from.username ?? null, firstName: from.first_name ?? null });
    await this.deps.users.touchLastSeen(from.id);
    return user;
  }

  private async start(msg: NonNullable<TelegramWebhookUpdate["message"]>, userId: number, lang: string, text: string) {
    const ref = text.split(/\s+/, 2)[1];
    const state = await this.deps.userState.getBotState(userId);
    if (ref) await this.deps.userState.setBotState(userId, { ...state, pendingReferralCode: ref, updatedAt: nowTs() });
    await this.showHome(msg.chat!.id, userId, lang, msg.message_id);
  }

  private async showHome(chatId: number, userId: number, lang: string, messageId?: number) {
    await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
    return this.editOrSend(chatId, messageId, mainText(lang), mainMenu(lang));
  }

  private async openLang(chatId: number, messageId: number | undefined, lang: string) {
    return this.editOrSend(chatId, messageId, `🌐 <b>${t("lang_title", lang)}</b>\n\n${t("lang_hint", lang)}`, langMenu());
  }

  private async setLang(chatId: number, messageId: number | undefined, userId: number, lang: string) {
    await this.deps.users.setLanguage(userId, lang);
    await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs(), langSelected: true });
    return this.editOrSend(chatId, messageId, t("lang_saved", lang), mainMenu(lang));
  }

  private async openInvite(chatId: number, messageId: number | undefined, userId: number, lang: string) {
    const bot = this.deps.botUsername || "VexaBot";
    const link = `https://t.me/${bot}?start=${userId}`;
    return this.editOrSend(chatId, messageId, `🎁 <b>${t("invite_title", lang)}</b>\n\n${fmt(t("invite_body", lang), { link })}`, backMenu(lang));
  }

  private async openCredit(chatId: number, messageId: number | undefined, lang: string) {
    return this.editOrSend(chatId, messageId, `🛒 <b>${t("credit_title", lang)}</b>\n\n${t("credit_header", lang)}`, creditMenu(lang));
  }

  private async handleCreditCallback(chatId: number, messageId: number | undefined, userId: number, lang: string, data: string) {
    if (data === "credit:stars") return this.editOrSend(chatId, messageId, t("credit_stars_menu", lang), starsMenu(lang));
    if (data.startsWith("credit:buy:")) {
      const [, , starsRaw, creditsRaw] = data.split(":");
      const stars = Number(starsRaw); const credits = Number(creditsRaw);
      return this.sendInvoice(userId, fmt(t("credit_invoice_title", lang), { credits }), t("credit_invoice_desc", lang), JSON.stringify({ user_id: userId, credits }), stars, credits, lang);
    }
    if (data === "credit:payrial") {
      if (lang !== "fa") return this.sendMessage(chatId, t("credit_unavailable", lang), { parse_mode: "HTML" });
      return this.editOrSend(chatId, messageId, "🧾 <b>پرداخت به تومان</b>\n\nبا خرید هر بسته 30% کردیت بیشتر دریافت میکنید\nیکی از بسته‌های زیر را انتخاب کنید:", rialMenu(lang));
    }
    if (data.startsWith("credit:select:")) {
      const planIndex = Number(data.split(":")[2]);
      const plan = PAYMENT_PLANS[planIndex];
      if (!plan) return this.sendMessage(chatId, "بسته نامعتبر است.");
      const state = await this.deps.userState.getBotState(userId);
      await this.deps.userState.setBotState(userId, { ...state, mode: "idle", waitingReceipt: true, selectedPlanIndex: planIndex, updatedAt: nowTs() });
      const card = this.deps.cardNumber || "CARD_NUMBER_NOT_SET";
      const body = `💱 <b>پرداخت فـوری (کارت‌به‌کارت)</b>\n<b>شماره کارت:</b><code>${card}</code>\n\n• دقیقاً مبلغ <b>${plan.amountToman.toLocaleString("en-US")} تومان</b> پرداخت کنید\n• سپس <b>تصویر رسید</b> را همین‌جا ارسال کنید\n\n✅ <b>پس از تایید، <b>${plan.credits.toLocaleString("en-US")} کردیت</b> + 30% کردیت اضافه به حساب شما اضافه خواهد شد (کمتر از ۵ دقیقه)</b>`;
      return this.editOrSend(chatId, messageId, body, receiptMenu(lang));
    }
    if (data === "credit:cancel") {
      await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
      return this.showHome(chatId, userId, lang, messageId);
    }
  }

  private async handleReceipt(msg: NonNullable<TelegramWebhookUpdate["message"]>, userId: number, lang: string, state: BotConversationState) {
    const planIndex = state.selectedPlanIndex ?? 0;
    const plan = PAYMENT_PLANS[planIndex];
    await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
    const photo = msg.photo?.[msg.photo.length - 1]?.file_id;
    if (photo && this.deps.ownerTelegramChatId) {
      const caption = `🧾 <b>رسید پرداخت جدید</b>\n• User ID: <code>${userId}</code>\n• Username: @${msg.from?.username || "-"}\n• Name: ${msg.from?.first_name || ""} ${msg.from?.last_name || ""}\n\n• مبلغ: ${plan?.amountToman.toLocaleString("en-US") || "-"} تومان\n• کردیت: ${plan?.credits.toLocaleString("en-US") || "-"}`;
      await this.callTelegram("sendPhoto", { chat_id: this.deps.ownerTelegramChatId, photo, caption, parse_mode: "HTML", reply_markup: adminReceiptMenu(userId, planIndex) });
    }
    await this.sendMessage(msg.chat!.id, "✅ رسید دریافت شد\n⏳ <b>لطفاً منتظر تایید باش</b>", { parse_mode: "HTML" });
    return this.showHome(msg.chat!.id, userId, lang);
  }

  private async handleCreditAdmin(callbackId: string, chatId: number, messageId: number | undefined, data: string) {
    const [, action, userRaw, planRaw] = data.split(":");
    const userId = Number(userRaw); const plan = PAYMENT_PLANS[Number(planRaw)];
    if (!plan) return this.answerCallbackQuery(callbackId, "بسته نامعتبر", true);
    if (action === "approve") {
      await this.deps.credits.grant(userId, plan.credits, "manual_rial_payment", "telegram_bot");
      await this.sendMessage(userId, `✅ <b>پرداخت تأیید شد!</b>\n\n💎 <b>${plan.credits.toLocaleString("en-US")} کردیت</b> به حساب شما اضافه شد.\n💰 مبلغ: ${plan.amountToman.toLocaleString("en-US")} تومان`, { parse_mode: "HTML" });
      await this.answerCallbackQuery(callbackId, `✅ تأیید شد - ${plan.credits} کردیت اضافه شد`);
      return this.callTelegram("editMessageCaption", { chat_id: chatId, message_id: messageId, caption: "✅ <b>تأیید شده توسط ادمین</b>", parse_mode: "HTML" });
    }
    await this.sendMessage(userId, "❌ <b>پرداخت رد شد</b>\n\nرسید ارسالی تأیید نشد. در صورت اطمینان از صحت پرداخت، مجدداً رسید ارسال کنید یا با پشتیبانی تماس بگیرید.", { parse_mode: "HTML" });
    await this.answerCallbackQuery(callbackId, "❌ پرداخت رد شد");
    return this.callTelegram("editMessageCaption", { chat_id: chatId, message_id: messageId, caption: "❌ <b>رد شده توسط ادمین</b>", parse_mode: "HTML" });
  }

  private async handleSuccessfulPayment(msg: NonNullable<TelegramWebhookUpdate["message"]>, userId: number, lang: string) {
    const payload = JSON.parse(msg.successful_payment?.invoice_payload || "{}");
    const credits = Number(payload.credits || 0);
    const stars = Number(msg.successful_payment?.total_amount || 0);
    if (credits > 0) await this.deps.credits.grant(userId, credits, "telegram_stars_payment", "telegram_bot");
    const balance = await this.deps.credits.getCredits(userId);
    return this.sendMessage(msg.chat!.id, fmt(t("credit_pay_success", lang), { stars, credits, balance: balance.credits }), { parse_mode: "HTML" });
  }

  private async openTts(chatId: number, messageId: number | undefined, userId: number, lang: string) {
    const voice = defaultVoice(lang);
    await this.deps.userState.setBotState(userId, { mode: "tts:wait_text", updatedAt: nowTs(), ttsVoice: voice, ttsOutput: "mp3", ttsPage: 0 });
    return this.editOrSend(chatId, messageId, ttsText(lang, voice), ttsMenu(lang, voice));
  }

  private async handleTtsCallback(chatId: number, messageId: number | undefined, userId: number, lang: string, data: string) {
    const state = await this.deps.userState.getBotState(userId);
    if (data === "tts:back") return this.showHome(chatId, userId, lang, messageId);
    let voice = state.ttsVoice || defaultVoice(lang);
    let page = state.ttsPage || 0;
    let output = state.ttsOutput || "mp3";
    if (data.startsWith("tts:voice:")) voice = data.split(":").slice(2).join(":");
    if (data === "tts:page:next") page += 1;
    if (data === "tts:page:prev") page = Math.max(0, page - 1);
    if (data === "tts:output:mp3") output = "mp3";
    if (data === "tts:output:voice") output = "voice";
    if (data.startsWith("tts:demo:")) return this.sendMessage(chatId, t("tts_demo_missing", lang));
    await this.deps.userState.setBotState(userId, { ...state, mode: "tts:wait_text", ttsVoice: voice, ttsOutput: output, ttsPage: page, updatedAt: nowTs() });
    return this.editOrSend(chatId, messageId, ttsText(lang, voice), ttsMenu(lang, voice, page, output));
  }

  private async handleTtsText(msg: NonNullable<TelegramWebhookUpdate["message"]>, userId: number, lang: string, state: BotConversationState, text: string) {
    const cost = text.length * CREDIT_PER_CHAR;
    const balance = await this.deps.credits.getCredits(userId);
    if (balance.credits < cost) return this.sendMessage(msg.chat!.id, fmt(t("tts_no_credit", lang), { credits: balance.credits, required: cost }), { parse_mode: "HTML", reply_markup: creditMenu(lang) });
    const voice = state.ttsVoice || defaultVoice(lang);
    const voiceId = getVoices(lang)[voice] || getVoices(lang)[defaultVoice(lang)];
    const status = await this.sendMessage(msg.chat!.id, t("tts_processing", lang), { parse_mode: "HTML" });
    try {
      if (!this.deps.elevenLabsApiKey) throw new Error("ELEVENLABS_API_KEY is not configured");
      await this.deps.credits.consume(userId, cost, "tts", "telegram_bot");
      const audio = await this.synthesizeTts(text, voiceId);
      await this.deleteMessage(msg.chat!.id, status.result?.message_id);
      const method = state.ttsOutput === "voice" ? "sendVoice" : "sendDocument";
      const form = new FormData();
      form.append("chat_id", String(msg.chat!.id));
      form.append(state.ttsOutput === "voice" ? "voice" : "document", new Blob([audio], { type: "audio/mpeg" }), "Vexa.mp3");
      await fetch(`https://api.telegram.org/bot${this.deps.botToken}/${method}`, { method: "POST", body: form });
      await this.openTts(msg.chat!.id, undefined, userId, lang);
    } catch (error) {
      await this.deleteMessage(msg.chat!.id, status.result?.message_id);
      await this.deps.credits.grant(userId, cost, "tts_refund", "telegram_bot").catch(() => undefined);
      await this.sendMessage(msg.chat!.id, `${t("tts_error", lang)}\n${String((error as Error).message || error)}`, { parse_mode: "HTML" });
      await this.deps.userState.setBotState(userId, { ...state, mode: "tts:wait_text", updatedAt: nowTs() });
    }
  }

  private async openGpt(chatId: number, messageId: number | undefined, userId: number, lang: string) {
    if (!this.deps.openAiApiKey) return this.editOrSend(chatId, messageId, t("gpt_not_configured", lang), backMenu(lang));
    await this.deps.history.clear(userId);
    await this.deps.userState.setBotState(userId, { mode: "gpt:chat", updatedAt: nowTs() });
    return this.editOrSend(chatId, messageId, fmt(t("gpt_open", lang), { cost: GPT_MESSAGE_COST }), undefined, gptReplyMenu(lang));
  }

  private async handleGptText(chatId: number, userId: number, lang: string, text: string) {
    if (text === t("gpt_end_button", lang)) {
      await this.deps.history.clear(userId);
      await this.deps.userState.setBotState(userId, { mode: "idle", updatedAt: nowTs() });
      await this.sendMessage(chatId, t("gpt_end", lang), { parse_mode: "HTML", reply_markup: { remove_keyboard: true } });
      return this.showHome(chatId, userId, lang);
    }
    if (!this.deps.openAiApiKey) return this.sendMessage(chatId, t("gpt_not_configured", lang), { parse_mode: "HTML" });
    const balance = await this.deps.credits.getCredits(userId);
    if (balance.credits < GPT_MESSAGE_COST) return this.sendMessage(chatId, fmt(t("gpt_no_credit", lang), { balance: balance.credits, cost: GPT_MESSAGE_COST }), { parse_mode: "HTML", reply_markup: creditMenu(lang) });
    await this.deps.credits.consume(userId, GPT_MESSAGE_COST, "gpt", "telegram_bot");
    await this.deps.history.append(userId, "user", text);
    const thinking = await this.sendMessage(chatId, t("gpt_wait", lang), { parse_mode: "HTML" });
    try {
      const history = await this.deps.history.list(userId, GPT_HISTORY_LIMIT);
      const messages = [
        { role: "system", content: "You are Vexa, a helpful concise assistant. Reply in the user's language." },
        ...history.map((m) => ({ role: m.role, content: m.content })),
      ];
      const answer = await this.chatCompletion(messages);
      await this.deps.history.append(userId, "assistant", answer);
      return this.editMessageText(chatId, thinking.result?.message_id, answer, undefined, "HTML");
    } catch (error) {
      await this.deps.credits.grant(userId, GPT_MESSAGE_COST, "gpt_refund", "telegram_bot").catch(() => undefined);
      return this.editMessageText(chatId, thinking.result?.message_id, fmt(t("gpt_error", lang), { error: String((error as Error).message || error) }), undefined, "HTML");
    }
  }

  private async synthesizeTts(text: string, voiceId: string) {
    const res = await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, {
      method: "POST",
      headers: { "xi-api-key": this.deps.elevenLabsApiKey || "", "content-type": "application/json", accept: "audio/mpeg" },
      body: JSON.stringify({ text, model_id: "eleven_multilingual_v2", voice_settings: { stability: 0.45, similarity_boost: 0.8 } }),
    });
    if (!res.ok) throw new Error(`ElevenLabs ${res.status}`);
    return res.arrayBuffer();
  }

  private async chatCompletion(messages: Array<{ role: string; content: string }>) {
    const res = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: { authorization: `Bearer ${this.deps.openAiApiKey}`, "content-type": "application/json" },
      body: JSON.stringify({ model: "gpt-4o-mini", messages, temperature: 0.7 }),
    });
    if (!res.ok) throw new Error(`OpenAI ${res.status}`);
    const data = (await res.json()) as { choices?: Array<{ message?: { content?: string } }> };
    return data.choices?.[0]?.message?.content?.trim() || "";
  }

  private async sendInvoice(chatId: number, title: string, description: string, payload: string, stars: number, credits: number, lang: string) {
    return this.callTelegram("sendInvoice", { chat_id: chatId, title, description, payload, provider_token: "", currency: "XTR", prices: [{ label: fmt(t("credit_invoice_label", lang), { credits }), amount: stars }] });
  }
  private async answerPreCheckoutQuery(id: string, ok: boolean) { return this.callTelegram("answerPreCheckoutQuery", { pre_checkout_query_id: id, ok }); }
  private async answerCallbackQuery(id: string, text?: string, showAlert = false) { return this.callTelegram("answerCallbackQuery", { callback_query_id: id, text, show_alert: showAlert }); }
  private async sendMessage(chatId: number | string, text: string, opts: { parse_mode?: ParseMode; reply_markup?: unknown } = {}) { return this.callTelegram("sendMessage", { chat_id: chatId, text, ...opts }); }
  private async editMessageText(chatId: number, messageId: number | undefined, text: string, replyMarkup?: unknown, parseMode: ParseMode = "HTML") {
    if (!messageId) return this.sendMessage(chatId, text, { parse_mode: parseMode, reply_markup: replyMarkup });
    return this.callTelegram("editMessageText", { chat_id: chatId, message_id: messageId, text, parse_mode: parseMode, reply_markup: replyMarkup });
  }
  private async editOrSend(chatId: number, messageId: number | undefined, text: string, inlineMarkup?: InlineKeyboard, replyMarkup?: ReplyKeyboard) {
    const reply_markup = inlineMarkup || replyMarkup;
    if (messageId && inlineMarkup) {
      const edited = await this.editMessageText(chatId, messageId, text, reply_markup, "HTML");
      if (edited.ok) return edited;
    }
    return this.sendMessage(chatId, text, { parse_mode: "HTML", reply_markup });
  }
  private async deleteMessage(chatId: number, messageId?: number) { if (messageId) await this.callTelegram("deleteMessage", { chat_id: chatId, message_id: messageId }).catch(() => undefined); }
  private async callTelegram(method: string, body: Record<string, unknown>) {
    const res = await fetch(`https://api.telegram.org/bot${this.deps.botToken}/${method}`, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
    return (await res.json().catch(() => ({ ok: false }))) as { ok?: boolean; result?: { message_id?: number } };
  }
}
