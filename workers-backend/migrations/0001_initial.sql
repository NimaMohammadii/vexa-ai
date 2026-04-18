CREATE TABLE IF NOT EXISTS users (
  user_id INTEGER PRIMARY KEY,
  username TEXT,
  first_name TEXT,
  lang TEXT DEFAULT 'fa',
  banned INTEGER NOT NULL DEFAULT 0,
  credits REAL NOT NULL DEFAULT 0,
  joined_at INTEGER NOT NULL,
  last_seen_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS api_tokens (
  user_id INTEGER PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
  token TEXT NOT NULL UNIQUE,
  created_at INTEGER NOT NULL,
  rotated_at INTEGER
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
  created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_gpt_messages_user_created
  ON gpt_messages(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_generated_assets_user_created
  ON generated_assets(user_id, created_at DESC);
