import base64
import csv
import datetime
import hashlib
import hmac
import io
import mimetypes
import os
import secrets
import sqlite3
import tempfile
import time
import zipfile
from contextlib import closing
from urllib.parse import urlparse

import requests
from cryptography.fernet import Fernet, InvalidToken

from config import API_CREDIT_COST, API_KEY_ENCRYPTION_SECRET

DB_DIR = os. getenv ("DB_DIR", "/data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "bot.db")
_API_KEY_SECRET_FALLBACK_PATH = os.path.join(DB_DIR, "api_key_secret.key")

print("DB_PATH =>", DB_PATH, flush=True)

con = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = con.cursor()

_API_KEY_HEADER_PREFIX = "VX"
_API_KEY_VERSION = "1"
_FERNET_KEY_CACHE: Fernet | None = None


def _load_or_create_encryption_secret() -> str:
    """Return a stable encryption secret stored alongside the database."""

    try:
        with open(_API_KEY_SECRET_FALLBACK_PATH, "r", encoding="utf-8") as fh:
            secret = fh.read().strip()
            if secret:
                return secret
    except FileNotFoundError:
        pass

    secret = secrets.token_urlsafe(64)
    tmp_path = f"{_API_KEY_SECRET_FALLBACK_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        fh.write(secret)
    os.replace(tmp_path, _API_KEY_SECRET_FALLBACK_PATH)
    try:
        os.chmod(_API_KEY_SECRET_FALLBACK_PATH, 0o600)
    except OSError:
        # Permission errors are expected on some platforms (e.g. Windows).
        pass
    return secret


def _get_api_key_cipher() -> Fernet:
    global _FERNET_KEY_CACHE
    if _FERNET_KEY_CACHE is not None:
        return _FERNET_KEY_CACHE
    secret = (API_KEY_ENCRYPTION_SECRET or "").strip()
    if not secret:
        secret = _load_or_create_encryption_secret()
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    _FERNET_KEY_CACHE = Fernet(key)
    return _FERNET_KEY_CACHE


def _encrypt_api_key(value: str) -> str:
    cipher = _get_api_key_cipher()
    token = cipher.encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def _decrypt_api_key(token: str) -> str:
    cipher = _get_api_key_cipher()
    try:
        value = cipher.decrypt(token.encode("utf-8"))
    except InvalidToken as exc:
        raise RuntimeError("Stored API key could not be decrypted") from exc
    return value.decode("utf-8")


def _generate_api_key_material() -> tuple[str, str, str]:
    key_id = secrets.token_hex(8)
    secret = secrets.token_urlsafe(32)
    api_key = f"{_API_KEY_HEADER_PREFIX}{_API_KEY_VERSION}-{key_id}.{secret}"
    return key_id, secret, api_key


def _hash_secret(secret: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt,
        200_000,
    )
    return base64.urlsafe_b64encode(digest).decode("utf-8")


def _generate_and_store_api_key(user_id: int, allow_existing: bool) -> str:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            "SELECT api_key_id, api_key_encrypted, api_key_revoked_at FROM users WHERE user_id=?",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            raise ValueError(f"User {user_id} does not exist")
        existing_id, encrypted_value, revoked_at = row
        if allow_existing and existing_id and encrypted_value and not revoked_at:
            return _decrypt_api_key(encrypted_value)

        # Ensure uniqueness of key_id even though collisions are extremely unlikely
        while True:
            key_id, secret, api_key = _generate_api_key_material()
            cur.execute("SELECT 1 FROM users WHERE api_key_id=?", (key_id,))
            if not cur.fetchone():
                break

        salt = secrets.token_bytes(16)
        secret_hash = _hash_secret(secret, salt)
        encrypted_value = _encrypt_api_key(api_key)
        now = int(time.time())
        cur.execute(
            """UPDATE users
                   SET api_key_id=?,
                       api_key_secret_hash=?,
                       api_key_salt=?,
                       api_key_encrypted=?,
                       api_key_created_at=?,
                       api_key_revoked_at=NULL
                 WHERE user_id=?""",
            (
                key_id,
                secret_hash,
                base64.urlsafe_b64encode(salt).decode("utf-8"),
                encrypted_value,
                now,
                user_id,
            ),
        )
        con.commit()
    return api_key


def ensure_user_api_key(user_id: int) -> str:
    try:
        return _generate_and_store_api_key(user_id, allow_existing=True)
    except RuntimeError:
        # If the encryption secret rotated we won't be able to decrypt the
        # stored key anymore. Fall back to issuing a fresh key so the user
        # can keep using the API without manual intervention.
        print(
            f"[API] Stored key for user {user_id} could not be decrypted; "
            "issuing a replacement.",
            flush=True,
        )
        return _generate_and_store_api_key(user_id, allow_existing=False)


def regenerate_user_api_key(user_id: int) -> str:
    return _generate_and_store_api_key(user_id, allow_existing=False)


def revoke_user_api_key(user_id: int) -> None:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """UPDATE users
                   SET api_key_id=NULL,
                       api_key_secret_hash=NULL,
                       api_key_salt=NULL,
                       api_key_encrypted=NULL,
                       api_key_revoked_at=?
                 WHERE user_id=?""",
            (
                int(time.time()),
                user_id,
            ),
        )
        con.commit()
        if cur.rowcount == 0:
            raise ValueError(f"User {user_id} does not exist")


def get_user_api_key(user_id: int, reveal: bool = False) -> dict | None:
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """SELECT api_key_id, api_key_encrypted, api_key_created_at,
                          api_key_last_used_at, api_key_revoked_at
                   FROM users WHERE user_id=?""",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
    key_id, encrypted_value, created_at, last_used_at, revoked_at = row
    api_key_value = None
    if reveal and encrypted_value and not revoked_at:
        api_key_value = _decrypt_api_key(encrypted_value)
    masked_value = None
    if encrypted_value and not revoked_at:
        try:
            full_value = _decrypt_api_key(encrypted_value)
            masked_value = f"{full_value[:8]}…{full_value[-4:]}"
        except Exception:
            masked_value = None
    return {
        "user_id": user_id,
        "key_id": key_id,
        "masked_key": masked_value,
        "api_key": api_key_value,
        "created_at": created_at,
        "last_used_at": last_used_at,
        "revoked_at": revoked_at,
    }


def verify_api_key(api_key: str) -> dict | None:
    if not api_key or "." not in api_key or "-" not in api_key:
        return None
    try:
        prefix, secret = api_key.split(".", 1)
        if not prefix.startswith(f"{_API_KEY_HEADER_PREFIX}{_API_KEY_VERSION}-"):
            return None
        _, key_id = prefix.split("-", 1)
    except ValueError:
        return None
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """SELECT user_id, username, first_name, credits,
                          api_key_secret_hash, api_key_salt, api_key_revoked_at
                   FROM users WHERE api_key_id=?""",
            (key_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        user_id, username, first_name, credits, secret_hash, salt, revoked_at = row
        if revoked_at:
            return None
        if not secret_hash or not salt:
            return None
        try:
            salt_bytes = base64.urlsafe_b64decode(salt.encode("utf-8"))
        except Exception:
            return None
        candidate = _hash_secret(secret, salt_bytes)
        if not hmac.compare_digest(candidate, secret_hash):
            return None
        return {
            "user_id": user_id,
            "username": username,
            "first_name": first_name,
            "credits": credits,
        }


def consume_api_credit(user_id: int, cost: int | None = None) -> bool:
    if cost is None:
        cost = API_CREDIT_COST
    cost = max(1, int(cost))
    now = int(time.time())
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute(
            """UPDATE users
                   SET credits = credits - ?, api_key_last_used_at=?
                 WHERE user_id=? AND credits >= ?""",
            (cost, now, user_id, cost),
        )
        con.commit()
        return cur.rowcount > 0

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
        cur.execute("""CREATE TABLE IF NOT EXISTS gpt_messages(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )""")
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
        "IG_URL": ""
    }
    for k,v in defaults.items():
        if get_setting(k) is None:
            set_setting(k,v)

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
        if not row: return None
        keys = ["user_id","username","first_name","joined_at","credits","ref_code","referred_by","banned","last_seen"]
        return dict(zip(keys,row))

def add_credits(user_id, amount):
    if amount == 0: return
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("UPDATE users SET credits = credits + ? WHERE user_id=?", (amount, user_id))
        con.commit()

def deduct_credits(user_id, amount):
    if amount <= 0: return True
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT credits FROM users WHERE user_id=?", (user_id,))
        r = cur.fetchone()
        if not r or r[0] < amount: return False
        cur.execute("UPDATE users SET credits = credits - ? WHERE user_id=?", (amount, user_id))
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
        return cur.fetchall()


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
            "credits": row[2] or 0,
            "banned": bool(row[3]),
            "total_images": row[4] or 0,
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

def get_all_user_credits():
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT user_id, credits FROM users ORDER BY user_id ASC")
        return cur.fetchall()

def bulk_update_user_credits(updates):
    """updates should be iterable of (new_credits, user_id). Returns number of affected rows."""
    updates = list(updates)
    if not updates:
        return 0
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.executemany("UPDATE users SET credits=? WHERE user_id=?", updates)
        con.commit()
        return len(updates)

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
        if "api_key_id" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN api_key_id TEXT")
        if "api_key_secret_hash" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN api_key_secret_hash TEXT")
        if "api_key_salt" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN api_key_salt TEXT")
        if "api_key_encrypted" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN api_key_encrypted TEXT")
        if "api_key_created_at" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN api_key_created_at INTEGER")
        if "api_key_last_used_at" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN api_key_last_used_at INTEGER")
        if "api_key_revoked_at" not in cols:
            cur.execute("ALTER TABLE users ADD COLUMN api_key_revoked_at INTEGER")
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
                """INSERT INTO users(user_id,username,first_name,joined_at,credits,ref_code,last_seen,lang)
                           VALUES(?,?,?,?,?,?,?,?)""",
                (
                    u.id,
                    (u.username or ""),
                    (u.first_name or ""),
                    int(time.time()),
                    free_credit,
                    ref_code,
                    int(time.time()),
                    "",
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
        try:
            ensure_user_api_key(u.id)
        except Exception as exc:
            print(f"[API-KEY] Failed to generate API key for user {u.id}: {exc}")
    return user

def get_user(user_id):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("""SELECT user_id,username,first_name,joined_at,credits,ref_code,referred_by,banned,last_seen,lang
                       FROM users WHERE user_id=?""", (user_id,))
        row = cur.fetchone()
        if not row: return None
        keys = ["user_id","username","first_name","joined_at","credits","ref_code","referred_by","banned","last_seen","lang"]
        return dict(zip(keys,row))

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
