import hashlib
import os
import json
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

# ייבוא הדרייבר של MySQL — אם לא מותקן, המערכת לא קורסת אלא עוברת למצב לא-מקוון
try:
    import mysql.connector
    _MYSQL_DRIVER = True
except ImportError:
    mysql = None
    _MYSQL_DRIVER = False

# ── הגדרות חיבור ל-MySQL (קוראות מ-config.py / .env) ──────────────────────
DB_CONFIG = {
    'host':     DB_HOST,
    'user':     DB_USER,
    'password': DB_PASSWORD,
    'database': DB_NAME,
    'connection_timeout': 4,   # נכשל מהר אם אין שרת — שלא יתקע את הממשק
}

# ══════════════════════════════════════════════════════════════════════════
#  חיבור
# ══════════════════════════════════════════════════════════════════════════

def get_connection():
    if not _MYSQL_DRIVER:
        raise RuntimeError("mysql.connector not installed - offline mode")
    return mysql.connector.connect(**DB_CONFIG)


def db_available():
    """בדיקה מהירה אם שרת MySQL זמין — קובע מצב מקוון/לא-מקוון."""
    if not _MYSQL_DRIVER:
        return False
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'], user=DB_CONFIG['user'],
            password=DB_CONFIG['password'], connection_timeout=3)
        conn.close()
        return True
    except Exception:
        return False


# ── חשבונות מקומיים (כשאין MySQL) — קובץ JSON פשוט, לא מסד נתונים ──
_LOCAL_FILE = os.path.join(os.path.expanduser("~"), "controlit_accounts.json")
_backend = None   # None=לא נקבע, True=מקומי, False=MySQL

def _use_local():
    """נקבע פעם אחת: אם אין שרת MySQL — עובדים מול קובץ מקומי."""
    global _backend
    if _backend is None:
        _backend = not db_available()
    return _backend

def _local_load():
    try:
        with open(_LOCAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _local_save(data):
    with open(_LOCAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)


# ══════════════════════════════════════════════════════════════════════════
#  יצירת טבלאות (אם לא קיימות)
# ══════════════════════════════════════════════════════════════════════════

def create_tables():
    if not _MYSQL_DRIVER or _use_local():
        return   # אין MySQL — משתמשים בקובץ חשבונות מקומי, אין מה ליצור
    # צור את ה-database אם לא קיים
    temp = mysql.connector.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        connection_timeout=4,
    )
    cur = temp.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
    cur.close()
    temp.close()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id   INT AUTO_INCREMENT PRIMARY KEY,
            username  VARCHAR(100) UNIQUE NOT NULL,
            password  VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL,
            is_active  TINYINT DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_machines (
            id         INT AUTO_INCREMENT PRIMARY KEY,
            username   VARCHAR(100) NOT NULL,
            ip_address VARCHAR(45)  NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_targets (
            id              INT AUTO_INCREMENT PRIMARY KEY,
            owner_username  VARCHAR(100) NOT NULL,
            computer_name   VARCHAR(100) NOT NULL,
            ip_address      VARCHAR(45)  NOT NULL,
            mac_address     VARCHAR(20)  DEFAULT NULL,
            saved_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


# ══════════════════════════════════════════════════════════════════════════
#  הצפנת סיסמאות
# ══════════════════════════════════════════════════════════════════════════

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(plain, hashed) -> bool:
    try:
        return hashlib.sha256(plain.encode('utf-8')).hexdigest() == hashed
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════
#  בדיקה אם משתמש קיים
# ══════════════════════════════════════════════════════════════════════════

def user_exists(username):
    if _use_local():
        return username in _local_load()
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username=%s", (username,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] > 0
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════
#  הרשמה
# ══════════════════════════════════════════════════════════════════════════

def register(username, password):
    try:
        if _use_local():
            accts = _local_load()
            if username in accts:
                return {'success': False, 'message': 'User exists'}
            accts[username] = hash_password(password)
            _local_save(accts)
            return {'success': True}
        if user_exists(username):
            return {'success': False, 'message': 'User exists'}
        conn = get_connection()
        cursor = conn.cursor()
        hashed = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password) VALUES (%s, %s)",
            (username, hashed)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'message': str(e)}


# ══════════════════════════════════════════════════════════════════════════
#  כניסה
# ══════════════════════════════════════════════════════════════════════════

def login(username, password):
    try:
        if _use_local():
            stored = _local_load().get(username)
            if stored and verify_password(password, stored):
                return {'success': True, 'username': username}
            return {'success': False, 'message': 'Invalid credentials'}
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        row = cursor.fetchone()

        if row and verify_password(password, row['password']):
            cursor.execute(
                "UPDATE users SET last_login=NOW() WHERE username=%s",
                (username,)
            )
            conn.commit()
            cursor.close()
            conn.close()
            return {'success': True, 'username': username}

        cursor.close()
        conn.close()
        return {'success': False, 'message': 'Invalid credentials'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


# ══════════════════════════════════════════════════════════════════════════
#  רישום מכונה
# ══════════════════════════════════════════════════════════════════════════

def save_user_machine(username):
    if _use_local():
        return
    try:
        import socket
        ip = socket.gethostbyname(socket.gethostname())
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_machines (username, ip_address) VALUES (%s, %s)",
            (username, ip)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Log error:", e)


# ══════════════════════════════════════════════════════════════════════════
#  שמירת מחשב יעד
# ══════════════════════════════════════════════════════════════════════════

def save_target_computer(owner, name, ip, mac=""):
    if _use_local():
        return True
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM saved_targets WHERE owner_username=%s AND ip_address=%s",
            (owner, ip)
        )
        row = cursor.fetchone()

        if row:
            cursor.execute(
                "UPDATE saved_targets SET computer_name=%s, mac_address=%s WHERE id=%s",
                (name, mac, row[0])
            )
        else:
            cursor.execute(
                "INSERT INTO saved_targets (owner_username, computer_name, ip_address, mac_address) "
                "VALUES (%s, %s, %s, %s)",
                (owner, name, ip, mac)
            )

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Save error: {e}")
        return False


# ══════════════════════════════════════════════════════════════════════════
#  קבלת מחשבים שמורים
# ══════════════════════════════════════════════════════════════════════════

def get_saved_computers(owner):
    if _use_local():
        return []
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT computer_name, ip_address, mac_address "
            "FROM saved_targets WHERE owner_username=%s",
            (owner,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{'computer_name': r[0], 'ip_address': r[1], 'mac_address': r[2]} for r in rows]
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════════════
#  הרצה ישירה – יוצר טבלאות
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    create_tables()
    print("Tables created successfully in MySQL database:", DB_CONFIG['database'])
