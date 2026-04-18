import type { ClientType, GptMessage } from "../domain/types";
import { HttpError } from "../http/response";
import type { ApiTokenRepository, AssetRepository, CreditLedgerRepository, FeatureRepository, GptHistoryRepository, SessionRepository, UserRepository } from "../storage/contracts";

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
