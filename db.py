import sqlite3, time, datetime, csv
from contextlib import closing
import os, sqlite3
# مسیر DB روی دیسکِ Render (Mount path شما: /var/data)
DB_DIR = os.getenv("DB_DIR", "/data")
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "bot.db")

print("DB_PATH =>", DB_PATH, flush=True)  # برای اطمینان در لاگ

con = sqlite3.connect(DB_PATH, check_same_thread=False)
cur = con.cursor()

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
        con.commit()
    _migrate_users_table()
    ensure_default_settings()

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
        con.commit()

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

def get_or_create_user(u):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT user_id FROM users WHERE user_id=?", (u.id,))
        row = cur.fetchone()
        if not row:
            # اعمال FREE_CREDIT از settings فقط برای کاربر جدید
            free_credit = int(get_setting("FREE_CREDIT","80") or 80)
            ref_code = str(u.id)
            cur.execute("""INSERT INTO users(user_id,username,first_name,joined_at,credits,ref_code,last_seen)
                           VALUES(?,?,?,?,?,?,?)""",
                        (u.id, (u.username or ""), (u.first_name or ""),
                         int(time.time()), free_credit, ref_code, int(time.time())))
            con.commit()
        else:
            # هم‌زمان یوزرنیم را به‌روز نگه داریم
            cur.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?",
                        (u.username or "", u.first_name or "", u.id))
            con.commit()
    return get_user(u.id)

def get_user(user_id):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("""SELECT user_id,username,first_name,joined_at,credits,ref_code,referred_by,banned,last_seen
                       FROM users WHERE user_id=?""", (user_id,))
        row = cur.fetchone()
        if not row: return None
        keys = ["user_id","username","first_name","joined_at","credits","ref_code","referred_by","banned","last_seen"]
        return dict(zip(keys,row))

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
        con.commit()

def get_or_create_user(u):
    with closing(sqlite3.connect(DB_PATH)) as con:
        cur = con.cursor()
        cur.execute("SELECT user_id FROM users WHERE user_id=?", (u.id,))
        row = cur.fetchone()
        if not row:
            free_credit = int(get_setting("FREE_CREDIT","80") or 80)
            ref_code = str(u.id)
            cur.execute("""INSERT INTO users(user_id,username,first_name,joined_at,credits,ref_code,last_seen,lang)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (u.id, (u.username or ""), (u.first_name or ""),
                         int(time.time()), free_credit, ref_code, int(time.time()), "fa"))
            con.commit()
        else:
            cur.execute("UPDATE users SET username=?, first_name=? WHERE user_id=?",
                        (u.username or "", u.first_name or "", u.id))
            con.commit()
    return get_user(u.id)

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
