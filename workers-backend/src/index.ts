import { withCors, handleCorsPreflight } from "./http/cors";
import { jsonError, HttpError } from "./http/response";
import { AssetService, ApiTokenService, CreditService, FeatureService, GptHistoryService, SessionService, UserService } from "./services/user-services";
import { D1ApiTokenRepository, D1AssetRepository, D1FeatureRepository, D1GptHistoryRepository, D1SessionRepository, D1UserRepository } from "./storage/d1-repositories";
import { UserStateDO } from "./storage/user-state-do";
import { handleMeRoutes } from "./routes/me-routes";
import { handlePublicRoutes } from "./routes/public-routes";
import { handleTelegramRoutes } from "./routes/telegram-routes";
import type { Env } from "./routes/types";

export { UserStateDO };

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const preflight = handleCorsPreflight(request);
    if (preflight) return preflight;

    const url = new URL(request.url);

    const services = {
      users: new UserService(new D1UserRepository(env.DB)),
      credits: new CreditService(new D1UserRepository(env.DB)),
      tokens: new ApiTokenService(new D1ApiTokenRepository(env.DB)),
      sessions: new SessionService(new D1SessionRepository(env.DB)),
      history: new GptHistoryService(new D1GptHistoryRepository(env.DB)),
      assets: new AssetService(new D1AssetRepository(env.DB)),
      features: new FeatureService(new D1FeatureRepository(env.DB)),
    };

    try {
      const ctx = { env, request, url, services };

      const handlers = [handleTelegramRoutes, handlePublicRoutes, handleMeRoutes];
      for (const handler of handlers) {
        const response = await handler(ctx);
        if (response) return withCors(request, response);
      }

      throw new HttpError(404, "not_found", `Route not found: ${request.method} ${url.pathname}`);
    } catch (error) {
      return withCors(request, jsonError(error));
    }
  },
};
