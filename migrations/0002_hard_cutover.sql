-- Hard-cutover schema extensions for Cloudflare-native runtime

CREATE TABLE IF NOT EXISTS feature_access (
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  feature_key TEXT NOT NULL REFERENCES feature_flags(feature_key) ON DELETE CASCADE,
  enabled INTEGER NOT NULL DEFAULT 1,
  source TEXT NOT NULL DEFAULT 'system',
  updated_at INTEGER NOT NULL,
  PRIMARY KEY (user_id, feature_key)
);

CREATE TABLE IF NOT EXISTS telegram_webhook_events (
  update_id INTEGER PRIMARY KEY,
  telegram_user_id INTEGER,
  event_type TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS website_sessions (
  session_token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
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

INSERT OR IGNORE INTO feature_flags(feature_key, enabled, description, updated_at) VALUES
('credit_ledger', 1, 'User credit ledger APIs', strftime('%s','now')),
('telegram_prompt_mode', 1, 'Telegram prompt capture flow over webhook + Durable Object state', strftime('%s','now')),
('miniapp_auth', 1, 'Telegram Mini App authentication and session issuance', strftime('%s','now')),
('owner_notifications', 1, 'Owner notification and handoff foundations', strftime('%s','now'));

CREATE INDEX IF NOT EXISTS idx_feature_access_user ON feature_access(user_id);
CREATE INDEX IF NOT EXISTS idx_telegram_webhook_events_user ON telegram_webhook_events(telegram_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_website_sessions_user ON website_sessions(user_id, expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_owner_notifications_user ON owner_notifications(user_id, created_at DESC);
