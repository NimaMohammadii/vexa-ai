#!/usr/bin/env bash
set -euo pipefail

WORKER_BASE_URL="${WORKER_BASE_URL:-https://vexaai.vexaagent.workers.dev}"
WEBHOOK_SECRET="${TELEGRAM_WEBHOOK_SECRET:-}"
BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"

if [[ -z "$BOT_TOKEN" ]]; then
  echo "ERROR: TELEGRAM_BOT_TOKEN is required in environment." >&2
  exit 1
fi

if [[ -z "$WEBHOOK_SECRET" ]]; then
  echo "ERROR: TELEGRAM_WEBHOOK_SECRET is required in environment." >&2
  exit 1
fi

WEBHOOK_URL="${WORKER_BASE_URL}/telegram/webhook/${WEBHOOK_SECRET}"
SET_URL="https://api.telegram.org/bot${BOT_TOKEN}/setWebhook"
INFO_URL="https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"

echo "Setting Telegram webhook to: ${WEBHOOK_URL}"
set_response="$(curl -sS --get "$SET_URL" --data-urlencode "url=${WEBHOOK_URL}")"
echo "setWebhook response:"
echo "$set_response"

echo
info_response="$(curl -sS "$INFO_URL")"
echo "getWebhookInfo response:"
echo "$info_response"
