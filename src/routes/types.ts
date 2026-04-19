import type {
  ApiTokenService,
  AssetService,
  CreditService,
  FeatureService,
  GptHistoryService,
  OwnerNotificationService,
  SessionService,
  TelegramWebhookService,
  UserService,
} from "../services/user-services";

export interface Env {
  DB: D1Database;
  USER_STATE: DurableObjectNamespace;
  TELEGRAM_BOT_TOKEN: string;
  TELEGRAM_WEBHOOK_SECRET: string;
  OWNER_TELEGRAM_CHAT_ID?: string;
  SESSION_TTL_SECONDS?: string;
  TELEGRAM_BOT_USERNAME?: string;
  FORCE_SUB_MODE?: string;
  TG_CHANNEL?: string;
  IG_URL?: string;
  WELCOME_AUDIO_FILE_ID?: string;
  WELCOME_AUDIO_KIND?: "audio" | "voice" | "document";
}

export interface Services {
  users: UserService;
  credits: CreditService;
  tokens: ApiTokenService;
  sessions: SessionService;
  history: GptHistoryService;
  assets: AssetService;
  features: FeatureService;
  telegramEvents: TelegramWebhookService;
  ownerNotifications: OwnerNotificationService;
}

export interface RouteCtx {
  env: Env;
  request: Request;
  url: URL;
  services: Services;
}
