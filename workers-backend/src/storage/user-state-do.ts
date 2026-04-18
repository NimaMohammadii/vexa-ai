/**
 * Per-user strongly consistent state.
 * Intended for flows like in-progress Telegram conversation/session state.
 */
export class UserStateDO extends DurableObject {
  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);

    if (request.method === "GET" && url.pathname === "/state") {
      const state = (await this.ctx.storage.get<string>("state")) ?? "";
      return Response.json({ state });
    }

    if (request.method === "PUT" && url.pathname === "/state") {
      const body = (await request.json()) as { state?: string };
      await this.ctx.storage.put("state", body.state ?? "");
      return Response.json({ ok: true });
    }

    return new Response("Not Found", { status: 404 });
  }
}
