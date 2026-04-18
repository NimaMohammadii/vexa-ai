import { validateTelegramInitData } from "../auth/telegram";
import { jsonOk, parseJsonBody } from "../http/response";
import type { RouteCtx } from "./types";

export async function handlePublicRoutes(ctx: RouteCtx): Promise<Response | null> {
  const { request, url, services, env } = ctx;

  if (request.method === "GET" && url.pathname === "/v1/health") {
    return jsonOk({ status: "ok", runtime: "cloudflare-workers" });
  }

  if (request.method === "GET" && (url.pathname === "/v1/features" || url.pathname === "/v1/public/features")) {
    const flags = await services.features.list();
    return jsonOk({
      features: flags,
      routes: {
        telegramWebhook: "/telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>",
        miniAppAuth: "/miniapp/auth/telegram",
        me: "/v1/me",
        meCredits: "/v1/me/credits",
        meApiToken: "/v1/me/api-token",
        meApiTokenRotate: "/v1/me/api-token/rotate",
        meGptHistory: "/v1/me/gpt-history",
        meAssets: "/v1/me/assets",
      },
      clients: {
        telegramBot: { transport: "webhook", route: "/telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>" },
        telegramMiniApp: { authRoute: "/miniapp/auth/telegram", tokenType: "Bearer" },
        website: { authRoute: "/miniapp/auth/telegram", publicRoute: "/v1/public/features" },
      },
    });
  }

  if (request.method === "GET" && url.pathname === "/v1/telegram/webhook-info") {
    return jsonOk({
      webhookPath: `/telegram/webhook/${env.TELEGRAM_WEBHOOK_SECRET}`,
      setWebhookExample: `https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<WORKER_BASE_URL>/telegram/webhook/${env.TELEGRAM_WEBHOOK_SECRET}`,
      notes: [
        "Use the exact TELEGRAM_WEBHOOK_SECRET value from Worker env.",
        "Do not run polling in production.",
      ],
    });
  }

  if (request.method === "POST" && (url.pathname === "/miniapp/auth/telegram" || url.pathname === "/v1/auth/telegram-miniapp")) {
    const body = await parseJsonBody<{ initData?: string }>(request);
    const identity = await validateTelegramInitData(body.initData ?? "", env.TELEGRAM_BOT_TOKEN);

    await services.users.bootstrapTelegramUser({
      userId: identity.telegramUserId,
      username: identity.username,
      firstName: identity.firstName,
    });

    const ttlSeconds = Number(env.SESSION_TTL_SECONDS ?? "2592000");
    const session = await services.sessions.createSession(identity.telegramUserId, "telegram_mini_app", ttlSeconds);
    const profile = await services.users.getProfile(identity.telegramUserId);

    return jsonOk({
      accessToken: session.sessionToken,
      tokenType: "Bearer",
      expiresAt: session.expiresAt,
      profile,
      routes: {
        me: "/v1/me",
        meCredits: "/v1/me/credits",
      },
    });
  }

  return null;
}
