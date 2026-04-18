# Migration status: Python polling stack ➜ Cloudflare Workers shared backend

## Completed cutover decisions

- Primary backend runtime is now **Cloudflare Workers**.
- Telegram bot transport is now **webhook-based** (no polling in the new architecture).
- Shared APIs are now available for Telegram Mini App and Website clients.
- D1 is now the persistent source of truth for shared entities.
- Durable Object support is retained for strongly consistent per-user state workflows.

## Shared domain concepts carried forward

The Workers data model and services preserve these repository concepts:

- users/profile + bootstrap from Telegram identity
- credits/balance representation
- API token lifecycle (read + rotate)
- GPT history listing/reset
- generated assets listing
- feature discovery for clients

## What is intentionally left as parity backlog

The following advanced generation/provider workflows from legacy Python are not yet fully ported:

- image/video/tts generation provider execution pipelines
- referral/purchase/admin commands and economics edge cases
- legacy module-specific conversational flows

These are now explicit backlog items and are no longer hidden behind scaffold routes.

## New backend route map (implemented)

- `GET /v1/health`
- `GET /v1/features`
- `GET /v1/telegram/webhook-info`
- `POST /v1/auth/telegram-miniapp`
- `GET /v1/me`
- `GET /v1/me/credits`
- `GET /v1/me/api-token`
- `POST /v1/me/api-token/rotate`
- `GET /v1/me/gpt-history`
- `DELETE /v1/me/gpt-history`
- `GET /v1/me/assets`
- `POST /telegram/webhook/<secret>`

## Operational note

Do not run `main.py` polling as primary production runtime after this migration stage. Python code is now legacy reference only.
