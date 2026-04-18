import { HttpError } from "../http/response";
import type { TelegramMiniAppIdentity } from "../domain/types";

const enc = new TextEncoder();
const MAX_AUTH_AGE_SECONDS = 24 * 60 * 60;

async function hmacSha256Raw(key: ArrayBuffer | Uint8Array, data: string): Promise<ArrayBuffer> {
  const cryptoKey = await crypto.subtle.importKey("raw", key, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return crypto.subtle.sign("HMAC", cryptoKey, enc.encode(data));
}

function hex(bytes: ArrayBuffer): string {
  return [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let out = 0;
  for (let i = 0; i < a.length; i++) out |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return out === 0;
}

export async function validateTelegramInitData(initData: string, botToken: string): Promise<TelegramMiniAppIdentity> {
  const params = new URLSearchParams(initData);
  const hash = params.get("hash");
  if (!hash) throw new HttpError(401, "invalid_init_data", "Missing Telegram hash");

  const authDate = Number(params.get("auth_date") || "0");
  const now = Math.floor(Date.now() / 1000);
  if (!authDate || authDate > now + 30 || now - authDate > MAX_AUTH_AGE_SECONDS) {
    throw new HttpError(401, "stale_init_data", "Telegram init data is expired or invalid");
  }

  params.delete("hash");
  const dataCheckString = [...params.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${k}=${v}`)
    .join("\n");

  const secret = await crypto.subtle.digest("SHA-256", enc.encode(botToken));
  const computed = hex(await hmacSha256Raw(secret, dataCheckString));
  if (!safeEqual(computed, hash)) {
    throw new HttpError(401, "invalid_init_data", "Telegram init data signature mismatch");
  }

  const userRaw = params.get("user");
  if (!userRaw) throw new HttpError(401, "invalid_init_data", "Telegram user payload missing");

  let user: any;
  try {
    user = JSON.parse(userRaw);
  } catch {
    throw new HttpError(401, "invalid_init_data", "Telegram user payload invalid JSON");
  }

  if (!user?.id) throw new HttpError(401, "invalid_init_data", "Telegram user id missing");

  return {
    telegramUserId: Number(user.id),
    username: user.username ?? null,
    firstName: user.first_name ?? null,
    authDate,
  };
}
