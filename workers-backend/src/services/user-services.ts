import type { ApiTokenRepository, AssetRepository, GptHistoryRepository, UserRepository } from "../storage/contracts";

export class UserService {
  constructor(private users: UserRepository) {}

  getProfile(userId: number) {
    return this.users.getById(userId);
  }
}

export class CreditService {
  constructor(private users: UserRepository) {}

  async charge(userId: number, amount: number) {
    const profile = await this.users.getById(userId);
    if (!profile) throw new Error("user_not_found");
    if (profile.credits < amount) throw new Error("insufficient_credits");
    await this.users.setCredits(userId, Number((profile.credits - amount).toFixed(2)));
    return this.users.getById(userId);
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
