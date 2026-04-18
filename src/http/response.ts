export interface ApiOk<T> {
  ok: true;
  data: T;
}

export interface ApiErr {
  ok: false;
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export class HttpError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details?: unknown
  ) {
    super(message);
  }
}

export function jsonOk<T>(data: T, status = 200, headers: HeadersInit = {}): Response {
  return new Response(JSON.stringify({ ok: true, data } satisfies ApiOk<T>), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      ...headers,
    },
  });
}

export function jsonError(err: unknown, fallbackMessage = "Internal Server Error"): Response {
  if (err instanceof HttpError) {
    return new Response(
      JSON.stringify({
        ok: false,
        error: {
          code: err.code,
          message: err.message,
          details: err.details,
        },
      } satisfies ApiErr),
      {
        status: err.status,
        headers: { "content-type": "application/json; charset=utf-8" },
      }
    );
  }

  return new Response(
    JSON.stringify({
      ok: false,
      error: {
        code: "internal_error",
        message: fallbackMessage,
      },
    } satisfies ApiErr),
    {
      status: 500,
      headers: { "content-type": "application/json; charset=utf-8" },
    }
  );
}

export function parseJsonBody<T>(request: Request): Promise<T> {
  return request.json<T>();
}
