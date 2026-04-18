import type { ClientType } from "../domain/types";
import { HttpError } from "../http/response";
import type { ApiTokenRepository, AssetRepository, FeatureRepository, GptHistoryRepository, SessionRepository, UserRepository } from "../storage/contracts";

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
}

export class CreditService {
  constructor(private users: UserRepository) {}

  async getCredits(userId: number) {
    const profile = await this.users.getById(userId);
    if (!profile) throw new HttpError(404, "not_found", "User not found");
    return { credits: profile.credits };
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
