import type { ApiTokenService, AssetService, CreditService, FeatureService, GptHistoryService, SessionService, UserService } from "../services/user-services";

export interface Env {
  DB: D1Database;
  USER_STATE: DurableObjectNamespace;
  TELEGRAM_BOT_TOKEN: string;
  TELEGRAM_WEBHOOK_SECRET: string;
  SESSION_TTL_SECONDS?: string;
}

export interface Services {
  users: UserService;
  credits: CreditService;
  tokens: ApiTokenService;
  sessions: SessionService;
  history: GptHistoryService;
  assets: AssetService;
  features: FeatureService;
}

export interface RouteCtx {
  env: Env;
  request: Request;
  url: URL;
  services: Services;
}
