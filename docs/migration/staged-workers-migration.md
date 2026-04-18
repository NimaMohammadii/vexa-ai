# Hard-cutover migration complete: Workers-only production

Date: 2026-04-18

## Outcome

- Active production runtime is Cloudflare Workers (`src/index.ts`).
- Python runtime is archived in `legacy/` and removed from deployment path.
- Telegram bot runs webhook transport at `/telegram/webhook/<secret>`.
- Telegram Mini App and website share the same backend and auth/session system.

## Runtime contracts

### Required routes implemented

- `POST /telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>`
- `POST /miniapp/auth/telegram`
- `GET /v1/me`
- `GET /v1/me/credits`
- `GET /v1/me/api-token`
- `POST /v1/me/api-token/rotate`
- `GET /v1/me/gpt-history`
- `DELETE /v1/me/gpt-history`
- `GET /v1/me/assets`
- `GET /v1/features`

No route advertised in `/v1/features` points to a missing endpoint.

## Auth/session model

- Mini App `initData` is validated via Telegram HMAC verification.
- Backend upserts the user and creates a `user_sessions` record.
- Returned bearer token works immediately for `/v1/me*` endpoints.
- API tokens remain valid via Bearer or `x-api-key` for website/server callers.

## D1 schema coverage

Core tables:

- `users`
- `api_tokens`
- `user_sessions`
- `gpt_messages`
- `generated_assets`
- `credit_ledger`
- `feature_flags`
- `feature_access`
- `telegram_webhook_events`
- `website_sessions`
- `owner_notifications`

## Durable Objects

- `UserStateDO`: per-user Telegram bot conversational state only.

## Shared services

- user/profile service
- credits service
- API token service
- GPT history service
- assets service
- feature discovery service
- bot interaction service
- owner notification service
