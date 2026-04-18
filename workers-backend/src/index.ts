import { validateTelegramInitData } from "./auth/telegram";
import { ApiTokenService, AssetService, GptHistoryService, UserService } from "./services/user-services";
import { D1ApiTokenRepository, D1AssetRepository, D1GptHistoryRepository, D1UserRepository } from "./storage/d1-repositories";
import { UserStateDO } from "./storage/user-state-do";
import { handleTelegramWebhook } from "./telegram/webhook";

export { UserStateDO };

interface Env {
  DB: D1Database;
  USER_STATE: DurableObjectNamespace;
  TELEGRAM_BOT_TOKEN: string;
  TELEGRAM_WEBHOOK_SECRET: string;
}

const json = (data: unknown, status = 200) => new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json" } });

function bearerToken(req: Request): string | null {
  const raw = req.headers.get("authorization") ?? "";
  const [scheme, token] = raw.split(" ");
  if (scheme?.toLowerCase() !== "bearer" || !token) return null;
  return token.trim();
}

async function resolveAuthedUserId(req: Request, tokens: D1ApiTokenRepository): Promise<number | null> {
  const token = bearerToken(req) ?? req.headers.get("x-api-key");
  if (!token) return null;
  return tokens.getUserIdByToken(token);
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    const users = new D1UserRepository(env.DB);
    const tokens = new D1ApiTokenRepository(env.DB);
    const history = new D1GptHistoryRepository(env.DB);
    const assets = new D1AssetRepository(env.DB);

    const userService = new UserService(users);
    const tokenService = new ApiTokenService(tokens);
    const historyService = new GptHistoryService(history);
    const assetService = new AssetService(assets);

    // Telegram bot webhook transport
    if (request.method === "POST" && url.pathname === `/telegram/webhook/${env.TELEGRAM_WEBHOOK_SECRET}`) {
      const update = await request.json();
      const result = await handleTelegramWebhook(update, { botToken: env.TELEGRAM_BOT_TOKEN, users });
      return json(result);
    }

    // Telegram Mini App auth bootstrap
    if (request.method === "POST" && url.pathname === "/miniapp/auth/telegram") {
      const body = (await request.json()) as { initData?: string };
      const initData = body.initData ?? "";
      const valid = await validateTelegramInitData(initData, env.TELEGRAM_BOT_TOKEN);
      if (!valid) return json({ error: "invalid_init_data" }, 401);
      return json({ ok: true });
    }

    const authedUserId = await resolveAuthedUserId(request, tokens);

    // Shared user profile for Mini App + Website
    if (request.method === "GET" && url.pathname === "/v1/me") {
      if (!authedUserId) return json({ error: "unauthorized" }, 401);
      const profile = await userService.getProfile(authedUserId);
      if (!profile) return json({ error: "not_found" }, 404);
      return json(profile);
    }

    if (request.method === "POST" && url.pathname === "/v1/me/api-token/rotate") {
      if (!authedUserId) return json({ error: "unauthorized" }, 401);
      return json({ token: await tokenService.rotate(authedUserId) });
    }

    if (request.method === "GET" && url.pathname === "/v1/me/gpt-history") {
      if (!authedUserId) return json({ error: "unauthorized" }, 401);
      return json({ messages: await historyService.list(authedUserId, 50) });
    }

    if (request.method === "DELETE" && url.pathname === "/v1/me/gpt-history") {
      if (!authedUserId) return json({ error: "unauthorized" }, 401);
      await historyService.clear(authedUserId);
      return json({ ok: true });
    }

    if (request.method === "GET" && url.pathname === "/v1/me/assets") {
      if (!authedUserId) return json({ error: "unauthorized" }, 401);
      return json({ items: await assetService.listUserAssets(authedUserId, 50) });
    }

    // Feature entrypoint discovery for Mini App/Website clients
    if (request.method === "GET" && url.pathname === "/v1/features") {
      return json({
        gpt: { enabled: true, entrypoint: "/v1/gpt/chat" },
        image: { enabled: true, entrypoint: "/v1/image" },
        tts: { enabled: true, entrypoint: "/v1/tts" },
        video: { enabled: true, entrypoint: "/v1/video" },
      });
    }

    return new Response("Not Found", { status: 404 });
  },
};
