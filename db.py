# db.py - database helper for Vexa bot
# Rewritten to be robust, idempotent and to write export files into /data by default.

import sqlite3
import time
import datetime
import csv
import os
import traceback
from contextlib import closing
from typing import Optional, List, Dict, Any

DB_DIR = "/data"
DB_PATH = os.path.join(DB_DIR, "bot.db")
os.makedirs(DB_DIR, exist_ok=True)

# A global connection is created for simple usages where required,
# but most functions use fresh connections (with closing(...)) to avoid
# concurrency/scope issues with sqlite.
con = sqlite3.connect(DB_PATH, check_same_thread=False)


# ----------------- Helpers -----------------
def _ensure_export_path(path: Optional[str]) -> str:
    """
    Ensure export path is inside DB_DIR when a relative path is given.
    If path is None, caller should provide a default filename.
    """
    if path is None:
        raise ValueError("path must be provided")
    # If user gave an absolute path, use it. Otherwise place under DB_DIR.
    if os.path.isabs(path):
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        return path
    os.makedirs(DB_DIR, exist_ok=True)
    return os.path.join(DB_DIR, path)


# ----------------- Init / Migrations -----------------
def init_db():
    """
    Create tables if not existing and run migrations. Safe to call multiple times.
    """
    try:
        with closing(sqlite3.connect(DB_PATH)) as c:
            cur = c.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS users(
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at INTEGER,
                credits INTEGER DEFAULT 0,
                ref_code TEXT,
                referred_by TEXT
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS kv_state(
                user_id INTEGER PRIMARY KEY,
                state TEXT
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS settings(
                key TEXT PRIMARY KEY,
                value TEXT
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS purchases(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                stars INTEGER,
                credits INTEGER,
                payload TEXT,
                created_at INTEGER
            )""")
            cur.execute("""CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                direction TEXT,
                text TEXT,
                created_at INTEGER
            )""")
            c.commit()
    except Exception:
        print("init_db: failed creating base tables", traceback.format_exc())

    # Run migrations that add optional columns
    try:
        _migrate_users_table()
    except Exception:
        print("_migrate_users_table failed", traceback.format_exc())

    try:
        _migrate_messages_kind()
    except Exception:
        print("_migrate_messages_kind failed", traceback.format_exc())

    # Ensure sane default settings
    try:
        ensure_default_settings()
    except Exception:
        print("ensure_default_settings failed", traceback.format_exc())


def _migrate_users_table():
    """
    Add columns to users table if missing (idempotent).
    """
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = {r[1] for r in cur.fetchall()}
        if "banned" not in cols:
            try:
                cur.execute("ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0")
            except Exception:
                pass
        if "last_seen" not in cols:
            try:
                cur.execute("ALTER TABLE users ADD COLUMN last_seen INTEGER DEFAULT 0")
            except Exception:
                pass
        if "referred_by" not in cols:
            try:
                cur.execute("ALTER TABLE users ADD COLUMN referred_by TEXT")
            except Exception:
                pass
        if "lang" not in cols:
            try:
                cur.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'fa'")
            except Exception:
                pass
        c.commit()


def _migrate_messages_kind():
    """
    Add 'kind' column to messages if missing. Used to distinguish TTS messages.
    """
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("PRAGMA table_info(messages)")
        cols = {r[1] for r in cur.fetchall()}
        if "kind" not in cols:
            try:
                cur.execute("ALTER TABLE messages ADD COLUMN kind TEXT DEFAULT ''")
            except Exception:
                # ignore if alter fails (older sqlite, locked, etc.)
                pass
        c.commit()


# ----------------- Settings -----------------
def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("SELECT value FROM settings WHERE key=?", (key,))
        r = cur.fetchone()
        return r[0] if r else default


def set_setting(key: str, value: Any):
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("""INSERT INTO settings(key,value) VALUES(?,?)
                       ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                    (key, str(value)))
        c.commit()


def get_settings() -> Dict[str, str]:
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("SELECT key,value FROM settings")
        return dict(cur.fetchall())


def ensure_default_settings():
    defaults = {
        "BONUS_REFERRAL": "30",
        "FREE_CREDIT": "80",
        "FORCE_SUB_MODE": "none",
        "TG_CHANNEL": "",
        "IG_URL": ""
    }
    for k, v in defaults.items():
        if get_setting(k) is None:
            set_setting(k, v)


# ----------------- Users -----------------
def touch_last_seen(user_id: int):
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("UPDATE users SET last_seen=? WHERE user_id=?", (int(time.time()), user_id))
        c.commit()


def get_or_create_user(u) -> Dict[str, Any]:
    """
    u is a Telegram user-like object with attributes id, username, first_name.
    Returns the user dict as stored in DB.
    """
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("SELECT user_id FROM users WHERE user_id=?", (u.id,))
        row = cur.fetchone()
        if not row:
            free_credit = int(get_setting("FREE_CREDIT", "80") or 80)
            ref_code = str(u.id)
            cur.execute("""INSERT INTO users(user_id,username,first_name,joined_at,credits,ref_code,last_seen,lang)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (u.id, (u.username or ""), (u.first_name or ""),
                         int(time.time()), free_credit, ref_code, int(time.time()), "fa"))
            c.commit()
        else:
            # Keep username/first_name updated
            cur.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?",
                        (u.username or "", u.first_name or "", u.id))
            c.commit()
    return get_user(u.id)


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("""SELECT user_id,username,first_name,joined_at,credits,ref_code,referred_by,banned,last_seen,lang
                       FROM users WHERE user_id=?""", (user_id,))
        row = cur.fetchone()
        if not row:
            return None
        keys = ["user_id", "username", "first_name", "joined_at", "credits", "ref_code", "referred_by", "banned", "last_seen", "lang"]
        return dict(zip(keys, row))


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    uname = (username or "").strip()
    if uname.startswith("@"):
        uname = uname[1:]
    if not uname:
        return None
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("""SELECT user_id,username,first_name,joined_at,credits,ref_code,referred_by,banned,last_seen,lang
                       FROM users WHERE LOWER(username)=LOWER(?) LIMIT 1""", (uname,))
        row = cur.fetchone()
        if not row:
            return None
        keys = ["user_id", "username", "first_name", "joined_at", "credits", "ref_code", "referred_by", "banned", "last_seen", "lang"]
        return dict(zip(keys, row))


def add_credits(user_id: int, amount: int):
    if amount == 0:
        return
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (amount, user_id))
        c.commit()


def deduct_credits(user_id: int, amount: int) -> bool:
    if amount <= 0:
        return True
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
        r = cur.fetchone()
        if not r or r[0] < amount:
            return False
        cur.execute("UPDATE users SET credits = credits - ? WHERE user_id=?", (amount, user_id))
        c.commit()
        return True


def set_state(user_id: int, state: str):
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("""INSERT INTO kv_state(user_id,state) VALUES(?,?)
                       ON CONFLICT(user_id) DO UPDATE SET state=excluded.state""",
                    (user_id, state))
        c.commit()


def get_state(user_id: int) -> Optional[str]:
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("SELECT state FROM kv_state WHERE user_id=?", (user_id,))
        r = cur.fetchone()
        return r[0] if r else None


def clear_state(user_id: int):
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("DELETE FROM kv_state WHERE user_id=?", (user_id,))
        c.commit()


def set_referred_by(user_id: int, code: str):
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("""UPDATE users
                       SET referred_by=?
                       WHERE user_id=? AND (referred_by IS NULL OR referred_by='')""",
                    (code, user_id))
        c.commit()


def count_invited(ref_code: str) -> int:
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (ref_code,))
        return cur.fetchone()[0]


# ----------------- Stats / Lists -----------------
def count_users() -> int:
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        return cur.fetchone()[0]


def sum_credits() -> int:
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("SELECT COALESCE(SUM(credits),0) FROM users")
        return cur.fetchone()[0]


def count_users_today() -> int:
    start = int(datetime.datetime.combine(datetime.date.today(), datetime.time.min).timestamp())
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE joined_at>=?", (start,))
        return cur.fetchone()[0]


def list_users(limit: int = 20, offset: int = 0) -> List[tuple]:
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("""SELECT user_id, username, credits, banned FROM users
                       ORDER BY joined_at DESC LIMIT ? OFFSET ?""", (limit, offset))
        return cur.fetchall()


def set_ban(user_id: int, banned: bool = True):
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("UPDATE users SET banned=? WHERE user_id=?", (1 if banned else 0, user_id))
        c.commit()


def log_purchase(user_id: int, stars: int, credits: int, payload: str):
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("""INSERT INTO purchases(user_id,stars,credits,payload,created_at)
                       VALUES(?,?,?,?,?)""", (user_id, stars, credits, payload, int(time.time())))
        c.commit()


def log_message(user_id: int, direction: str, text: str, kind: str = ""):
    """
    direction: 'in' or 'out' etc.
    kind: optional message kind, e.g. 'tts_in'
    """
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        # Ensure messages table has 'kind' column before inserting with kind
        cur.execute("PRAGMA table_info(messages)")
        cols = {r[1] for r in cur.fetchall()}
        if "kind" in cols:
            cur.execute("""INSERT INTO messages(user_id,direction,text,created_at,kind)
                           VALUES(?,?,?,?,?)""", (user_id, direction, text[:4000], int(time.time()), kind))
        else:
            cur.execute("""INSERT INTO messages(user_id,direction,text,created_at)
                           VALUES(?,?,?,?)""", (user_id, direction, text[:4000], int(time.time())))
        c.commit()


# ----------------- Exports -----------------
def export_users_csv(path: Optional[str] = None) -> str:
    if path is None:
        path = os.path.join(DB_DIR, "users.csv")
    path = _ensure_export_path(path)
    with closing(sqlite3.connect(DB_PATH)) as c, open(path, "w", newline="", encoding="utf-8") as f:
        cur = c.cursor()
        cur.execute("""SELECT user_id,username,first_name,joined_at,credits,ref_code,referred_by,banned,last_seen,lang FROM users""")
        w = csv.writer(f)
        w.writerow(["user_id", "username", "first_name", "joined_at", "credits", "ref_code", "referred_by", "banned", "last_seen", "lang"])
        rows = cur.fetchall()
        w.writerows(rows)
    return path


def export_purchases_csv(path: Optional[str] = None) -> str:
    if path is None:
        path = os.path.join(DB_DIR, "purchases.csv")
    path = _ensure_export_path(path)
    with closing(sqlite3.connect(DB_PATH)) as c, open(path, "w", newline="", encoding="utf-8") as f:
        cur = c.cursor()
        cur.execute("""SELECT id,user_id,stars,credits,payload,created_at FROM purchases""")
        w = csv.writer(f)
        w.writerow(["id", "user_id", "stars", "credits", "payload", "created_at"])
        w.writerows(cur.fetchall())
    return path


def export_messages_csv(path: Optional[str] = None) -> str:
    if path is None:
        path = os.path.join(DB_DIR, "messages.csv")
    path = _ensure_export_path(path)
    with closing(sqlite3.connect(DB_PATH)) as c, open(path, "w", newline="", encoding="utf-8") as f:
        cur = c.cursor()
        # If 'kind' exists, include it in export
        cur.execute("PRAGMA table_info(messages)")
        cols = {r[1] for r in cur.fetchall()}
        if "kind" in cols:
            cur.execute("""SELECT id,user_id,direction,text,created_at,kind FROM messages""")
            w = csv.writer(f)
            w.writerow(["id", "user_id", "direction", "text", "created_at", "kind"])
        else:
            cur.execute("""SELECT id,user_id,direction,text,created_at FROM messages""")
            w = csv.writer(f)
            w.writerow(["id", "user_id", "direction", "text", "created_at"])
        w.writerows(cur.fetchall())
    return path


def count_active_users(hours: int = 24) -> int:
    since = int(time.time()) - hours * 3600
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE last_seen>=?", (since,))
        return cur.fetchone()[0]


def get_all_user_ids() -> List[int]:
    with closing(sqlite3.connect(DB_PATH)) as c:
        cur = c.cursor()
        cur.execute("SELECT user_id FROM users")
        return [r[0] for r in cur.fetchall()]


def export_user_messages_csv(user_id: int, path: Optional[str] = None) -> str:
    if path is None:
        path = os.path.join(DB_DIR, f"user_{user_id}_messages.csv")
    path = _ensure_export_path(path)
    with closing(sqlite3.connect(DB_PATH)) as c, open(path, "w", newline="", encoding="utf-8") as f:
        cur = c.cursor()
        # include kind if available
        cur.execute("PRAGMA table_info(messages)")
        cols = {r[1] for r in cur.fetchall()}
        if "kind" in cols:
            cur.execute("""SELECT id, direction, text, created_at, kind
                           FROM messages
                           WHERE user_id=?
                           ORDER BY id ASC""", (user_id,))
            w = csv.writer(f)
            w.writerow(["id", "direction", "text", "created_at", "kind"])
        else:
            cur.execute("""SELECT id, direction, text, created_at
                           FROM messages
                           WHERE user_id=?
                           ORDER BY id ASC""", (user_id,))
            w = csv.writer(f)
            w.writerow(["id", "direction", "text", "created_at"])
        w.writerows(cur.fetchall())
    return path


def log_tts_request(user_id: int, text: str):
    """
    Log a TTS input from user (mark kind='tts_in' if column exists).
    """
    log_message(user_id, "in", text, kind="tts_in")


def export_user_tts_csv(user_id: int, path: Optional[str] = None) -> str:
    """
    Export only texts that were used for TTS by a user.
    Uses messages.kind='tts_in' if available; otherwise falls back to direction='in'.
    Default output file is placed under /data.
    """
    if path is None:
        path = os.path.join(DB_DIR, f"user_{user_id}_tts_texts.csv")
    path = _ensure_export_path(path)

    with closing(sqlite3.connect(DB_PATH)) as c, open(path, "w", newline="", encoding="utf-8") as f:
        cur = c.cursor()
        cur.execute("PRAGMA table_info(messages)")
        cols = {r[1] for r in cur.fetchall()}
        if "kind" in cols:
            cur.execute("""SELECT id, text, created_at
                           FROM messages
                           WHERE user_id=? AND kind='tts_in'
                           ORDER BY id ASC""", (user_id,))
        else:
            # fallback to direction='in' (best-effort)
            cur.execute("""SELECT id, text, created_at
                           FROM messages
                           WHERE user_id=? AND direction='in'
                           ORDER BY id ASC""", (user_id,))
        w = csv.writer(f)
        w.writerow(["id", "text", "created_at"])
        rows = cur.fetchall()
        w.writerows(rows)
    return path


# Initialize DB on import to ensure tables/migrations exist.
try:
    init_db()
except Exception:
    print("init_db encountered error on import:", traceback.format_exc())
