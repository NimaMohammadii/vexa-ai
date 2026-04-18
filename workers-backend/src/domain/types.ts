export type ClientType = "telegram_bot" | "telegram_mini_app" | "website";

export interface UserProfile {
  userId: number;
  username: string | null;
  firstName: string | null;
  lang: string;
  banned: boolean;
  credits: number;
  joinedAt: number;
  lastSeenAt: number;
}

export interface AssetSummary {
  id: number;
  userId: number;
  assetType: "image" | "video" | "audio" | "other";
  sourcePrompt: string | null;
  storageUrl: string | null;
  status: "pending" | "ready" | "failed";
  createdAt: number;
}

export interface GptMessage {
  id?: number;
  role: "user" | "assistant" | "system";
  content: string;
  createdAt: number;
}

export interface FeatureFlag {
  key: string;
  enabled: boolean;
  description: string;
}

export interface SessionRecord {
  sessionToken: string;
  userId: number;
  clientType: ClientType;
  createdAt: number;
  expiresAt: number;
}

export interface TelegramMiniAppIdentity {
  telegramUserId: number;
  username?: string | null;
  firstName?: string | null;
  authDate: number;
}
