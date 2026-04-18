-- Runtime consistency patch for Cloudflare Workers migration.
-- Ensures tables used by current repositories exist in every environment.

CREATE TABLE IF NOT EXISTS telegram_webhook_events (
  update_id INTEGER PRIMARY KEY,
  telegram_user_id INTEGER,
  event_type TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS owner_notifications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
  source TEXT NOT NULL,
  category TEXT NOT NULL,
  message TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  created_at INTEGER NOT NULL,
  delivered_at INTEGER
);

-- Query helpers for webhook/event inspection and owner escalation workflows.
CREATE INDEX IF NOT EXISTS idx_telegram_webhook_events_event_created
  ON telegram_webhook_events(event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_telegram_webhook_events_user_created
  ON telegram_webhook_events(telegram_user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_owner_notifications_status_created
  ON owner_notifications(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_owner_notifications_recent
  ON owner_notifications(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_owner_notifications_user_created
  ON owner_notifications(user_id, created_at DESC);
