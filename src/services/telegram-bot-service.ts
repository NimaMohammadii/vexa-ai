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
  message?: {
    message_id?: number;
    text?: string;
    caption?: string;
    photo?: Array<{ file_id: string }>;
    voice?: { file_id: string };
    audio?: { file_id: string };
    document?: { file_id: string; mime_type?: string };
    from?: TelegramUser;
    chat?: { id: number };
  };
  callback_query?: {
    id: string;
    data?: string;
    from?: TelegramUser;
    message?: { message_id?: number; chat?: { id: number } };
  };
}

interface TelegramBotFlowDeps {
  botToken: string;
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
  inline_keyboard: Array<Array<{ text: string; callback_data: string }>>;
};

type ReplyKeyboard = {
  keyboard: Array<Array<{ text: string }>>;
  resize_keyboard?: boolean;
  one_time_keyboard?: boolean;
};

const nowTs = () => Math.floor(Date.now() / 1000);
const DAILY_REWARD_SECONDS = 24 * 60 * 60;
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

const LABELS = {
  homeTitle: "منوی اصلی",
  homeBody: "یکی از گزینه‌های زیر را انتخاب کنید:",
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
};

export class TelegramBotFlowService {
  constructor(private deps: TelegramBotFlowDeps) {}

  async handleWebhook(update: TelegramWebhookUpdate): Promise<{ handled: string }> {
    if (await this.deps.telegramEvents.shouldSkipUpdate(update.update_id)) {
      return { handled: "duplicate_update" };
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

    if (text.startsWith("/")) {
      const handled = await this.handleCommand(user.userId, user.lang || "fa", msg.chat.id, text);
      await this.markProcessed(update, user.userId, handled.handled);
      return handled;
    }

    if (await this.handleMediaDrivenMessage(user.userId, msg.chat.id, msg, state)) {
      await this.markProcessed(update, user.userId, `${state.mode}:media`);
      return { handled: `${state.mode}:media` };
    }

    if (await this.handleStateDrivenMessage(user.userId, user.lang || "fa", msg.chat.id, text, state)) {
      await this.markProcessed(update, user.userId, state.mode);
      return { handled: state.mode };
    }

    if (await this.handleTextNavigation(user.userId, user.lang || "fa", msg.chat.id, text)) {
      await this.markProcessed(update, user.userId, "text_navigation");
      return { handled: "text_navigation" };
    }

    await this.sendMainMenu(msg.chat.id);
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

    if (data === "home:back") {
      await this.sendMainMenu(chatId, messageId);
      await this.answerCallback(callback.id);
      return { handled: "home_back" };
    }
    if (data === "home:profile") {
      const credits = (await this.deps.credits.getCredits(user.userId)).credits;
      await this.answerCallback(callback.id, `نمای کلی حساب\n\n💳 موجودی شما: ${credits} کردیت`, true);
      return { handled: "profile" };
    }
    if (data === "home:credit" || data === "credit:menu") {
      await this.sendCreditMenu(chatId, messageId);
      await this.answerCallback(callback.id);
      return { handled: "credit_menu" };
    }
    if (data === "credit:stars") {
      await this.sendMessage(chatId, "🌟 شارژ با Telegram Stars\n\nبرای شارژ فوری، لطفاً از پشتیبانی داخل بات راهنمای پرداخت Stars را بگیر.", "HTML", {
        inline_keyboard: [[{ text: LABELS.back, callback_data: "credit:menu" }]],
      });
      await this.answerCallback(callback.id);
      return { handled: "credit_stars" };
    }
    if (data === "credit:payrial") {
      await this.sendMessage(
        chatId,
        "💱 <b>پرداخت ریالی</b>\n\nبرای پرداخت کارت‌به‌کارت، رسیدت را برای ادمین ارسال می‌کنیم تا حداکثر ظرف چند دقیقه تایید شود.",
        "HTML",
        {
          inline_keyboard: [
            [{ text: "ارسال رسید برای تایید", callback_data: "credit:payrial:instant" }],
            [{ text: LABELS.back, callback_data: "credit:menu" }],
          ],
        }
      );
      await this.answerCallback(callback.id);
      return { handled: "credit_payrial" };
    }
    if (data === "credit:payrial:instant") {
      await this.deps.userState.setBotState(user.userId, { mode: "idle", updatedAt: nowTs() });
      await this.sendMessage(
        chatId,
        "🧾 عکس رسید پرداخت را ارسال کن.\n\nبعد از ارسال، درخواستت برای تایید دستی پشتیبانی ثبت می‌شود.",
        "HTML",
        {
          inline_keyboard: [[{ text: LABELS.back, callback_data: "credit:menu" }]],
        }
      );
      await this.answerCallback(callback.id);
      return { handled: "credit_payrial_instant" };
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
      await this.answerCallback(callback.id, "✅ زبان ذخیره شد.");
      await this.sendMainMenu(chatId, messageId);
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
      await this.deps.userState.setBotState(user.userId, { mode: "tts:wait_text", updatedAt: nowTs(), ttsVoice: "alloy", ttsOutput: "mp3" });
      await this.sendMessage(chatId, "🎧 <b>تبدیل متن به صدا</b>\n\nمتن را بفرست. می‌تونی صدا و خروجی را از منوی زیر عوض کنی.", "HTML", this.ttsKeyboard("alloy", "mp3"));
      await this.answerCallback(callback.id);
      return { handled: "tts_open" };
    }
    if (data.startsWith("tts:demo:")) {
      const voice = data.split(":")[2] || "alloy";
      await this.answerCallback(callback.id, `دموی صدا: ${voice}`);
      await this.sendMessage(chatId, `🎙 دمو برای صدای <b>${voice}</b>\n\nیک متن بفرست تا با همین صدا پردازش شود.`, "HTML", this.ttsKeyboard(voice));
      return { handled: "tts_demo" };
    }
    if (data.startsWith("tts:output:")) {
      const state = await this.deps.userState.getBotState(user.userId);
      const output = data.endsWith(":voice") ? "voice" : "mp3";
      const voice = state.ttsVoice || "alloy";
      await this.deps.userState.setBotState(user.userId, { ...state, mode: "tts:wait_text", updatedAt: nowTs(), ttsOutput: output });
      await this.sendMessage(chatId, `✅ خروجی روی <b>${output.toUpperCase()}</b> تنظیم شد.`, "HTML", this.ttsKeyboard(voice, output));
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
      await this.sendMainMenu(chatId, messageId);
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
      await this.sendMainMenu(chatId, messageId);
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

  private async handleCommand(userId: number, lang: string, chatId: number, text: string): Promise<{ handled: string }> {
    if (text.startsWith("/start")) {
      await this.handleStart(userId, lang, chatId, text);
      return { handled: "start" };
    }

    switch (text) {
      case "/help":
      case "/menu":
        await this.sendMainMenu(chatId);
        return { handled: "menu" };
      case "/profile": {
        const credits = await this.deps.credits.getCredits(userId);
        await this.sendMessage(chatId, `نمای کلی حساب\n\n💳 موجودی شما: ${credits.credits} کردیت`);
        return { handled: "profile" };
      }
      case "/credits":
        await this.sendCreditMenu(chatId);
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
        await this.sendMainMenu(chatId);
        return { handled: "cancel" };
      default:
        await this.sendMainMenu(chatId);
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
        await this.sendMainMenu(chatId);
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
      await this.sendMessage(chatId, `✅ متن صوتی ثبت شد.\n\n🎙 صدا: <b>${state.ttsVoice || "alloy"}</b>\n📦 خروجی: <b>${(state.ttsOutput || "mp3").toUpperCase()}</b>`, "HTML", this.ttsKeyboard(state.ttsVoice || "alloy", state.ttsOutput || "mp3"));
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
      await this.sendMainMenu(chatId);
      return true;
    }

    return false;
  }

  private async handleTextNavigation(userId: number, lang: string, chatId: number, text: string): Promise<boolean> {
    switch (text) {
      case LABELS.profile:
        await this.handleCommand(userId, lang, chatId, "/profile");
        return true;
      case LABELS.credit:
        await this.sendCreditMenu(chatId);
        return true;
      case LABELS.tts:
        await this.deps.userState.setBotState(userId, { mode: "tts:wait_text", updatedAt: nowTs(), ttsVoice: "alloy", ttsOutput: "mp3" });
        await this.sendMessage(chatId, "🎧 <b>تبدیل متن به صدا</b>\n\nمتن را بفرست. می‌تونی صدا و خروجی را از منوی زیر عوض کنی.", "HTML", this.ttsKeyboard("alloy", "mp3"));
        return true;
      case LABELS.gpt:
        await this.handleCommand(userId, lang, chatId, "/ask");
        return true;
      case LABELS.lang:
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

  private mainMenuKeyboard(): InlineKeyboard {
    return {
      inline_keyboard: [
        [
          { text: LABELS.profile, callback_data: "home:profile" },
          { text: LABELS.credit, callback_data: "home:credit" },
        ],
        [{ text: LABELS.tts, callback_data: "home:tts" }],
        [{ text: LABELS.gpt, callback_data: "home:gpt_chat" }],
        [
          { text: LABELS.lang, callback_data: "home:lang" },
          { text: LABELS.invite, callback_data: "home:invite" },
        ],
        [
          { text: LABELS.apiToken, callback_data: "home:api_token" },
          { text: LABELS.image, callback_data: "home:image" },
        ],
        [{ text: LABELS.video, callback_data: "home:video" }],
      ],
    };
  }

  private async sendMainMenu(chatId: number, messageId?: number) {
    const text = `🏠 <b>${LABELS.homeTitle}</b>\n\n${LABELS.homeBody}`;
    await this.sendOrEditMessage(chatId, text, this.mainMenuKeyboard(), messageId, "HTML");
  }

  private async sendCreditMenu(chatId: number, messageId?: number) {
    const text = "🛒 <b>خرید کردیت</b>\n\nبرای استفاده از ربات، کردیت لازم دارید";
    const replyMarkup: InlineKeyboard = {
      inline_keyboard: [
        [{ text: "خرید با Telegram Stars 🌟", callback_data: "credit:stars" }],
        [{ text: "پرداخت به تومان", callback_data: "credit:payrial" }],
        [{ text: LABELS.back, callback_data: "home:back" }],
      ],
    };
    await this.sendOrEditMessage(chatId, text, replyMarkup, messageId, "HTML");
  }

  private async sendLanguageMenu(chatId: number, currentLang: string, messageId?: number) {
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

    const text = "🌐 <b>انتخاب زبان</b>\n\nیکی از زبان‌های زیر را انتخاب کن.";
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

  private ttsKeyboard(selectedVoice = "alloy", selectedOutput: "mp3" | "voice" = "mp3"): InlineKeyboard {
    return {
      inline_keyboard: [
        [{ text: `▶︎ دمو (${selectedVoice})`, callback_data: `tts:demo:${selectedVoice}` }],
        [
          { text: `${selectedOutput === "mp3" ? "✔️ " : ""}MP3 📁`, callback_data: "tts:output:mp3" },
          { text: `${selectedOutput === "voice" ? "✔️ " : ""}Voice 🎙️`, callback_data: "tts:output:voice" },
        ],
        [{ text: "ساخت صدای شخصی 🧬", callback_data: "home:clone" }],
        [{ text: LABELS.back, callback_data: "home:back" }],
      ],
    };
  }

  private async handleStart(userId: number, lang: string, chatId: number, text: string) {
    const parts = text.split(/\s+/, 2);
    const startParam = parts.length > 1 ? parts[1] : "";
    if (startParam && /^\d+$/.test(startParam) && Number(startParam) !== userId) {
      await this.deps.ownerNotifications.queue({
        userId,
        source: "telegram_bot",
        category: "start_referral",
        message: `start_param_ref=${startParam}`,
      });
      await this.sendMessage(chatId, "🎉 از لینک دعوت وارد شدی. کد ارجاع ثبت شد.");
    }

    const profile = await this.deps.users.getProfile(userId);
    const isFirstOpen = Math.abs(profile.lastSeenAt - profile.joinedAt) <= 3;
    if (isFirstOpen) {
      await this.sendMessage(
        chatId,
        "👋 خوش اومدی به Vexa AI!\n\n🎁 اعتبار اولیه حسابت فعال شده.\nاز منوی اصلی سرویس مورد نظرت رو انتخاب کن.",
        "HTML",
        {
          inline_keyboard: [[{ text: "🎁 پاداش روزانه", callback_data: "onboarding:daily_reward" }, { text: "دعوت دوستان", callback_data: "onboarding:invite" }]],
        }
      );
    }
    await this.sendMainMenu(chatId);
  }

  private async handleMediaDrivenMessage(userId: number, chatId: number, msg: NonNullable<TelegramWebhookUpdate["message"]>, state: BotConversationState): Promise<boolean> {
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
    await this.sendMessage(
      chatId,
      `🎁 <b>دعوت دوستان</b>\n\nلینک دعوت اختصاصی تو:\n<code>https://t.me/VexaAiBot?start=${userId}</code>\n\nبا هر دعوت موفق، پاداش اضافه می‌گیری.`,
      "HTML",
      {
        inline_keyboard: [
          [{ text: "🎁 دریافت جایزه روزانه", callback_data: "invite:daily_reward" }],
          [{ text: LABELS.back, callback_data: "home:back" }],
        ],
      }
    );
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
