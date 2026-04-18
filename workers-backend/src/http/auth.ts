import { HttpError } from "./response";
import type { Services } from "../routes/types";

function bearerToken(req: Request): string | null {
  const raw = req.headers.get("authorization") ?? "";
  const [scheme, token] = raw.split(" ");
  if (scheme?.toLowerCase() !== "bearer" || !token) return null;
  return token.trim();
}

export async function resolveAuthedUserId(req: Request, services: Services): Promise<number | null> {
  const bearer = bearerToken(req);
  if (bearer) {
    const session = await services.sessions.getByToken(bearer);
    if (session) return session.userId;

    const apiTokenUserId = await services.tokens.resolveTokenToUser(bearer);
    if (apiTokenUserId) return apiTokenUserId;
  }

  const apiKey = req.headers.get("x-api-key")?.trim();
  if (apiKey) return services.tokens.resolveTokenToUser(apiKey);

  return null;
}

export async function requireAuthedUserId(req: Request, services: Services): Promise<number> {
  const userId = await resolveAuthedUserId(req, services);
  if (!userId) throw new HttpError(401, "unauthorized", "Missing or invalid authentication token");
  return userId;
}
