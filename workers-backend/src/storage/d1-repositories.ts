import type { AssetSummary, ClientType, CreditLedgerEntry, FeatureFlag, GptMessage, SessionRecord, UserProfile } from "../domain/types";
import type { ApiTokenRepository, AssetRepository, CreditLedgerRepository, FeatureRepository, GptHistoryRepository, SessionRepository, UserRepository } from "./contracts";

const now = () => Math.floor(Date.now() / 1000);

export class D1UserRepository implements UserRepository {
  constructor(private db: D1Database) {}

  async upsertTelegramUser(input: { userId: number; username?: string | null; firstName?: string | null }): Promise<UserProfile> {
    const ts = now();
    await this.db
      .prepare(
        `INSERT INTO users (user_id, username, first_name, lang, banned, credits, joined_at, last_seen_at)
         VALUES (?1, ?2, ?3, 'fa', 0, 10, ?4, ?4)
         ON CONFLICT(user_id) DO UPDATE SET
           username = COALESCE(excluded.username, users.username),
           first_name = COALESCE(excluded.first_name, users.first_name),
           last_seen_at = excluded.last_seen_at`
      )
      .bind(input.userId, input.username ?? null, input.firstName ?? null, ts)
      .run();

    const profile = await this.getById(input.userId);
    if (!profile) throw new Error("failed_to_upsert_user");
    return profile;
  }

  async getById(userId: number): Promise<UserProfile | null> {
    const row = await this.db
      .prepare(`SELECT user_id, username, first_name, lang, banned, credits, joined_at, last_seen_at FROM users WHERE user_id = ?1`)
      .bind(userId)
      .first<any>();

    if (!row) return null;
    return {
      userId: row.user_id,
      username: row.username,
      firstName: row.first_name,
      lang: row.lang ?? "fa",
      banned: !!row.banned,
      credits: Number(row.credits ?? 0),
      joinedAt: Number(row.joined_at),
      lastSeenAt: Number(row.last_seen_at),
    };
  }

  async touchLastSeen(userId: number): Promise<void> {
    await this.db.prepare(`UPDATE users SET last_seen_at = ?1 WHERE user_id = ?2`).bind(now(), userId).run();
  }

  async incrementCredits(userId: number, delta: number): Promise<void> {
    await this.db.prepare(`UPDATE users SET credits = credits + ?1 WHERE user_id = ?2`).bind(delta, userId).run();
  }
}

export class D1ApiTokenRepository implements ApiTokenRepository {
  constructor(private db: D1Database) {}

  async getByUserId(userId: number): Promise<string | null> {
    const row = await this.db.prepare(`SELECT token FROM api_tokens WHERE user_id = ?1`).bind(userId).first<any>();
    return row?.token ?? null;
  }

  async rotate(userId: number): Promise<string> {
    const token = crypto.randomUUID().replace(/-/g, "") + crypto.randomUUID().replace(/-/g, "");
    const ts = now();
    await this.db
      .prepare(
        `INSERT INTO api_tokens (user_id, token, created_at, rotated_at)
         VALUES (?1, ?2, ?3, NULL)
         ON CONFLICT(user_id) DO UPDATE SET token = excluded.token, rotated_at = ?4`
      )
      .bind(userId, token, ts, ts)
      .run();
    return token;
  }

  async getUserIdByToken(token: string): Promise<number | null> {
    const row = await this.db.prepare(`SELECT user_id FROM api_tokens WHERE token = ?1`).bind(token).first<any>();
    return row ? Number(row.user_id) : null;
  }
}

export class D1SessionRepository implements SessionRepository {
  constructor(private db: D1Database) {}

  async create(input: { userId: number; clientType: ClientType; ttlSeconds: number }): Promise<SessionRecord> {
    const sessionToken = crypto.randomUUID().replace(/-/g, "") + crypto.randomUUID().replace(/-/g, "");
    const createdAt = now();
    const expiresAt = createdAt + input.ttlSeconds;
    await this.db
      .prepare(`INSERT INTO user_sessions(session_token, user_id, client_type, created_at, expires_at) VALUES(?1, ?2, ?3, ?4, ?5)`)
      .bind(sessionToken, input.userId, input.clientType, createdAt, expiresAt)
      .run();
    return { sessionToken, userId: input.userId, clientType: input.clientType, createdAt, expiresAt };
  }

  async getByToken(token: string): Promise<SessionRecord | null> {
    const row = await this.db
      .prepare(`SELECT session_token, user_id, client_type, created_at, expires_at FROM user_sessions WHERE session_token = ?1 LIMIT 1`)
      .bind(token)
      .first<any>();

    if (!row) return null;
    if (Number(row.expires_at) <= now()) {
      await this.revoke(token);
      return null;
    }

    return {
      sessionToken: row.session_token,
      userId: Number(row.user_id),
      clientType: row.client_type,
      createdAt: Number(row.created_at),
      expiresAt: Number(row.expires_at),
    };
  }

  async revoke(token: string): Promise<void> {
    await this.db.prepare(`DELETE FROM user_sessions WHERE session_token = ?1`).bind(token).run();
  }
}

export class D1GptHistoryRepository implements GptHistoryRepository {
  constructor(private db: D1Database) {}

  async list(userId: number, limit: number): Promise<GptMessage[]> {
    const { results } = await this.db
      .prepare(
        `SELECT id, role, content, created_at
           FROM gpt_messages
          WHERE user_id = ?1
          ORDER BY created_at DESC
          LIMIT ?2`
      )
      .bind(userId, limit)
      .all<any>();

    return (results ?? []).reverse().map((row) => ({ id: Number(row.id), role: row.role, content: row.content, createdAt: Number(row.created_at) }));
  }

  async append(userId: number, role: GptMessage["role"], content: string): Promise<void> {
    await this.db
      .prepare(`INSERT INTO gpt_messages (user_id, role, content, created_at) VALUES (?1, ?2, ?3, ?4)`)
      .bind(userId, role, content, now())
      .run();
  }

  async clear(userId: number): Promise<void> {
    await this.db.prepare(`DELETE FROM gpt_messages WHERE user_id = ?1`).bind(userId).run();
  }
}

export class D1AssetRepository implements AssetRepository {
  constructor(private db: D1Database) {}

  async listByUser(userId: number, limit: number): Promise<AssetSummary[]> {
    const { results } = await this.db
      .prepare(
        `SELECT id, user_id, asset_type, source_prompt, storage_url, status, created_at
           FROM generated_assets
          WHERE user_id = ?1
          ORDER BY created_at DESC
          LIMIT ?2`
      )
      .bind(userId, limit)
      .all<any>();

    return (results ?? []).map((row) => ({
      id: Number(row.id),
      userId: Number(row.user_id),
      assetType: row.asset_type,
      sourcePrompt: row.source_prompt,
      storageUrl: row.storage_url,
      status: row.status,
      createdAt: Number(row.created_at),
    }));
  }
}

export class D1FeatureRepository implements FeatureRepository {
  constructor(private db: D1Database) {}

  async list(): Promise<FeatureFlag[]> {
    const { results } = await this.db.prepare(`SELECT feature_key, enabled, description FROM feature_flags ORDER BY feature_key`).all<any>();

    return (results ?? []).map((row) => ({
      key: row.feature_key,
      enabled: !!row.enabled,
      description: row.description ?? "",
    }));
  }
}

export class D1CreditLedgerRepository implements CreditLedgerRepository {
  constructor(private db: D1Database) {}

  async append(input: { userId: number; amount: number; reason: string; source: ClientType }): Promise<void> {
    await this.db
      .prepare(`INSERT INTO credit_ledger (user_id, amount, reason, source, created_at) VALUES (?1, ?2, ?3, ?4, ?5)`)
      .bind(input.userId, input.amount, input.reason, input.source, now())
      .run();
  }

  async listByUser(userId: number, limit: number): Promise<CreditLedgerEntry[]> {
    const { results } = await this.db
      .prepare(`SELECT id, amount, reason, source, created_at FROM credit_ledger WHERE user_id = ?1 ORDER BY created_at DESC LIMIT ?2`)
      .bind(userId, limit)
      .all<any>();

    return (results ?? []).map((row) => ({
      id: Number(row.id),
      amount: Number(row.amount),
      reason: row.reason,
      source: row.source,
      createdAt: Number(row.created_at),
    }));
  }
}
