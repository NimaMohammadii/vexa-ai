import type { ClientType, GptMessage } from "../domain/types";
import { HttpError } from "../http/response";
import type {
  ApiTokenRepository,
  AssetRepository,
  CreditLedgerRepository,
  FeatureRepository,
  GptHistoryRepository,
  OwnerNotificationRepository,
  SessionRepository,
  TelegramWebhookEventRepository,
  UserRepository,
} from "../storage/contracts";

export class UserService {
  constructor(private users: UserRepository) {}

  async getProfile(userId: number) {
    const profile = await this.users.getById(userId);
    if (!profile) throw new HttpError(404, "not_found", "User profile not found");
    return profile;
  }

  async bootstrapTelegramUser(input: { userId: number; username?: string | null; firstName?: string | null }) {
    return this.users.upsertTelegramUser(input);
  }

  touchLastSeen(userId: number) {
    return this.users.touchLastSeen(userId);
  }

  setLanguage(userId: number, lang: string) {
    return this.users.setLanguage(userId, lang);
  }

  async ensureActiveUser(userId: number) {
    const profile = await this.getProfile(userId);
    if (profile.banned) throw new HttpError(403, "forbidden", "User is banned");
    return profile;
  }
}

export class CreditService {
  constructor(private users: UserRepository, private ledger: CreditLedgerRepository) {}

  async getCredits(userId: number) {
    const profile = await this.users.getById(userId);
    if (!profile) throw new HttpError(404, "not_found", "User not found");
    return { credits: profile.credits };
  }

  async consume(userId: number, amount: number, reason: string, source: ClientType) {
    if (amount <= 0) throw new HttpError(400, "invalid_amount", "amount must be > 0");
    const existing = await this.users.getById(userId);
    if (!existing) throw new HttpError(404, "not_found", "User not found");
    if (existing.credits < amount) throw new HttpError(402, "insufficient_credits", "Insufficient credits");

    await this.users.incrementCredits(userId, -amount);
    await this.ledger.append({ userId, amount: -amount, reason, source });
  }

  async grant(userId: number, amount: number, reason: string, source: ClientType) {
    if (amount <= 0) throw new HttpError(400, "invalid_amount", "amount must be > 0");
    await this.users.incrementCredits(userId, amount);
    await this.ledger.append({ userId, amount, reason, source });
  }

  listLedger(userId: number, limit = 20) {
    return this.ledger.listByUser(userId, limit);
  }
}

export class ApiTokenService {
  constructor(private tokens: ApiTokenRepository) {}

  async getOrCreate(userId: number) {
    const existing = await this.tokens.getByUserId(userId);
    if (existing) return existing;
    return this.tokens.rotate(userId);
  }

  rotate(userId: number) {
    return this.tokens.rotate(userId);
  }

  async resolveTokenToUser(token: string) {
    return this.tokens.getUserIdByToken(token);
  }
}

export class SessionService {
  constructor(private sessions: SessionRepository) {}

  createSession(userId: number, clientType: ClientType, ttlSeconds: number) {
    return this.sessions.create({ userId, clientType, ttlSeconds });
  }

  getByToken(token: string) {
    return this.sessions.getByToken(token);
  }

  revoke(token: string) {
    return this.sessions.revoke(token);
  }
}

export class GptHistoryService {
  constructor(private history: GptHistoryRepository) {}
  list(userId: number, limit = 20) {
    return this.history.list(userId, limit);
  }
  clear(userId: number) {
    return this.history.clear(userId);
  }
  append(userId: number, role: GptMessage["role"], content: string) {
    return this.history.append(userId, role, content);
  }
}

export class AssetService {
  constructor(private assets: AssetRepository) {}
  listUserAssets(userId: number, limit = 20) {
    return this.assets.listByUser(userId, limit);
  }
}

export class FeatureService {
  constructor(private features: FeatureRepository) {}

  list() {
    return this.features.list();
  }
}

export class TelegramWebhookService {
  constructor(private events: TelegramWebhookEventRepository) {}

  async shouldSkipUpdate(updateId?: number | null): Promise<boolean> {
    if (updateId === undefined || updateId === null) return false;
    return this.events.isProcessed(updateId);
  }

  async markProcessed(updateId: number, telegramUserId: number | null, eventType: string) {
    await this.events.markProcessed({ updateId, telegramUserId, eventType });
  }
}

export class OwnerNotificationService {
  constructor(private notifications: OwnerNotificationRepository, private botToken: string, private ownerChatId?: string) {}

  async queue(input: { userId?: number | null; source: ClientType | "system"; category: string; message: string }) {
    if (!this.ownerChatId) {
      return this.notifications.create({ ...input, status: "queued" });
    }

    try {
      const text = [`🔔 ${input.category}`, input.message, input.userId ? `user_id: ${input.userId}` : undefined]
        .filter(Boolean)
        .join("\n");
      await fetch(`https://api.telegram.org/bot${this.botToken}/sendMessage`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ chat_id: this.ownerChatId, text }),
      });
      return this.notifications.create({ ...input, status: "sent", deliveredAt: Math.floor(Date.now() / 1000) });
    } catch {
      return this.notifications.create({ ...input, status: "failed" });
    }
  }
}
