CREATE TABLE IF NOT EXISTS user_settings (
  chat_id TEXT PRIMARY KEY NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  selected_decks_json TEXT NOT NULL DEFAULT '["*"]',
  reminder_times_json TEXT NOT NULL DEFAULT '["08:00","18:00"]',
  timezone TEXT NOT NULL DEFAULT 'Asia/Ho_Chi_Minh',
  language TEXT NOT NULL DEFAULT 'vi-en',
  version INTEGER NOT NULL DEFAULT 1,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_state (
  chat_id TEXT PRIMARY KEY NOT NULL,
  sent_slots_json TEXT NOT NULL DEFAULT '{}',
  completion_sent_dates_json TEXT NOT NULL DEFAULT '[]',
  last_sync_at TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS decks (
  deck_name TEXT PRIMARY KEY NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS telegram_sessions (
  chat_id TEXT PRIMARY KEY NOT NULL,
  flow TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS processed_updates (
  update_id INTEGER PRIMARY KEY NOT NULL,
  processed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_decks_name ON decks(deck_name);
