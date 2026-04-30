import mysql.connector
import hashlib
import os
import sys

def get_connection():
    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='Liamfort5',
        database='users_db'
    )
    return conn

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL,
            is_active BOOLEAN DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_machines (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            ip_address VARCHAR(45) NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS saved_targets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            owner_username VARCHAR(255) NOT NULL,
            computer_name VARCHAR(255) NOT NULL,
            ip_address VARCHAR(45) NOT NULL,
            mac_address VARCHAR(17) DEFAULT NULL,
            saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("Database ready: users_db")

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
        cursor.execute("SELECT COUNT(*) FROM users WHERE username=%s", (username,))
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
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
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
        cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
        row = cursor.fetchone()

        if row and verify_password(password, row[2]):
            cursor.execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE username=%s", (username,))
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
        cursor.execute("INSERT INTO user_machines (username, ip_address) VALUES (%s, %s)", (username, ip))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Log error:", e)

def save_target_computer(owner, name, ip, mac=""):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM saved_targets WHERE owner_username=%s AND ip_address=%s", (owner, ip))
        row = cursor.fetchone()

        if row:
            cursor.execute("UPDATE saved_targets SET computer_name=%s, mac_address=%s WHERE id=%s", (name, mac, row[0]))
        else:
            cursor.execute("INSERT INTO saved_targets (owner_username, computer_name, ip_address, mac_address) VALUES (%s, %s, %s, %s)", (owner, name, ip, mac))

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
        cursor.execute("SELECT computer_name, ip_address, mac_address FROM saved_targets WHERE owner_username=%s", (owner,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        result = []
        for row in rows:
            result.append({
                'computer_name': row[0],
                'ip_address': row[1],
                'mac_address': row[2]
            })
        return result
    except Exception:
        return []

if __name__ == "__main__":
    create_tables()
