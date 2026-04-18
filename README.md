# Vexa AI (Hard Cutover): Cloudflare Workers as the only production runtime

This repository has been hard-cut over to a **Cloudflare-native backend**.

## Production runtime (authoritative)

- **Primary backend:** Cloudflare Workers (`workers-backend/`)
- **Data storage:** Cloudflare D1
- **State coordination:** Cloudflare Durable Objects
- **Telegram bot transport:** webhook-only (no polling)
- **Client surfaces:** Telegram bot + Telegram Mini App + Website on one shared backend

## Legacy Python status

The previous Python production stack has been archived under `legacy/` and is no longer the deployment target.

- Deprecated bot runtime: `legacy/main.py`
- Deprecated API runtime: `legacy/api_server.py`
- Deprecated sqlite layer: `legacy/db.py`

Do **not** deploy from root Python files. Deploy only the Worker in `workers-backend/`.

## Shared backend routes

### Telegram
- `POST /telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>`
- `GET /v1/telegram/webhook-info`

### Mini App / Website auth
- `POST /miniapp/auth/telegram`

### Public APIs
- `GET /v1/health`
- `GET /v1/features`
- `GET /v1/public/features`

### Authenticated APIs
- `GET /v1/me`
- `GET /v1/me/credits`
- `GET /v1/me/api-token`
- `POST /v1/me/api-token/rotate`
- `GET /v1/me/gpt-history`
- `DELETE /v1/me/gpt-history`
- `GET /v1/me/assets`

## Local development

```bash
cd workers-backend
npm install
npm run check
npm run dev
```

## One-time infrastructure setup

```bash
cd workers-backend
wrangler d1 create vexa
```

Copy the returned `database_id` into `workers-backend/wrangler.toml` under `[[d1_databases]]`.

Apply schema:

```bash
npm run d1:migrate:local
npm run d1:migrate:remote
```

## Telegram webhook setup

1. Set Worker secrets:
   ```bash
   cd workers-backend
   wrangler secret put TELEGRAM_BOT_TOKEN
   wrangler secret put TELEGRAM_WEBHOOK_SECRET
   ```
2. Deploy Worker:
   ```bash
   npm run deploy
   ```
3. Register webhook:
   ```bash
   curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook?url=<WORKER_BASE_URL>/telegram/webhook/<TELEGRAM_WEBHOOK_SECRET>"
   ```
4. Verify:
   ```bash
   curl "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/getWebhookInfo"
   ```

## Production deploy

```bash
cd workers-backend
npm install
npm run check
npm run d1:migrate:remote
npm run deploy
```

