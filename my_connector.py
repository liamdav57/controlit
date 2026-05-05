import sqlite3
import hashlib
import os
import sys

def get_db_path():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'users.db')

def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL,
            is_active INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_username TEXT NOT NULL,
            computer_name TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            mac_address TEXT DEFAULT NULL,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_password(plain, hashed) -> bool:
    try:
        return hashlib.sha256(plain.encode('utf-8')).hexdigest() == hashed
    except Exception:
        return False

def user_exists(username):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username=?", (username,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] > 0
    except Exception:
        return False

def register(username, password):
    try:
        if user_exists(username):
            return {'success': False, 'message': 'User exists'}
        conn = get_connection()
        cursor = conn.cursor()
        hashed = hash_password(password)
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
        conn.commit()
        cursor.close()
        conn.close()
        return {'success': True}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def login(username, password):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username=?", (username,))
        row = cursor.fetchone()

        if row and verify_password(password, row['password']):
            cursor.execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE username=?", (username,))
            conn.commit()
            cursor.close()
            conn.close()
            return {'success': True, 'username': username}

        cursor.close()
        conn.close()
        return {'success': False, 'message': 'Invalid credentials'}
    except Exception as e:
        return {'success': False, 'message': str(e)}

def save_user_machine(username):
    try:
        import socket
        ip = socket.gethostbyname(socket.gethostname())
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO user_machines (username, ip_address) VALUES (?, ?)", (username, ip))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Log error:", e)

def save_target_computer(owner, name, ip, mac=""):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM saved_targets WHERE owner_username=? AND ip_address=?", (owner, ip))
        row = cursor.fetchone()

        if row:
            cursor.execute("UPDATE saved_targets SET computer_name=?, mac_address=? WHERE id=?", (name, mac, row[0]))
        else:
            cursor.execute("INSERT INTO saved_targets (owner_username, computer_name, ip_address, mac_address) VALUES (?, ?, ?, ?)", (owner, name, ip, mac))

        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Save error: {e}")
        return False

def get_saved_computers(owner):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT computer_name, ip_address, mac_address FROM saved_targets WHERE owner_username=?", (owner,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{'computer_name': r[0], 'ip_address': r[1], 'mac_address': r[2]} for r in rows]
    except Exception:
        return []

if __name__ == "__main__":
    create_tables()
