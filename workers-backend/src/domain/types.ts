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
  assetType: "image" | "video" | "audio";
  sourcePrompt: string | null;
  storageUrl: string | null;
  status: "pending" | "ready" | "failed";
  createdAt: number;
}

export interface GptMessage {
  role: "user" | "assistant" | "system";
  content: string;
  createdAt: number;
}
