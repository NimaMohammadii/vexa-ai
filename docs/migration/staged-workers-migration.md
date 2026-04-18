# Staged migration plan: Python polling bot ➜ Cloudflare Workers shared backend

## Repository inspection summary

### What can be reused

1. **Feature-level domain behavior already exists** inside service modules such as image, TTS, clone, GPT, and video. The core business actions (e.g. credit charging, generation flow) are conceptually reusable if detached from TeleBot update objects.
2. **Data model concepts in `db.py`** (users, credits, API tokens, GPT history, generated assets, cloned voices) are reusable as schema/contracts, even if the implementation must change.
3. **Existing FastAPI endpoint design** in `api_server.py` can seed the HTTP-first API shape for all clients.
4. **Localization text catalogs and feature flags** can be reused as part of service responses.

### What must be rewritten

1. **Transport wiring in `main.py` and module handlers** is tightly bound to pyTelegramBotAPI polling callbacks and cannot run in Cloudflare Workers.
2. **Persistence layer in `db.py`** relies on local `sqlite3` and filesystem paths (`/data/bot.db`), incompatible with Workers runtime constraints.
3. **Long-running/blocking processing assumptions** in current bot flow need asynchronous HTTP-friendly orchestration (job status endpoints and webhooks where needed).
4. **Authentication model** must expand from bot-user context and `X-API-Key` into mini app init data validation + website session/JWT boundaries.

### What should be migrated first

1. **Establish storage abstraction + Cloudflare-native adapters** (D1 + Durable Objects).
2. **Introduce transport-agnostic service layer** for user profile, credits, GPT history, API token, assets metadata.
3. **Stand up Workers HTTP API** for mini app + website + Telegram webhook ingress.
4. **Migrate Telegram bot from polling to webhook delivery** with service calls instead of direct DB logic.
5. **Backfill remaining feature modules** (image/video/tts/gpt advanced flows) into service layer incrementally.

## Staged phases

### Phase 0 (this change set)
- Add Workers backend skeleton with shared API surface.
- Add service layer contracts for profile/credits/history/token/feature entrypoints.
- Add storage abstractions and initial D1/Durable Object usage points.
- Add Telegram webhook + Mini App init-data validation entrypoints.

### Phase 1
- Port Python DB read/write call sites module-by-module into service layer methods.
- Mirror existing user-visible bot responses for `/start`, profile, credit checks, GPT entrypoint.

### Phase 2
- Move generation workloads to provider adapters and async job model.
- Add website auth/session boundary and admin/internal route separation.

### Phase 3
- Decommission polling process and local sqlite, cut over to webhook-only bot.
- Run data migration from current sqlite exports into D1/DO stores.

## Compatibility notes

- This migration intentionally **does not attempt to run Python bot code inside Workers**.
- User-visible behavior can be preserved for simple flows first; media-heavy and long-running features may temporarily return "processing" + status polling responses during phased migration.
