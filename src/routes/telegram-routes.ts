import { HttpError, jsonOk, parseJsonBody } from "../http/response";
import { TelegramBotFlowService, type TelegramWebhookUpdate } from "../services/telegram-bot-service";
import { UserStateRepository } from "../storage/user-state-repository";
import type { RouteCtx } from "./types";

export async function handleTelegramRoutes(ctx: RouteCtx): Promise<Response | null> {
  const { request, url, env, services } = ctx;

  if (request.method === "POST" && url.pathname === `/telegram/webhook/${env.TELEGRAM_WEBHOOK_SECRET}`) {
    const update = await parseJsonBody<TelegramWebhookUpdate>(request);
    const flow = new TelegramBotFlowService({
      botToken: env.TELEGRAM_BOT_TOKEN,
      botUsername: env.TELEGRAM_BOT_USERNAME,
      forceSubMode: env.FORCE_SUB_MODE,
      forceSubChannel: env.TG_CHANNEL,
      forceSubInstagramUrl: env.IG_URL,
      welcomeAudioFileId: env.WELCOME_AUDIO_FILE_ID,
      welcomeAudioKind: env.WELCOME_AUDIO_KIND,
      ownerTelegramChatId: env.OWNER_TELEGRAM_CHAT_ID,
      cardNumber: env.CARD_NUMBER,
      users: services.users,
      credits: services.credits,
      tokens: services.tokens,
      history: services.history,
      userState: new UserStateRepository(env.USER_STATE),
      telegramEvents: services.telegramEvents,
      ownerNotifications: services.ownerNotifications,
    });
    const result = await flow.handleWebhook(update);
    return jsonOk(result);
  }

  if (request.method === "POST" && url.pathname.startsWith("/telegram/webhook/")) {
    throw new HttpError(403, "forbidden", "Invalid webhook secret");
  }

  return null;
}
