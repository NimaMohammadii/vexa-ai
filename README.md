# Vexa AI — Cloudflare-native shared platform

Vexa is now migrated to a **Cloudflare Workers-first architecture** with one shared backend for:

1. Telegram Bot (webhook)
2. Telegram Mini App
3. Website clients

The old Python polling stack (`main.py`, `api_server.py`, `db.py`) is retained only as **legacy reference** and is no longer the production target.

## Architecture

- **Runtime:** Cloudflare Workers (`workers-backend/src/index.ts`)
- **Persistence:** Cloudflare D1 (relational data)
- **Strong per-user flow state:** Durable Object (`UserStateDO`)
- **Auth:**
  - Telegram Mini App `initData` verification + issued session token
  - Bearer session token and per-user API token auth
- **Shared services:** user profile, credits, API token lifecycle, GPT history, assets, feature discovery

## Implemented API routes

### Public routes
- `GET /v1/health`
- `GET /v1/features`
- `GET /v1/telegram/webhook-info`
- `POST /v1/auth/telegram-miniapp`

### Authenticated routes
- `GET /v1/me`
- `GET /v1/me/credits`
- `GET /v1/me/api-token`
- `POST /v1/me/api-token/rotate`
- `GET /v1/me/gpt-history`
- `DELETE /v1/me/gpt-history`
- `GET /v1/me/assets`

### Telegram webhook route
- `POST /telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>`

Implemented bot commands:
- `/start`
- `/profile`
- `/credits`
- `/apitoken`
- `/rotatetoken`
- `/history`
- `/resethistory`

`callback_query` is now acknowledged and preserved as an extension point for future interactive flows.

## Storage model (D1)

Core tables in `workers-backend/migrations/0001_initial.sql`:

- `users`
- `api_tokens`
- `user_sessions`
- `gpt_messages`
- `generated_assets`
- `user_state`
- `credit_ledger`
- `feature_flags`

## Local development

```bash
cd workers-backend
npm install
npm run check
npm run dev
```

## D1 setup

1. Create database:
   ```bash
   wrangler d1 create vexa
   ```
2. Copy resulting `database_id` into `workers-backend/wrangler.toml`.
3. Run migrations locally:
   ```bash
   npm run d1:migrate:local
   ```
4. Run migrations remotely:
   ```bash
   npm run d1:migrate:remote
   ```

## Durable Object setup

`wrangler.toml` already binds `USER_STATE` and includes the class migration tag.
Deploy once after migration to register it in your Worker.

## Telegram webhook setup

1. Deploy Worker and copy base URL.
2. Set secrets:
   ```bash
   wrangler secret put TELEGRAM_BOT_TOKEN
   wrangler secret put TELEGRAM_WEBHOOK_SECRET
   ```
3. Set webhook:
   ```bash
   curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<WORKER_BASE_URL>/telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>"
   ```
4. Verify:
   ```bash
   curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
   ```

## Telegram Mini App auth flow

1. Mini App sends `initData` to `POST /v1/auth/telegram-miniapp`.
2. Backend validates signature and `auth_date` freshness.
3. Backend upserts user and issues a `Bearer` session token.
4. Mini App uses `Authorization: Bearer <accessToken>` for `/v1/me*` APIs.

## Production deploy

```bash
cd workers-backend
npm install
npm run check
npm run d1:migrate:remote
npm run deploy
```

## Legacy status

- Python polling bot is deprecated and not the active production architecture.
- New production path is Cloudflare Workers + D1 + Durable Objects.
- Legacy code is retained temporarily for behavior parity reference during final feature backfill.
