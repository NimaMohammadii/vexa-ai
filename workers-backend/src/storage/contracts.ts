import type { AssetSummary, ClientType, CreditLedgerEntry, FeatureFlag, GptMessage, SessionRecord, UserProfile } from "../domain/types";

export interface UserRepository {
  upsertTelegramUser(input: { userId: number; username?: string | null; firstName?: string | null }): Promise<UserProfile>;
  getById(userId: number): Promise<UserProfile | null>;
  touchLastSeen(userId: number): Promise<void>;
  incrementCredits(userId: number, delta: number): Promise<void>;
}

export interface ApiTokenRepository {
  getByUserId(userId: number): Promise<string | null>;
  rotate(userId: number): Promise<string>;
  getUserIdByToken(token: string): Promise<number | null>;
}

export interface SessionRepository {
  create(input: { userId: number; clientType: ClientType; ttlSeconds: number }): Promise<SessionRecord>;
  getByToken(token: string): Promise<SessionRecord | null>;
  revoke(token: string): Promise<void>;
}

export interface GptHistoryRepository {
  list(userId: number, limit: number): Promise<GptMessage[]>;
  append(userId: number, role: GptMessage["role"], content: string): Promise<void>;
  clear(userId: number): Promise<void>;
}

export interface AssetRepository {
  listByUser(userId: number, limit: number): Promise<AssetSummary[]>;
}

export interface FeatureRepository {
  list(): Promise<FeatureFlag[]>;
}

export interface CreditLedgerRepository {
  append(input: { userId: number; amount: number; reason: string; source: ClientType }): Promise<void>;
  listByUser(userId: number, limit: number): Promise<CreditLedgerEntry[]>;
}
