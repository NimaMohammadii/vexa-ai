import csv
import datetime
import io
import mimetypes
import os
import secrets
import sqlite3
import tempfile
import time
import zipfile
from contextlib import closing
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlparse

import requests

DB_DIR = os.getenv("DB_DIR", "/data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "bot.db")

print("DB_PATH =>", DB_PATH, flush=True)

con = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = con.cursor()


_CREDIT_QUANTIZER = Decimal("0.01")


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def normalize_credit_amount(value) -> float:
    """Normalize a credit value to two decimal places.

    The function accepts values such as ``None``, ``int``, ``float`` or strings
    and returns a ``float`` rounded to two decimal places using
    ``ROUND_HALF_UP``. Any invalid inputs are treated as ``0``.
    """

    decimal_value = _to_decimal(value)
    normalized = decimal_value.quantize(_CREDIT_QUANTIZER, rounding=ROUND_HALF_UP)
    return float(normalized)


def format_credit_amount(value) -> str:
    """Return a user-facing string for a credit value.

    Numbers are rounded the same way as :func:`normalize_credit_amount` and
    trailing zeros are trimmed so that ``1`` stays ``"1"`` and ``1.50`` becomes
    ``"1.5"``. Negative balances are preserved.
    """

    normalized = _to_decimal(normalize_credit_amount(value))
    quantized = normalized.quantize(_CREDIT_QUANTIZER, rounding=ROUND_HALF_UP)
    text = format(quantized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _normalize_user_dict(keys, row):
    data = dict(zip(keys, row))
    if "credits" in data:
        data["credits"] = normalize_credit_amount(data["credits"])
    return data

def init_db():
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at INTEGER,
            credits INTEGER DEFAULT 0,
            ref_code TEXT,
            referred_by TEXT,
            onboarding_pending INTEGER DEFAULT 0,
            welcome_sent_at INTEGER DEFAULT 0,
            daily_bonus_prompted_at INTEGER DEFAULT 0,
            daily_bonus_unlocked_at INTEGER DEFAULT 0,
            daily_bonus_reminded_at INTEGER DEFAULT 0,
            low_credit_prompted_at INTEGER DEFAULT 0,
            tts_creator_prompted_at INTEGER DEFAULT 0,
            last_main_menu_id INTEGER DEFAULT 0
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
        cur.execute("""CREATE TABLE IF NOT EXISTS gpt_messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )""")
        cur.execute(
            """CREATE TABLE IF NOT EXISTS vexa_assistant_messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL
            )"""
        )
        # 🟢 جدول جدید برای صداهای اختصاصی
        cur.execute("""CREATE TABLE IF NOT EXISTS user_voices(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            voice_name TEXT,
            voice_id TEXT,
            created_at INTEGER
        )""")
        cur.execute(
            """CREATE TABLE IF NOT EXISTS image_generations(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                prompt TEXT,
                image_url TEXT,
                created_at INTEGER NOT NULL
            )"""
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS api_tokens(
                user_id INTEGER PRIMARY KEY,
                token TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                rotated_at INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )"""
        )
        cur.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_api_tokens_token ON api_tokens(token)"
        )
        cur.execute(
            """CREATE TABLE IF NOT EXISTS sora2_requests(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                created_at INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending'
            )"""
        )
        con.commit()
    _migrate_users_table()
    ensure_default_settings()
    _migrate_messages_kind()


def ensure_default_settings():
    defaults = {
        "BONUS_REFERRAL": "30",
        "FREE_CREDIT": "80",
        "FORCE_SUB_MODE": "none",
        "TG_CHANNEL": "",
        "IG_URL": "",
        "FEATURE_GPT": "1",
        "FEATURE_TTS": "1",
        "FEATURE_CLONE": "1",
        "FEATURE_IMAGE": "1",
        "FEATURE_VIDEO": "1",
        "FEATURE_SORA2": "1",
    }
    for k,v in defaults.items():
        if get_setting(k) is None:
            set_setting(k,v)


def _generate_api_token() -> str:
    return secrets.token_urlsafe(32)


def get_api_token(user_id: int) -> str | None:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT token FROM api_tokens WHERE user_id=? LIMIT 1",
            (user_id,),
        )
        row = cur.fetchone()
        return row[0] if row else None


def _upsert_api_token(user_id: int, token: str) -> str:
    now = int(time.time())
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """INSERT INTO api_tokens(user_id, token, created_at, rotated_at)
                   VALUES(?,?,?,NULL)
                   ON CONFLICT(user_id) DO UPDATE SET
                       token=excluded.token,
                       rotated_at=?
            """,
            (user_id, token, now, now),
        )
        con.commit()
    return token


def get_or_create_api_token(user_id: int) -> str:
    existing = get_api_token(user_id)
    if existing:
        return existing
    token = _generate_api_token()
    return _upsert_api_token(user_id, token)


def rotate_api_token(user_id: int) -> str:
    token = _generate_api_token()
    return _upsert_api_token(user_id, token)


def get_user_by_api_token(token: str):
    cleaned = (token or "").strip()
    if not cleaned:
        return None
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """SELECT u.user_id,u.username,u.first_name,u.joined_at,u.credits,u.ref_code,
                       u.referred_by,u.banned,u.last_seen,u.lang
                   FROM api_tokens t
                   JOIN users u ON u.user_id = t.user_id
                   WHERE t.token=?
            """,
            (cleaned,),
        )
        row = cur.fetchone()
        if not row:
            return None
        keys = [
            "user_id",
            "username",
            "first_name",
            "joined_at",
            "credits",
            "ref_code",
            "referred_by",
            "banned",
            "last_seen",
            "lang",
        ]
        return dict(zip(keys, row))

# -------------------
# User Voice Helpers
# -------------------
def add_user_voice(user_id:int, voice_name:str, voice_id:str):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("""INSERT INTO user_voices(user_id,voice_name,voice_id,created_at)
                       VALUES(?,?,?,?)""",
                    (user_id, voice_name, voice_id, int(time.time())))
        con.commit()

def list_user_voices(user_id:int):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT voice_name,voice_id FROM user_voices WHERE user_id=? ORDER BY id DESC",(user_id,))
        return cur.fetchall() or []

def get_user_voice(user_id:int, voice_name:str):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT voice_id FROM user_voices WHERE user_id=? AND voice_name=? LIMIT 1",(user_id,voice_name))
        r = cur.fetchone()
        return r[0] if r else None

def delete_user_voice_by_voice_id(voice_id:str):
    """حذف صدا از دیتابیس بر اساس voice_id"""
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("DELETE FROM user_voices WHERE voice_id=?", (voice_id,))
        con.commit()
        return cur.rowcount > 0

# 🟡 (بقیه توابع قبلی بدون تغییر می‌مونن)
def get_setting(key, default=None):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT value FROM settings WHERE key=?", (key,))
        r = cur.fetchone()
        return r[0] if r else default

def set_setting(key, value):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("""INSERT INTO settings(key,value) VALUES(?,?)
                       ON CONFLICT(key) DO UPDATE SET value=excluded.value""",
                    (key, str(value)))
        con.commit()

def get_settings():
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT key,value FROM settings")
        return dict(cur.fetchall())

def touch_last_seen(user_id):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("UPDATE users SET last_seen=? WHERE user_id=?", (int(time.time()), user_id))
        con.commit()



def get_user_by_username(username:str):
    """@name یا name → user dict یا None"""
    uname = (username or "").strip()
    if uname.startswith("@"): uname = uname[1:]
    if not uname: return None
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("""SELECT user_id,username,first_name,joined_at,credits,ref_code,referred_by,banned,last_seen
                       FROM users WHERE LOWER(username)=LOWER(?) LIMIT 1""", (uname,))
        row = cur.fetchone()
        if not row:
            return None
        keys = [
            "user_id",
            "username",
            "first_name",
            "joined_at",
            "credits",
            "ref_code",
            "referred_by",
            "banned",
            "last_seen",
        ]
        return _normalize_user_dict(keys, row)

def add_credits(user_id, amount):
    amount = normalize_credit_amount(amount)
    if amount == 0:
        return

    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        if not row:
            return

        current = normalize_credit_amount(row[0])
        new_balance = normalize_credit_amount(current + amount)

        cur.execute("UPDATE users SET credits=? WHERE user_id=?", (new_balance, user_id))
        con.commit()

def deduct_credits(user_id, amount):
    amount = normalize_credit_amount(amount)
    if amount <= 0:
        return True

    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
        r = cur.fetchone()
        if not r:
            return False

        current = normalize_credit_amount(r[0])
        if current < amount:
            return False

        new_balance = normalize_credit_amount(current - amount)
        cur.execute("UPDATE users SET credits=? WHERE user_id=?", (new_balance, user_id))
        con.commit()
        return True

def set_state(user_id, state):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("""INSERT INTO kv_state(user_id,state) VALUES(?,?)
                       ON CONFLICT(user_id) DO UPDATE SET state=excluded.state""",
                    (user_id, state))
        con.commit()

def get_state(user_id):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT state FROM kv_state WHERE user_id=?", (user_id,))
        r = cur.fetchone()
        return r[0] if r else None

def clear_state(user_id):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("DELETE FROM kv_state WHERE user_id=?", (user_id,))
        con.commit()

def set_referred_by(user_id, code):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("""UPDATE users
                       SET referred_by=?
                       WHERE user_id=? AND (referred_by IS NULL OR referred_by='')""",
                    (code, user_id))
        con.commit()

def count_invited(ref_code):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (ref_code,))
        return cur.fetchone()[0]


def create_sora2_request(user_id: int) -> int:
    """Create a Sora 2 invite request and return the 1-based queue index."""

    now = int(time.time())
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM sora2_requests")
        row = cur.fetchone()
        position = int(row[0]) + 1 if row and row[0] is not None else 1
        cur.execute(
            """INSERT INTO sora2_requests(user_id, created_at, status)
                   VALUES(?,?,?)""",
            (user_id, now, "pending"),
        )
        con.commit()
        return position


# آمار و خروجی‌ها
def count_users():
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        return cur.fetchone()[0]

def sum_credits():
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT COALESCE(SUM(credits),0) FROM users")
        return cur.fetchone()[0]

def count_users_today():
    start = int(datetime.datetime.combine(datetime.date.today(), datetime.time.min).timestamp())
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE joined_at>=?", (start,))
        return cur.fetchone()[0]

def list_users(limit=20, offset=0):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("""SELECT user_id, username, credits, banned FROM users
                       ORDER BY joined_at DESC LIMIT ? OFFSET ?""", (limit, offset))
        rows = cur.fetchall()
    return [
        (user_id, username, normalize_credit_amount(credits), banned)
        for user_id, username, credits, banned in rows
    ]


def list_image_users(limit=20, offset=0):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT ig.user_id,
                   u.username,
                   u.credits,
                   u.banned,
                   COUNT(*) AS total_images,
                   MAX(ig.created_at) AS last_created_at
              FROM image_generations AS ig
         LEFT JOIN users AS u ON u.user_id = ig.user_id
          GROUP BY ig.user_id
          ORDER BY last_created_at DESC
             LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = cur.fetchall() or []

    return [
        {
            "user_id": row[0],
            "username": row[1] or "",
            "credits": normalize_credit_amount(row[2]),
            "banned": bool(row[3]),
            "total_images": row[4] or 0,
            "last_created_at": row[5] or 0,
        }
        for row in rows
    ]


def list_gpt_users(limit=20, offset=0):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT gm.user_id,
                   u.username,
                   u.credits,
                   u.banned,
                   COUNT(*) AS total_messages,
                   MAX(gm.created_at) AS last_created_at
              FROM gpt_messages AS gm
         LEFT JOIN users AS u ON u.user_id = gm.user_id
          GROUP BY gm.user_id
          ORDER BY last_created_at DESC
             LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = cur.fetchall() or []

    return [
        {
            "user_id": row[0],
            "username": row[1] or "",
            "credits": normalize_credit_amount(row[2]),
            "banned": bool(row[3]),
            "total_messages": row[4] or 0,
            "last_created_at": row[5] or 0,
        }
        for row in rows
    ]


def set_ban(user_id, banned=True):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("UPDATE users SET banned=? WHERE user_id=?", (1 if banned else 0, user_id))
        con.commit()

def log_purchase(user_id, stars, credits, payload):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("""INSERT INTO purchases(user_id,stars,credits,payload,created_at)
                       VALUES(?,?,?,?,?)""", (user_id, stars, credits, payload, int(time.time())))
        con.commit()

def log_message(user_id, direction, text):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("""INSERT INTO messages(user_id,direction,text,created_at)
                       VALUES(?,?,?,?)""", (user_id, direction, text[:4000], int(time.time())))
        con.commit()


def log_image_generation(user_id: int, prompt: str, image_url: str) -> None:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """INSERT INTO image_generations(user_id, prompt, image_url, created_at)
                   VALUES(?,?,?,?)""",
            (user_id, (prompt or "")[:1000], image_url or "", int(time.time())),
        )
        con.commit()


def list_user_images(user_id: int):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """SELECT id, prompt, image_url, created_at
                   FROM image_generations
                   WHERE user_id=?
                   ORDER BY id ASC""",
            (user_id,),
        )
        rows = cur.fetchall() or []
    return [
        {
            "id": row[0],
            "prompt": row[1] or "",
            "image_url": row[2] or "",
            "created_at": row[3] or 0,
        }
        for row in rows
    ]


def count_users_with_images() -> int:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(DISTINCT user_id) FROM image_generations")
        result = cur.fetchone()
        return result[0] if result else 0


def count_users_with_gpt() -> int:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(DISTINCT user_id) FROM gpt_messages")
        result = cur.fetchone()
        return result[0] if result else 0


def count_users_by_lang():
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT COALESCE(NULLIF(lang, ''), 'fa') AS lang,
                   COUNT(*) AS total
              FROM users
          GROUP BY COALESCE(NULLIF(lang, ''), 'fa')
          ORDER BY total DESC
            """
        )
        rows = cur.fetchall() or []
    return [(row[0], row[1]) for row in rows]


def _guess_image_extension(url: str, content_type: str | None) -> str:
    parsed = urlparse(url or "")
    candidate = os.path.splitext(parsed.path)[1]
    if candidate and len(candidate) <= 5:
        return candidate
    if content_type:
        ext = mimetypes.guess_extension(content_type.split(";")[0].strip())
        if ext:
            return ext
    return ".jpg"


def export_user_images_zip(user_id: int, path: str | None = None):
    records = list_user_images(user_id)
    if not records:
        return None

    tmp_dir = DB_DIR if os.path.isdir(DB_DIR) else None
    if path is None:
        tmp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".zip",
            prefix=f"user_{user_id}_images_",
            dir=tmp_dir or None,
        )
        path = tmp_file.name
        tmp_file.close()
    else:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)

    downloaded = 0
    skipped = 0
    session = requests.Session()
    manifest_buffer = io.StringIO()
    writer = csv.writer(manifest_buffer)
    writer.writerow([
        "id",
        "prompt",
        "created_at",
        "created_at_iso",
        "image_url",
        "status",
        "filename",
    ])

    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for idx, item in enumerate(records, start=1):
            url = item.get("image_url") or ""
            status = "ok"
            filename = ""
            image_bytes = None
            content_type = ""
            if url:
                try:
                    response = session.get(url, timeout=30)
                    response.raise_for_status()
                    image_bytes = response.content
                    content_type = response.headers.get("Content-Type", "")
                except Exception:
                    status = "download_error"
            else:
                status = "missing_url"

            if image_bytes:
                ext = _guess_image_extension(url, content_type)
                filename = f"{idx:03d}_{item.get('id')}" + ext
                zf.writestr(filename, image_bytes)
                downloaded += 1
            else:
                skipped += 1

            created_at = int(item.get("created_at") or 0)
            try:
                created_iso = datetime.datetime.utcfromtimestamp(created_at).isoformat()
            except Exception:
                created_iso = ""

            writer.writerow([
                item.get("id"),
                item.get("prompt"),
                created_at,
                created_iso,
                url,
                status,
                filename,
            ])

        zf.writestr("manifest.csv", manifest_buffer.getvalue())

    return {
        "path": path,
        "total": len(records),
        "downloaded": downloaded,
        "skipped": skipped,
    }


def reset_user(user_id: int) -> bool:
    """Completely remove a user and all related data from the bot database."""
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT 1 FROM users WHERE user_id=?", (user_id,))
        if not cur.fetchone():
            return False

        cur.execute("DELETE FROM users WHERE user_id=?", (user_id,))
        cur.execute("DELETE FROM kv_state WHERE user_id=?", (user_id,))
        cur.execute("DELETE FROM messages WHERE user_id=?", (user_id,))
        cur.execute("DELETE FROM gpt_messages WHERE user_id=?", (user_id,))
        cur.execute(
            "DELETE FROM vexa_assistant_messages WHERE user_id=?",
            (user_id,),
        )
        cur.execute("DELETE FROM purchases WHERE user_id=?", (user_id,))
        cur.execute("DELETE FROM user_voices WHERE user_id=?", (user_id,))
        cur.execute("DELETE FROM image_generations WHERE user_id=?", (user_id,))
        con.commit()
    return True


def log_gpt_message(user_id: int, role: str, content: str) -> None:
    role_value = str(role or "assistant").strip() or "assistant"
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """INSERT INTO gpt_messages(user_id, role, content, created_at)
                   VALUES(?,?,?,?)""",
            (user_id, role_value, (content or "")[:6000], int(time.time())),
        )
        con.commit()


def get_recent_gpt_messages(user_id: int, limit: int) -> list[dict[str, str]]:
    lim = max(0, int(limit or 0))
    if lim == 0:
        return []
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """SELECT role, content
                   FROM gpt_messages
                   WHERE user_id=?
                   ORDER BY id DESC
                   LIMIT ?""",
            (user_id, lim),
        )
        rows = cur.fetchall() or []
    return [
        {"role": role, "content": content}
        for role, content in reversed(rows)
        if (role or "").strip() and (content or "").strip()
    ]


def clear_gpt_history(user_id: int) -> None:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("DELETE FROM gpt_messages WHERE user_id=?", (user_id,))
        con.commit()


def log_vexa_assistant_message(user_id: int, role: str, content: str) -> None:
    role_value = str(role or "assistant").strip() or "assistant"
    text = (content or "").strip()
    if not text:
        return

    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """INSERT INTO vexa_assistant_messages(user_id, role, content, created_at)
                   VALUES(?,?,?,?)""",
            (user_id, role_value, text[:6000], int(time.time())),
        )
        con.commit()


def get_recent_vexa_assistant_messages(user_id: int, limit: int) -> list[dict[str, str]]:
    try:
        lim = int(limit or 0)
    except (TypeError, ValueError):
        lim = 0
    lim = max(0, lim)
    if lim == 0:
        return []

    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """SELECT role, content
                   FROM vexa_assistant_messages
                   WHERE user_id=?
                   ORDER BY id DESC
                   LIMIT ?""",
            (user_id, lim),
        )
        rows = cur.fetchall() or []

    return [
        {"role": role, "content": content}
        for role, content in reversed(rows)
        if (role or "").strip() and (content or "").strip()
    ]


def clear_vexa_assistant_history(user_id: int) -> None:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "DELETE FROM vexa_assistant_messages WHERE user_id=?",
            (user_id,),
        )
        con.commit()

def export_users_csv(path="users.csv"):
    with closing(sqlite3.connect(DB_PATH)) as con, open(path,"w",newline="",encoding="utf-8") as f:
        cur = con.cursor()
        cur.execute("""SELECT user_id,username,first_name,joined_at,credits,ref_code,referred_by,banned,last_seen FROM users""")
        w = csv.writer(f)
        w.writerow(["user_id","username","first_name","joined_at","credits","ref_code","referred_by","banned","last_seen"])
        w.writerows(cur.fetchall())
    return path

def export_purchases_csv(path="purchases.csv"):
    with closing(sqlite3.connect(DB_PATH)) as con, open(path,"w",newline="",encoding="utf-8") as f:
        cur = con.cursor()
        cur.execute("""SELECT id,user_id,stars,credits,payload,created_at FROM purchases""")
        w = csv.writer(f)
        w.writerow(["id","user_id","stars","credits","payload","created_at"])
        w.writerows(cur.fetchall())
    return path

def export_messages_csv(path="messages.csv"):
    with closing(sqlite3.connect(DB_PATH)) as con, open(path,"w",newline="",encoding="utf-8") as f:
        cur = con.cursor()
        cur.execute("""SELECT id,user_id,direction,text,created_at FROM messages""")
        w = csv.writer(f)
        w.writerow(["id","user_id","direction","text","created_at"])
        w.writerows(cur.fetchall())
    return path

def count_active_users(hours=24):
    since = int(time.time()) - hours*3600
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE last_seen>=?", (since,))
        return cur.fetchone()[0]

def get_all_user_ids():
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT user_id FROM users")
        return [r[0] for r in cur.fetchall()]

def get_user_ids_by_lang(lang: str):
    lang_code = (lang or "fa").strip()
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT user_id FROM users WHERE COALESCE(NULLIF(lang, ''), 'fa')=?",
            (lang_code,),
        )
        return [r[0] for r in cur.fetchall()]

def get_all_user_credits():
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT user_id, credits FROM users ORDER BY user_id ASC")
        rows = cur.fetchall()
    return [
        (user_id, normalize_credit_amount(credits)) for user_id, credits in rows
    ]

def bulk_update_user_credits(updates):
    """updates should be iterable of (new_credits, user_id). Returns number of affected rows."""

    normalized_updates = [
        (normalize_credit_amount(credits), user_id) for credits, user_id in updates
    ]

    if not normalized_updates:
        return 0

    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.executemany("UPDATE users SET credits=? WHERE user_id=?", normalized_updates)
        con.commit()
        return len(normalized_updates)

def export_user_messages_csv(user_id: int, path=None):
    if path is None:
        path = f"user_{user_id}_messages.csv"
    with closing(sqlite3.connect(DB_PATH)) as con, open(path, "w", newline="", encoding="utf-8") as f:
        cur = con.cursor()
        cur.execute("""SELECT id, direction, text, created_at
                       FROM messages
                       WHERE user_id=?
                       ORDER BY id ASC""", (user_id,))
        import csv; w = csv.writer(f)
        w.writerow(["id","direction","text","created_at"])
        w.writerows(cur.fetchall())
    return path


def export_user_gpt_messages_csv(user_id: int, path: str | None = None):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """SELECT id, role, content, created_at
                   FROM gpt_messages
                  WHERE user_id=?
               ORDER BY id ASC""",
            (user_id,),
        )
        rows = cur.fetchall() or []

    if not rows:
        return None

    if path is None:
        tmp_dir = DB_DIR if os.path.isdir(DB_DIR) else None
        tmp = tempfile.NamedTemporaryFile(
            delete=False,
            prefix=f"user_{user_id}_gpt_",
            suffix=".csv",
            dir=tmp_dir or None,
        )
        path = tmp.name
        tmp.close()
    else:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "role", "content", "created_at", "created_at_iso"])
        for row_id, role, content, created_at in rows:
            created_at = int(created_at or 0)
            try:
                created_iso = datetime.datetime.utcfromtimestamp(created_at).isoformat()
            except Exception:
                created_iso = ""
            writer.writerow([row_id, role, content, created_at, created_iso])

    return path

# ... بقیه کد همون قبلی ...

def _migrate_users_table():
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("PRAGMA table_info(users)")
        cols = {r[1] for r in cur.fetchall()}
        if "banned" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN banned INTEGER DEFAULT 0")
        if "last_seen" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN last_seen INTEGER DEFAULT 0")
        if "referred_by" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN referred_by TEXT")
        if "lang" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'fa'")
        if "last_daily_reward" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN last_daily_reward INTEGER DEFAULT 0")
        if "onboarding_pending" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN onboarding_pending INTEGER DEFAULT 0")
        if "welcome_sent_at" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN welcome_sent_at INTEGER DEFAULT 0")
        if "daily_bonus_prompted_at" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN daily_bonus_prompted_at INTEGER DEFAULT 0")
        if "daily_bonus_unlocked_at" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN daily_bonus_unlocked_at INTEGER DEFAULT 0")
        if "daily_bonus_reminded_at" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN daily_bonus_reminded_at INTEGER DEFAULT 0")
        if "low_credit_prompted_at" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN low_credit_prompted_at INTEGER DEFAULT 0")
        if "tts_creator_prompted_at" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN tts_creator_prompted_at INTEGER DEFAULT 0")
        if "last_main_menu_id" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN last_main_menu_id INTEGER DEFAULT 0")
        con.commit()

def get_or_create_user(u):
    is_new = False
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT user_id FROM users WHERE user_id=?", (u.id,))
        row = cur.fetchone()
        if not row:
            free_credit = int(get_setting("FREE_CREDIT", "80") or 80)
            ref_code = str(u.id)
            cur.execute(
                """INSERT INTO users(
                    user_id,
                    username,
                    first_name,
                    joined_at,
                    credits,
                    ref_code,
                    last_seen,
                    lang,
                    onboarding_pending
                )
                VALUES(?,?,?,?,?,?,?,?,?)""",
                (
                    u.id,
                    (u.username or ""),
                    (u.first_name or ""),
                    int(time.time()),
                    free_credit,
                    ref_code,
                    int(time.time()),
                    "",
                    1,
                ),
            )
            con.commit()
            is_new = True
        else:
            cur.execute(
                "UPDATE users SET username=?, first_name=? WHERE user_id=?",
                (u.username or "", u.first_name or "", u.id),
            )
            con.commit()
    user = get_user(u.id)
    if user and is_new:
        user["is_new"] = True
    return user

def get_user(user_id):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT
                user_id,
                username,
                first_name,
                joined_at,
                credits,
                ref_code,
                referred_by,
                banned,
                last_seen,
                lang,
                last_daily_reward,
                onboarding_pending,
                welcome_sent_at,
                daily_bonus_prompted_at,
                daily_bonus_unlocked_at,
                daily_bonus_reminded_at,
                low_credit_prompted_at,
                tts_creator_prompted_at,
                last_main_menu_id
            FROM users WHERE user_id=?
            """,
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        keys = [
            "user_id",
            "username",
            "first_name",
            "joined_at",
            "credits",
            "ref_code",
            "referred_by",
            "banned",
            "last_seen",
            "lang",
            "last_daily_reward",
            "onboarding_pending",
            "welcome_sent_at",
            "daily_bonus_prompted_at",
            "daily_bonus_unlocked_at",
            "daily_bonus_reminded_at",
            "low_credit_prompted_at",
            "tts_creator_prompted_at",
            "last_main_menu_id",
        ]
        return _normalize_user_dict(keys, row)


def get_last_daily_reward(user_id: int) -> int:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT last_daily_reward FROM users WHERE user_id=?",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return 0
        value = row[0]
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0


def get_welcome_sent_at(user_id: int) -> int:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT welcome_sent_at FROM users WHERE user_id=?",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return 0
        value = row[0]
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0


def set_welcome_sent_at(user_id: int, timestamp: int | None = None) -> None:
    ts = int(timestamp or time.time())
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "UPDATE users SET welcome_sent_at=? WHERE user_id=?",
            (ts, user_id),
        )
        con.commit()


def set_onboarding_pending(user_id: int, pending: bool) -> None:
    value = 1 if pending else 0
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "UPDATE users SET onboarding_pending=? WHERE user_id=?",
            (value, user_id),
        )
        con.commit()


def get_daily_bonus_prompted_at(user_id: int) -> int:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT daily_bonus_prompted_at FROM users WHERE user_id=?",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return 0
        value = row[0]
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0


def set_daily_bonus_prompted_at(user_id: int, timestamp: int | None = None) -> None:
    ts = int(timestamp or time.time())
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "UPDATE users SET daily_bonus_prompted_at=? WHERE user_id=?",
            (ts, user_id),
        )
        con.commit()


def get_daily_bonus_unlocked_at(user_id: int) -> int:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT daily_bonus_unlocked_at FROM users WHERE user_id=?",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return 0
        value = row[0]
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0


def set_daily_bonus_unlocked_at(user_id: int, timestamp: int | None = None) -> None:
    ts = int(timestamp or time.time())
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "UPDATE users SET daily_bonus_unlocked_at=? WHERE user_id=?",
            (ts, user_id),
        )
        con.commit()


def get_daily_bonus_reminded_at(user_id: int) -> int:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT daily_bonus_reminded_at FROM users WHERE user_id=?",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return 0
        value = row[0]
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0


def set_daily_bonus_reminded_at(user_id: int, timestamp: int | None = None) -> None:
    ts = int(timestamp or time.time())
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "UPDATE users SET daily_bonus_reminded_at=? WHERE user_id=?",
            (ts, user_id),
        )
        con.commit()

def get_low_credit_prompted_at(user_id: int) -> int:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT low_credit_prompted_at FROM users WHERE user_id=?",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return 0
        value = row[0]
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0


def set_low_credit_prompted_at(user_id: int, timestamp: int | None = None) -> None:
    ts = int(time.time()) if timestamp is None else int(timestamp)
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "UPDATE users SET low_credit_prompted_at=? WHERE user_id=?",
            (ts, user_id),
        )
        con.commit()


def get_tts_creator_prompted_at(user_id: int) -> int:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT tts_creator_prompted_at FROM users WHERE user_id=?",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return 0
        value = row[0]
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0


def set_tts_creator_prompted_at(user_id: int, timestamp: int | None = None) -> None:
    ts = int(time.time()) if timestamp is None else int(timestamp)
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "UPDATE users SET tts_creator_prompted_at=? WHERE user_id=?",
            (ts, user_id),
        )
        con.commit()


def get_last_main_menu_id(user_id: int) -> int:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT last_main_menu_id FROM users WHERE user_id=?",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return 0
        value = row[0]
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0


def set_last_main_menu_id(user_id: int, message_id: int | None) -> None:
    value = int(message_id or 0)
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "UPDATE users SET last_main_menu_id=? WHERE user_id=?",
            (value, user_id),
        )
        con.commit()


def set_last_daily_reward(user_id: int, timestamp: int | None = None) -> None:
    ts = int(timestamp or time.time())
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "UPDATE users SET last_daily_reward=? WHERE user_id=?",
            (ts, user_id),
        )
        con.commit()


def count_daily_reward_users() -> int:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM users WHERE IFNULL(last_daily_reward, 0) > 0"
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0


def count_daily_reward_users_since(*, seconds: float | None = None, hours: float | None = None, days: float | None = None) -> int:
    total_seconds = 0.0
    if seconds is not None:
        try:
            total_seconds += float(seconds)
        except (TypeError, ValueError):
            total_seconds += 0.0
    if hours is not None:
        try:
            total_seconds += float(hours) * 3600.0
        except (TypeError, ValueError):
            total_seconds += 0.0
    if days is not None:
        try:
            total_seconds += float(days) * 86400.0
        except (TypeError, ValueError):
            total_seconds += 0.0

    if total_seconds <= 0:
        return count_daily_reward_users()

    threshold = int(time.time() - total_seconds)
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM users WHERE IFNULL(last_daily_reward, 0) >= ?",
            (threshold,),
        )
        row = cur.fetchone()
        return int(row[0]) if row else 0


def list_daily_reward_users(limit: int = 10, offset: int = 0):
    limit = max(0, int(limit))
    offset = max(0, int(offset))
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """
            SELECT
                user_id,
                username,
                credits,
                banned,
                last_daily_reward
            FROM users
            WHERE IFNULL(last_daily_reward, 0) > 0
            ORDER BY last_daily_reward DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
        rows = cur.fetchall() or []
    result = []
    for row in rows:
        result.append(
            {
                "user_id": row[0],
                "username": row[1],
                "credits": row[2],
                "banned": bool(row[3]),
                "last_daily_reward": row[4],
            }
        )
    return result


def set_user_lang(user_id:int, lang:str):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, user_id))
        con.commit()

def get_user_lang(user_id:int, default="fa"):
    u = get_user(user_id)
    return (u and (u.get("lang") or default)) or default

# --- migrations: messages.kind (برای تمایز TTS)
def _migrate_messages_kind():
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("PRAGMA table_info(messages)")
        cols = {r[1] for r in cur.fetchall()}
        if "kind" not in cols:
            try:
                cur.execute("ALTER TABLE messages ADD COLUMN kind TEXT DEFAULT ''")
            except Exception:
                pass
        con.commit()

# در init_db() بعد از ساخت جداول، اینو هم صدا بزن:
# _migrate_messages_kind()

def log_tts_request(user_id: int, text: str):
    """ثبت متن ارسالی کاربر برای TTS (فقط ورودی کاربر)"""
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("""INSERT INTO messages(user_id, direction, text, created_at, kind)
                       VALUES(?,?,?,?,?)""",
                    (user_id, "in", text, int(time.time()), "tts_in"))
        con.commit()


def count_tts_requests(user_id: int) -> int:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM messages WHERE user_id=? AND kind='tts_in'",
            (user_id,),
        )
        row = cur.fetchone()
        try:
            return int(row[0] if row else 0)
        except (TypeError, ValueError):
            return 0

def export_user_tts_csv(user_id: int, path=None):
    """خروجی فقط متن‌های TTS کاربر (چیزی که برای تبدیل فرستاده)"""
    if path is None:
        path = f"user_{user_id}_tts_texts.csv"
    with closing(sqlite3.connect(DB_PATH)) as con, open(path, "w", newline="", encoding="utf-8") as f:
        cur = con.cursor()
        cur.execute("""SELECT id, text, created_at
                       FROM messages
                       WHERE user_id=? AND kind='tts_in'
                       ORDER BY id ASC""", (user_id,))
        import csv; w = csv.writer(f)
        w.writerow(["id","text","created_at"])
        w.writerows(cur.fetchall())
    return path
