const DEFAULT_ALLOWED_HEADERS = ["authorization", "content-type", "x-api-key"];

export function withCors(request: Request, response: Response): Response {
  const origin = request.headers.get("origin");
  const headers = new Headers(response.headers);

  if (origin) {
    headers.set("access-control-allow-origin", origin);
    headers.set("vary", "Origin");
  } else {
    headers.set("access-control-allow-origin", "*");
  }

  headers.set("access-control-allow-methods", "GET,POST,PUT,DELETE,OPTIONS");
  headers.set("access-control-allow-headers", DEFAULT_ALLOWED_HEADERS.join(","));
  headers.set("access-control-max-age", "86400");

  return new Response(response.body, { status: response.status, headers });
}

export function handleCorsPreflight(request: Request): Response | null {
  if (request.method !== "OPTIONS") return null;
  return withCors(request, new Response(null, { status: 204 }));
}
