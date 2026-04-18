# Hard-cutover migration complete: Python stack archived, Worker is primary

Date: 2026-04-18

## Cutover outcome

The repository is no longer dual-primary.

- Active production runtime is Cloudflare Workers in `workers-backend/`.
- Python runtime has been moved to `legacy/` for reference only.
- Telegram bot is webhook-based on Worker route `/telegram/webhook/<secret>`.
- Telegram Mini App and Website both use shared Worker APIs and auth.

## Auth model

- Mini App auth endpoint: `POST /miniapp/auth/telegram`
- Telegram `initData` is validated via official HMAC procedure.
- Backend creates `user_sessions` token and returns Bearer credentials.
- Authenticated routes use `Authorization: Bearer <token>` or `x-api-key`.

## Shared domain coverage

Implemented in Worker service layer:

- users/profile bootstrap
- credits balance and consumption/grant ledger
- per-user API token lifecycle
- GPT history list/append/clear
- generated assets listing
- feature discovery
- Telegram bot interaction flow with Durable Object-backed prompt mode state

## Required route coverage

Implemented routes:

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

No advertised route in `/v1/features` points to a missing handler.

## Storage updates

D1 migrations now include:

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

Durable Object class:

- `UserStateDO` for per-user bot flow state

## Remaining parity gaps

Some advanced generation/provider logic from the legacy Python modules remains to be ported:

- deep provider-specific generation pipelines
- legacy admin/referral/economics command surface breadth
- niche command UX parity

These are migration backlog items on top of a complete infrastructure/runtime cutover.
