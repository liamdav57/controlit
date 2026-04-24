# ============================================================
#  my_connector.py - ניהול מסד הנתונים
#  משתמש ב-SQLite — אין צורך בהתקנת MySQL
#  הקובץ users.db נוצר אוטומטית ליד ה-exe
# ============================================================

import sqlite3
import bcrypt
import os
import sys


def _db_path():
    """מחזיר את הנתיב לקובץ users.db ליד ה-exe או הסקריפט"""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "users.db")


def get_connection():
    """פותח חיבור ל-SQLite ומחזיר אותו"""
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    """יוצר את הטבלאות אם לא קיימות"""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            username  TEXT UNIQUE NOT NULL,
            password  TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL,
            is_active  BOOLEAN DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_machines (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            username   TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS saved_targets (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_username TEXT NOT NULL,
            computer_name  TEXT NOT NULL,
            ip_address     TEXT NOT NULL,
            mac_address    TEXT DEFAULT NULL,
            saved_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("Database ready:", _db_path())


def hash_password(password: str) -> bytes:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))


def verify_password(plain, hashed) -> bool:
    try:
        if isinstance(hashed, str):
            hashed = hashed.encode('utf-8')
        return bcrypt.checkpw(plain.encode('utf-8'), hashed)
    except Exception:
        return False


def user_exists(username):
    try:
        conn = get_connection()
        row = conn.execute("SELECT COUNT(*) FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        return row[0] > 0
    except Exception:
        return False


def register(username, password):
    """רושם משתמש חדש עם סיסמה מוצפנת"""
    try:
        if user_exists(username):
            return {'success': False, 'message': 'User exists'}
        conn = get_connection()
        hashed = hash_password(password).decode('utf-8')
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        conn.commit()
        conn.close()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def login(username, password):
    """מבצע לוגין ומחזיר success/failure"""
    try:
        conn = get_connection()
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if row and verify_password(password, row['password']):
            conn2 = get_connection()
            conn2.execute(
                "UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE username=?",
                (username,)
            )
            conn2.commit()
            conn2.close()
            return {'success': True, 'username': username}
        return {'success': False, 'message': 'Invalid credentials'}
    except Exception as e:
        return {'success': False, 'message': str(e)}


def save_user_machine(username):
    """שומר את ה-IP של המחשב שממנו המשתמש התחבר"""
    try:
        import socket
        ip = socket.gethostbyname(socket.gethostname())
        conn = get_connection()
        conn.execute(
            "INSERT INTO user_machines (username, ip_address) VALUES (?, ?)",
            (username, ip)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print("Log error:", e)


def save_target_computer(owner, name, ip, mac=""):
    """שומר או מעדכן מחשב מרוחק"""
    try:
        conn = get_connection()
        row = conn.execute(
            "SELECT id FROM saved_targets WHERE owner_username=? AND ip_address=?",
            (owner, ip)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE saved_targets SET computer_name=?, mac_address=? WHERE id=?",
                (name, mac, row[0])
            )
        else:
            conn.execute(
                "INSERT INTO saved_targets (owner_username, computer_name, ip_address, mac_address) VALUES (?, ?, ?, ?)",
                (owner, name, ip, mac)
            )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Save error: {e}")
        return False


def get_saved_computers(owner):
    """מחזיר רשימה של כל המחשבים השמורים של משתמש"""
    try:
        conn = get_connection()
        rows = conn.execute(
            "SELECT computer_name, ip_address, mac_address FROM saved_targets WHERE owner_username=?",
            (owner,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


if __name__ == "__main__":
    create_tables()
