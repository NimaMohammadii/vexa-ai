import { requireAuthedUserId } from "../http/auth";
import { jsonOk } from "../http/response";
import type { RouteCtx } from "./types";

export async function handleMeRoutes(ctx: RouteCtx): Promise<Response | null> {
  const { request, url, services } = ctx;

  if (!url.pathname.startsWith("/v1/me")) return null;

  const userId = await requireAuthedUserId(request, services);

  if (request.method === "GET" && url.pathname === "/v1/me") {
    return jsonOk(await services.users.getProfile(userId));
  }

  if (request.method === "GET" && url.pathname === "/v1/me/credits") {
    return jsonOk(await services.credits.getCredits(userId));
  }

  if (request.method === "GET" && url.pathname === "/v1/me/api-token") {
    const token = await services.tokens.getOrCreate(userId);
    return jsonOk({ token });
  }

  if (request.method === "POST" && url.pathname === "/v1/me/api-token/rotate") {
    const token = await services.tokens.rotate(userId);
    return jsonOk({ token });
  }

  if (request.method === "GET" && url.pathname === "/v1/me/gpt-history") {
    return jsonOk({ messages: await services.history.list(userId, 100) });
  }

  if (request.method === "DELETE" && url.pathname === "/v1/me/gpt-history") {
    await services.history.clear(userId);
    return jsonOk({ cleared: true });
  }

  if (request.method === "GET" && url.pathname === "/v1/me/assets") {
    return jsonOk({ items: await services.assets.listUserAssets(userId, 100) });
  }

  return null;
}
