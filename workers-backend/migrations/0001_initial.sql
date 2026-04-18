CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY,
  username TEXT,
  first_name TEXT,
  lang TEXT DEFAULT 'fa',
  banned INTEGER NOT NULL DEFAULT 0,
  credits REAL NOT NULL DEFAULT 0,
  ref_code TEXT,
  referred_by TEXT,
  joined_at INTEGER NOT NULL,
  last_seen_at INTEGER NOT NULL,
  onboarding_pending INTEGER NOT NULL DEFAULT 0,
  welcome_sent_at INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS api_tokens (
  user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
  token TEXT NOT NULL UNIQUE,
  created_at INTEGER NOT NULL,
  rotated_at INTEGER
);

CREATE TABLE IF NOT EXISTS user_sessions (
  session_token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  client_type TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS gpt_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS generated_assets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  asset_type TEXT NOT NULL,
  source_prompt TEXT,
  storage_url TEXT,
  status TEXT NOT NULL,
  provider TEXT,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS user_state (
  user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
  state_json TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS credit_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
  amount REAL NOT NULL,
  reason TEXT NOT NULL,
  source TEXT,
  created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS feature_flags (
  feature_key TEXT PRIMARY KEY,
  enabled INTEGER NOT NULL DEFAULT 1,
  description TEXT,
  updated_at INTEGER NOT NULL
);

INSERT OR IGNORE INTO feature_flags(feature_key, enabled, description, updated_at) VALUES
('telegram_bot', 1, 'Telegram bot webhook transport', strftime('%s','now')),
('telegram_mini_app', 1, 'Telegram Mini App client support', strftime('%s','now')),
('website', 1, 'Website client support over shared APIs', strftime('%s','now')),
('api_tokens', 1, 'Per-user API token lifecycle', strftime('%s','now')),
('gpt_history', 1, 'GPT history fetch/reset APIs', strftime('%s','now')),
('assets', 1, 'Generated assets list APIs', strftime('%s','now'));

CREATE INDEX IF NOT EXISTS idx_api_tokens_token ON api_tokens(token);
CREATE INDEX IF NOT EXISTS idx_sessions_user_expires ON user_sessions(user_id, expires_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_gpt_messages_user_created ON gpt_messages(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generated_assets_user_created ON generated_assets(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_credit_ledger_user_created ON credit_ledger(user_id, created_at DESC);
