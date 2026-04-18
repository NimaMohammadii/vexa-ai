# Vexa AI: Cloudflare-native production backend

This repository is hard-cut over to **Cloudflare Workers** as the only production runtime.

## Production architecture (authoritative)

- **Runtime:** Cloudflare Workers (`src/index.ts`)
- **Persistent relational data:** Cloudflare D1 (`migrations/*.sql`)
- **Per-user flow state:** Durable Objects (`src/storage/user-state-do.ts`)
- **Clients on one backend:** Telegram bot (webhook), Telegram Mini App, Website
- **Shared services:** user/profile, credits, API tokens, GPT history, assets, features, bot flow, owner notifications

## Python status

Legacy Python code is archived under `legacy/` for reference only.

- `legacy/main.py` (old polling bot runtime)
- `legacy/api_server.py` (old FastAPI backend)
- `legacy/db.py` (old sqlite/local-filesystem persistence)

Python is **not** part of the active production path.

## API routes

### Telegram
- `POST /telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>`
- `GET /v1/telegram/webhook-info`

### Auth (Mini App + Website)
- `POST /miniapp/auth/telegram`

### Public
- `GET /v1/health`
- `GET /v1/features`
- `GET /v1/public/features`

### Authenticated
- `GET /v1/me`
- `GET /v1/me/credits`
- `GET /v1/me/credits/ledger`
- `GET /v1/me/api-token`
- `POST /v1/me/api-token/rotate`
- `GET /v1/me/gpt-history`
- `DELETE /v1/me/gpt-history`
- `GET /v1/me/assets`

## Local development

```bash
npm install
npm run check
npm run d1:migrate:local
npm run dev
```

## D1 setup (required before deploy)

Create D1 once:

```bash
wrangler d1 create vexa
```

Then copy the returned `database_id` into `wrangler.toml` under `[[d1_databases]]`:

- Replace `__REPLACE_WITH_D1_DATABASE_ID__` with your real D1 ID.
- `npm run deploy` and `npm run d1:migrate:remote` will fail until this is replaced.

## D1 migrations

Apply local migrations:

```bash
npm run d1:migrate:local
# equivalent:
# wrangler d1 migrations apply vexa --local
```

Apply remote (production) migrations:

```bash
npm run d1:migrate:remote
# equivalent:
# wrangler d1 migrations apply vexa --remote
```

## Required secrets

Set required secrets:

```bash
wrangler secret put TELEGRAM_BOT_TOKEN
wrangler secret put TELEGRAM_WEBHOOK_SECRET
```

Optional secret for owner escalation notifications:

```bash
wrangler secret put OWNER_TELEGRAM_CHAT_ID
```

## Telegram webhook setup

Run the helper (recommended):

```bash
TELEGRAM_BOT_TOKEN=... TELEGRAM_WEBHOOK_SECRET=... ./scripts/setup-telegram-webhook.sh
```

Or call Telegram API manually:

```bash
npm run deploy
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<WORKER_BASE_URL>/telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>"
curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
```

## Deploy (production)

```bash
npm install
npm run check
npm run d1:migrate:remote
npm run deploy
```

## Pre-deploy checklist (minimum)

- [ ] D1 database created (`wrangler d1 create vexa`)
- [ ] `wrangler.toml` updated with real `database_id`
- [ ] Migrations applied locally and remotely
- [ ] Required secrets set (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_SECRET`)
- [ ] Optional `OWNER_TELEGRAM_CHAT_ID` set if owner notifications are needed
- [ ] `npm run deploy` executed
