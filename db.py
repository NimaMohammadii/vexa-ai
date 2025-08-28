# db.py
# SQLite helper for Vexa AI bot
# — handles users, credits, settings, messages, purchases
# — gives FREE_CREDIT only once per user via welcome_granted flag

import os
import csv
import time
import sqlite3
from typing import Optional, Tuple, List, Dict, Any

DB_PATH = os.getenv("DB_PATH", "bot.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row


# ---------- bootstrap & migrations ----------

def create_tables() -> None:
    cur = conn.cursor()

    # users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id        INTEGER PRIMARY KEY,
        username       TEXT,
        first_name     TEXT,
        joined_at      INTEGER,
        credits        INTEGER DEFAULT 0,
        ref_code       TEXT,
        ref_by         INTEGER,
        last_seen      INTEGER,
        banned         INTEGER DEFAULT 0,
        selected_voice TEXT,
        welcome_granted INTEGER DEFAULT 0
    )
    """)

    # messages (for admin export of user TTS texts)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages(
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER,
        text       TEXT,
        created_at INTEGER
    )
    """)

    # purchases (Stars, etc.)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS purchases(
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER,
        stars      INTEGER,
        credits    INTEGER,
        status     TEXT,
        created_at INTEGER
    )
    """)

    # settings (key/value)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings(
        key   TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # --- migrations: make sure welcome_granted exists (safe idempotent)
    cur.execute("PRAGMA table_info(users)")
    cols = [r[1] for r in cur.fetchall()]
    if "welcome_granted" not in cols:
        cur.execute("ALTER TABLE users ADD COLUMN welcome_granted INTEGER DEFAULT 0")

    conn.commit()


create_tables()


# ---------- settings ----------

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = cur.fetchone()
    return (row["value"] if row else default)


def set_setting(key: str, value: str) -> None:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO settings(key,value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    conn.commit()


# ---------- users & credits ----------

def grant_welcome_credit(user_id: int, amount: int) -> bool:
    """Give initial credit only once. Returns True if applied now."""
    cur = conn.cursor()
    cur.execute("""
        UPDATE users
        SET credits = credits + ?, welcome_granted = 1
        WHERE user_id = ? AND welcome_granted = 0
    """, (amount, user_id))
    conn.commit()
    return cur.rowcount > 0


def upsert_user(u) -> Dict[str, Any]:
    """
    u: telebot.types.User
    Creates user if not exists (with FREE_CREDIT once), else updates profile.
    Returns minimal profile dict.
    """
    now = int(time.time())
    cur = conn.cursor()

    cur.execute("SELECT user_id, welcome_granted FROM users WHERE user_id=?", (u.id,))
    row = cur.fetchone()

    free_credit = int(get_setting("FREE_CREDIT", "80") or 80)
    ref_code = str(u.id)

    if not row:
        # new user → give initial credit once, flag = 1
        cur.execute("""
            INSERT INTO users(user_id, username, first_name, joined_at, credits, ref_code, last_seen, welcome_granted)
            VALUES(?,?,?,?,?,?,?,1)
        """, (
            u.id,
            (u.username or ""),
            (u.first_name or ""),
            now,
            free_credit,
            ref_code,
            now
        ))
        conn.commit()
    else:
        # existing → keep data fresh; if somehow flag not set, grant atomically
        cur.execute(
            "UPDATE users SET username=?, first_name=?, last_seen=? WHERE user_id=?",
            (u.username or "", u.first_name or "", now, u.id)
        )
        conn.commit()
        grant_welcome_credit(u.id, free_credit)

    return get_user(u.id)


def get_user(user_id: int) -> Dict[str, Any]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return dict(row) if row else {}


def set_selected_voice(user_id: int, voice_name: str) -> None:
    cur = conn.cursor()
    cur.execute("UPDATE users SET selected_voice=? WHERE user_id=?", (voice_name, user_id))
    conn.commit()


def get_credits(user_id: int) -> int:
    cur = conn.cursor()
    cur.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    return int(row["credits"]) if row else 0


def add_credits(user_id: int, amount: int) -> None:
    cur = conn.cursor()
    cur.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (amount, user_id))
    conn.commit()


def deduct_credits(user_id: int, amount: int) -> bool:
    """Deduct if enough balance. Returns True if done."""
    cur = conn.cursor()
    cur.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row or row["credits"] < amount:
        return False
    cur.execute("UPDATE users SET credits = credits - ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    return True


def set_banned(user_id: int, banned: bool) -> None:
    cur = conn.cursor()
    cur.execute("UPDATE users SET banned=? WHERE user_id=?", (1 if banned else 0, user_id))
    conn.commit()


def list_users(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY joined_at DESC LIMIT ? OFFSET ?", (limit, offset))
    return [dict(r) for r in cur.fetchall()]


def users_count() -> int:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM users")
    return int(cur.fetchone()["c"])


# ---------- messages (for admin export) ----------

def log_user_message(user_id: int, text: str) -> None:
    cur = conn.cursor()
    cur.execute("INSERT INTO messages(user_id, text, created_at) VALUES(?,?,?)",
                (user_id, text, int(time.time())))
    conn.commit()


def export_user_messages_csv(user_id: int) -> str:
    """
    Export user's messages to CSV; returns file path.
    Columns: id, user_id, text, created_at (ISO).
    """
    cur = conn.cursor()
    cur.execute("SELECT id, user_id, text, created_at FROM messages WHERE user_id=? ORDER BY id DESC", (user_id,))
    rows = cur.fetchall()

    path = f"messages_{user_id}.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "user_id", "text", "created_at"])
        for r in rows:
            w.writerow([r["id"], r["user_id"], r["text"], time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(r["created_at"]))])
    return path


# ---------- purchases ----------

def log_purchase(user_id: int, stars: int, credits: int, status: str) -> None:
    cur = conn.cursor()
    cur.execute("INSERT INTO purchases(user_id, stars, credits, status, created_at) VALUES(?,?,?,?,?)",
                (user_id, stars, credits, status, int(time.time())))
    conn.commit()


# ---------- credits cost helper (optional used by TTS) ----------

def cost_per_char() -> int:
    return int(get_setting("COST_PER_CHAR", "1") or 1)


# ---------- convenience for referral bonus (if elsewhere used) ----------

def add_referrer(user_id: int, ref_by: Optional[int]) -> None:
    """Set ref_by only if empty."""
    if not ref_by or ref_by == user_id:
        return
    cur = conn.cursor()
    cur.execute("SELECT ref_by FROM users WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        return
    if row["ref_by"] is None:
        cur.execute("UPDATE users SET ref_by=? WHERE user_id=?", (ref_by, user_id))
        conn.commit()
