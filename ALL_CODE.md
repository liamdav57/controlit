# ControlIt - כל הקוד של הפרויקט

> פרויקט שליטה מרחוק ב-LAN, כתוב ב-Python + tkinter.
> מבנה: login_page -> launcher -> main_menu (Admin) / agent_gui (User).
> תקשורת: TCP 5555 (פקודות מוצפנות), UDP 5556 (גילוי), TCP 5001 (קבצים).

---

## 📄 config.py  (27 שורות)

```python
"""
config.py — הגדרות גלובליות לפרויקט
קורא מ-.env אם קיים, אחרת משתמש בברירת מחדל.
"""
import os

# נסה לטעון .env אם python-dotenv מותקן
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv לא מותקן — משתמשים ב-environment variables רגילים

# ── MySQL ────────────────────────────────────────────────────────────────────
DB_HOST     = os.environ.get("DB_HOST",     "localhost")
DB_USER     = os.environ.get("DB_USER",     "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "Liamfort5")   # fallback לפיתוח בלבד
DB_NAME     = os.environ.get("DB_NAME",     "controlit_db")

# ── רשת ─────────────────────────────────────────────────────────────────────
CMD_PORT      = int(os.environ.get("CMD_PORT",      5555))  # TCP: פקודות
DISCOVERY_PORT = int(os.environ.get("DISCOVERY_PORT", 5556))  # UDP: גילוי agents
TRANSFER_PORT  = int(os.environ.get("TRANSFER_PORT",  5001))  # TCP: העברת קבצים

# ── אבטחה ────────────────────────────────────────────────────────────────────
AGENT_TIMEOUT_SEC = int(os.environ.get("AGENT_TIMEOUT_SEC", 10))  # שניות עד שagent נחשב offline
```

---

## 📄 crypto.py  (26 שורות)

```python
import hashlib
import base64

_SECRET_PASSWORD = b"ControlIt-SecretKey-2024"
_raw_key = hashlib.sha256(_SECRET_PASSWORD).digest()

def encrypt(text: str) -> str:
    data = text.encode('utf-8')
    key = _raw_key
    result = bytearray()

    for i, byte in enumerate(data):
        result.append(byte ^ key[i % len(key)])

    return base64.b64encode(bytes(result)).decode('utf-8')

def decrypt(text: str) -> str:
    data = base64.b64decode(text.encode('utf-8'))
    key = _raw_key
    result = bytearray()

    for i, byte in enumerate(data):
        result.append(byte ^ key[i % len(key)])

    return bytes(result).decode('utf-8')
```

---

## 📄 net_utils.py  (72 שורות)

```python
"""
net_utils.py — שליחה וקבלה מוצפנת דרך TCP socket

פרוטוקול:
  כל הודעה = מחרוזת מוצפנת + תו newline (\\n)
  נתונים פנימיים מופרדים בתו | (pipe)

דוגמה:
  שליחה: send_msg(sock, ["CMD", "SCREENSHOT"])
  קבלה:  recv_msg(sock)  →  ["OK", "<base64_image>"]
"""

from crypto import encrypt, decrypt


def send_msg(conn, data):
    """
    שולח הודעה מוצפנת דרך socket.

    data יכול להיות:
      - list  → מחברים ב-|    לדוגמה: ["CMD","SHELL","dir"] → "CMD|SHELL|dir"
      - dict  → key=value ב-| לדוגמה: {"cmd":"SYSINFO"}     → "cmd=SYSINFO"
      - str   → נשלח כמו שהוא
    """
    if isinstance(data, list):
        data = '|'.join(str(x) for x in data)
    elif isinstance(data, dict):
        # תיקון: שומרים גם את המפתחות ולא רק הערכים
        data = '|'.join(f"{k}={v}" for k, v in data.items())
    elif not isinstance(data, str):
        data = str(data)

    encrypted = encrypt(data)
    conn.sendall((encrypted + "\n").encode("utf-8"))


def recv_msg(conn):
    """
    מקבל הודעה מוצפנת אחת מ-socket.

    קורא bytes עד שמגיע \\n, מפענח, ומחזיר list של חלקים.
    מחזיר None אם החיבור נסגר או הפענוח נכשל.

    הערה: בפרוטוקול request-response (שלח אחת, קבל אחת)
          השיטה הזאת עובדת בצורה אמינה לחלוטין.
    """
    buf = bytearray()
    while True:
        try:
            chunk = conn.recv(4096)
        except OSError:
            return None

        if not chunk:
            return None

        buf.extend(chunk)

        if b"\n" in buf:
            line, _remainder = buf.split(b"\n", 1)
            # _remainder נשמר לשימוש עתידי אם יהיה צורך
            text = bytes(line).decode("utf-8").strip()
            if not text:
                return None
            try:
                decrypted = decrypt(text)
                parts = decrypted.split('|')
                return parts
            except Exception as e:
                print(f"[net_utils] Decrypt error: {e}")
                return None
```

---

## 📄 my_connector.py  (314 שורות)

```python
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
```

---

## 📄 login_page.py  (180 שורות)

```python
import tkinter as tk
from tkinter import messagebox, font
import sys
import subprocess
from my_connector import login, register, save_user_machine, create_tables, db_available

try:
    create_tables()
except Exception as e:
    print(f"DB init error: {e}")

def open_window(mode, *args):
    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable, mode] + list(args))
    else:
        scripts = {
            "agent": "agent_gui.py",
            "login": "login_page.py",
            "launcher": "launcher.py",
            "controller": "main_menu.py",
        }
        subprocess.Popen([sys.executable, scripts[mode]] + list(args))

class LoginApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ControlIt - Access")
        self.geometry("1000x600")
        self.configure(bg="#0a0a0a")
        self.resizable(False, False)

        self.setup_ui()

    def setup_ui(self):
        # Left panel - Login
        left = tk.Frame(self, bg="#1a1a1a", width=500)
        left.pack(side="left", fill="both", expand=True)

        # Right panel - Register
        right = tk.Frame(self, bg="#0a0a0a", width=500)
        right.pack(side="right", fill="both", expand=True)

        # ===== LEFT PANEL: LOGIN =====
        login_title = tk.Label(left, text="LOGIN",
                              font=("Arial", 22, "bold"),
                              bg="#1a1a1a", fg="#e74c3c")
        login_title.pack(pady=(60, 10))

        tk.Label(left, text="Sign in to your account",
                font=("Arial", 10),
                bg="#1a1a1a", fg="#888888").pack()

        # Login username
        tk.Label(left, text="Username:",
                font=("Arial", 11, "bold"),
                bg="#1a1a1a", fg="#ffffff").pack(anchor="w", padx=40, pady=(30, 5))

        self.login_user = tk.Entry(left, font=("Arial", 11),
                                   bg="#222222", fg="#ffffff",
                                   width=35, bd=0)
        self.login_user.pack(padx=40, pady=(0, 15), ipady=8)

        # Login password
        tk.Label(left, text="Password:",
                font=("Arial", 11, "bold"),
                bg="#1a1a1a", fg="#ffffff").pack(anchor="w", padx=40, pady=(0, 5))

        self.login_pass = tk.Entry(left, show="•", font=("Arial", 11),
                                   bg="#222222", fg="#ffffff",
                                   width=35, bd=0)
        self.login_pass.pack(padx=40, pady=(0, 30), ipady=8)

        tk.Button(left, text="SIGN IN",
                 font=("Arial", 12, "bold"),
                 bg="#e74c3c", fg="white",
                 width=25, bd=0, padx=20, pady=10,
                 command=self.handle_login).pack()

        # ===== RIGHT PANEL: REGISTER =====
        reg_title = tk.Label(right, text="CREATE ACCOUNT",
                            font=("Arial", 22, "bold"),
                            bg="#0a0a0a", fg="#e74c3c")
        reg_title.pack(pady=(60, 10))

        tk.Label(right, text="Join ControlIt today",
                font=("Arial", 10),
                bg="#0a0a0a", fg="#888888").pack()

    # Register username
        tk.Label(right, text="Username:",
                font=("Arial", 11, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(anchor="w", padx=40, pady=(30, 5))

        self.reg_user = tk.Entry(right, font=("Arial", 11),
                                bg="#222222", fg="#ffffff",
                                width=35, bd=0)
        self.reg_user.pack(padx=40, pady=(0, 15), ipady=8)

        # Register password
        tk.Label(right, text="Password:",
                font=("Arial", 11, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(anchor="w", padx=40, pady=(0, 5))

        self.reg_pass = tk.Entry(right, show="•", font=("Arial", 11),
                                bg="#222222", fg="#ffffff",
                                width=35, bd=0)
        self.reg_pass.pack(padx=40, pady=(0, 15), ipady=8)

        # Confirm password
        tk.Label(right, text="Confirm Password:",
                font=("Arial", 11, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(anchor="w", padx=40, pady=(0, 5))

        self.reg_confirm = tk.Entry(right, show="•", font=("Arial", 11),
                                   bg="#222222", fg="#ffffff",
                                   width=35, bd=0)
        self.reg_confirm.pack(padx=40, pady=(0, 30), ipady=8)

        tk.Button(right, text="SIGN UP",
                 font=("Arial", 12, "bold"),
                 bg="#e74c3c", fg="white",
                 width=25, bd=0, padx=20, pady=10,
                 command=self.handle_register).pack()

        self.bind("<Return>", lambda e: self.handle_login())

    def handle_login(self):
        u = self.login_user.get().strip()
        p = self.login_pass.get()

        if not u or not p:
            messagebox.showerror("Error", "Fill all fields")
            return

        # התחברות אמיתית — מול MySQL אם קיים, אחרת מול קובץ חשבונות מקומי
        res = login(u, p)
        if res.get('success'):
            try:
                save_user_machine(u)
            except Exception:
                pass
            self._enter(u)
        else:
            messagebox.showerror("Failed", res.get('message', "Invalid credentials"))

    def _enter(self, username):
        """סוגר את מסך הכניסה ופותח את מסך בחירת המצב."""
        self.destroy()
        import launcher
        launcher.ControlItLauncher(username).mainloop()

    def handle_register(self):
        u = self.reg_user.get().strip()
        p = self.reg_pass.get()
        c = self.reg_confirm.get()

        if not u or not p or not c:
            messagebox.showerror("Error", "Fill all fields")
            return

        if p != c:
            messagebox.showerror("Error", "Passwords don't match")
            return

        res = register(u, p)
        if res.get('success'):
            messagebox.showinfo("Success", "Account created! Now login.")
            self.reg_user.delete(0, "end")
            self.reg_pass.delete(0, "end")
            self.reg_confirm.delete(0, "end")
            self.login_user.delete(0, "end")
            self.login_pass.delete(0, "end")
            self.login_user.insert(0, u)
        else:
            messagebox.showerror("Failed", res.get('message', "Error"))

if __name__ == "__main__":
    app = LoginApp()
    app.mainloop()
```

---

## 📄 launcher.py  (85 שורות)

```python
import tkinter as tk
from tkinter import messagebox
import subprocess
import sys

def open_window(mode, *args):
    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable, mode] + list(args))
    else:
        scripts = {
            "agent": "agent_gui.py",
            "login": "login_page.py",
            "launcher": "launcher.py",
            "controller": "main_menu.py",
            "script": "script.py",
            "transfer": "file_transfer.py",
        }
        subprocess.Popen([sys.executable, scripts[mode]] + list(args))

class ControlItLauncher(tk.Tk):
    def __init__(self, username="User"):
        super().__init__()
        self.username = username
        self.title("ControlIt - Select Mode")
        self.geometry("600x400")
        self.configure(bg="#1a1a1a")
        self.resizable(False, False)
        self.setup_ui()

    def setup_ui(self):
        top_frame = tk.Frame(self, bg="#1a1a1a")
        top_frame.pack(pady=30)

        title_label = tk.Label(top_frame, text="CONTROLIT",
                              font=("Arial", 28, "bold"),
                              bg="#1a1a1a", fg="#e74c3c")
        title_label.pack()

        subtitle = tk.Label(top_frame, text=f"Welcome {self.username} - choose mode",
                          font=("Arial", 11),
                          bg="#1a1a1a", fg="#999999")
        subtitle.pack()

        buttons_frame = tk.Frame(self, bg="#1a1a1a")
        buttons_frame.pack(fill="both", expand=True, padx=40, pady=20)

        admin_btn = tk.Button(buttons_frame, text="ADMIN\nControl Mode",
                             font=("Arial", 14, "bold"),
                             bg="#e74c3c", fg="white",
                             width=20, height=5,
                             command=self.launch_admin)
        admin_btn.pack(side="left", padx=10)

        user_btn = tk.Button(buttons_frame, text="USER\nManaged Mode",
                            font=("Arial", 14, "bold"),
                            bg="#cc0000", fg="white",
                            width=20, height=5,
                            command=self.launch_user)
        user_btn.pack(side="right", padx=10)

    def launch_admin(self):
        try:
            print("Launching ADMIN mode...")
            import main_menu
            self.destroy()
            app = main_menu.CyberDashboard(self.username)
            app.mainloop()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Admin:\n{e}")

    def launch_user(self):
        try:
            print("Launching USER mode...")
            import agent_gui
            self.destroy()
            app = agent_gui.AgentApp()
            app.mainloop()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open User:\n{e}")

if __name__ == "__main__":
    user = sys.argv[1] if len(sys.argv) > 1 else "Guest"
    app = ControlItLauncher(user)
    app.mainloop()
```

---

## 📄 main.py  (66 שורות)

```python
# ============================================================
#  main.py - נקודת הכניסה המאוחדת לכל האפליקציה
# ============================================================

import sys
import traceback


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""

    if mode == "agent":
        from agent_gui import AgentApp
        AgentApp().mainloop()

    elif mode == "login":
        from login_page import LoginApp
        LoginApp().mainloop()

    elif mode == "controller":
        username = sys.argv[2] if len(sys.argv) > 2 else "User"
        from main_menu import CyberDashboard
        CyberDashboard(username).mainloop()

    elif mode == "script":
        from script import ScriptConsoleApp
        if len(sys.argv) >= 5:
            target_ip  = sys.argv[2]
            relay_port = int(sys.argv[3])
            agent_id   = sys.argv[4]
            agent_name = sys.argv[5] if len(sys.argv) > 5 else agent_id
            ScriptConsoleApp(target_ip, relay_port=relay_port,
                             agent_id=agent_id, agent_name=agent_name).mainloop()
        else:
            ScriptConsoleApp("127.0.0.1").mainloop()

    elif mode == "transfer":
        from file_transfer import FileTransferApp
        target_ip = sys.argv[2] if len(sys.argv) > 2 else ""
        FileTransferApp(target_ip).mainloop()

    elif mode == "launcher":
        username = sys.argv[2] if len(sys.argv) > 2 else "User"
        from launcher import ControlItLauncher
        ControlItLauncher(username).mainloop()

    else:
        from login_page import LoginApp
        LoginApp().mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        err = traceback.format_exc()
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("ControlIt - Startup Error", err)
            root.destroy()
        except Exception:
            pass
```

---

## 📄 agent_gui.py  (340 שורות)

```python
import tkinter as tk
import socket
import threading
import subprocess
import platform
import os
import sys
import time
import base64
import io
from PIL import ImageGrab
from tkinter import messagebox
from net_utils import send_msg, recv_msg
from config import CMD_PORT, DISCOVERY_PORT, TRANSFER_PORT

class UDPBroadcaster(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.stop_flag = False

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while not self.stop_flag:
            try:
                msg = f"user|{socket.gethostname()}|{socket.gethostbyname(socket.gethostname())}"
                sock.sendto(msg.encode('utf-8'), ("<broadcast>", DISCOVERY_PORT))
                time.sleep(3)
            except Exception:
                pass

class CommandServer(threading.Thread):
    def __init__(self, agent_app):
        super().__init__(daemon=True)
        self.agent_app = agent_app
        self.stop_flag = False

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(("0.0.0.0", CMD_PORT))
            server.listen(5)
            print(f"Server listening on port {CMD_PORT}...")

            while not self.stop_flag:
                try:
                    server.settimeout(1)
                    client, addr = server.accept()
                    threading.Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
                except socket.timeout:
                    pass
                except Exception:
                    pass
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            server.close()

    def handle_client(self, client, addr):
        try:
            print(f"Client connected: {addr}")
            while True:
                msg = recv_msg(client)
                if not msg:
                    break

                response = self.process_command(msg)
                send_msg(client, response)
        except Exception as e:
            print(f"Client error: {e}")
        finally:
            client.close()

    def process_command(self, msg):
        try:
            if isinstance(msg, list):
                cmd = msg[0] if msg else "UNKNOWN"
            else:
                cmd = msg

            print(f"Command: {cmd}")

            if cmd == "CMD" and len(msg) > 1:
                action = msg[1] if len(msg) > 1 else ""

                if action == "SCREENSHOT":
                    return self.do_screenshot()
                elif action == "SHELL" and len(msg) > 2:
                    return self.do_shell(msg[2])
                elif action == "SYSINFO":
                    return self.do_sysinfo()
                elif action == "MSG" and len(msg) > 2:
                    return self.do_message(msg[2])
                elif action == "POWER" and len(msg) > 2:
                    return self.do_power(msg[2])
                else:
                    return ["ERROR", "Unknown action"]
            else:
                return ["ERROR", "Invalid command"]
        except Exception as e:
            return ["ERROR", str(e)]

    def do_screenshot(self):
        try:
            print("Taking screenshot...")
            img = ImageGrab.grab()
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return ["OK", img_data]
        except Exception as e:
            return ["ERROR", str(e)]

    def do_shell(self, cmd):
        try:
            print(f"Executing: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            output = result.stdout + result.stderr
            return ["OK", output[:2000]]
        except Exception as e:
            return ["ERROR", str(e)]

    def do_sysinfo(self):
        try:
            info = f"System: {platform.system()} {platform.release()}\n"
            info += f"Machine: {platform.machine()}\n"
            proc = platform.processor() or os.environ.get("PROCESSOR_IDENTIFIER", "Unknown")
            info += f"Processor: {proc}\n"
            info += f"CPU cores: {os.cpu_count()}\n"
            info += f"Hostname: {socket.gethostname()}\n"
            info += f"User: {os.environ.get('USERNAME', '?')}\n"

            # RAM דרך ctypes (עובד בכל גרסת Windows, בלי wmic)
            try:
                import ctypes
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [("dwLength", ctypes.c_ulong),
                                ("dwMemoryLoad", ctypes.c_ulong),
                                ("ullTotalPhys", ctypes.c_ulonglong),
                                ("ullAvailPhys", ctypes.c_ulonglong),
                                ("ullTotalPageFile", ctypes.c_ulonglong),
                                ("ullAvailPageFile", ctypes.c_ulonglong),
                                ("ullTotalVirtual", ctypes.c_ulonglong),
                                ("ullAvailVirtual", ctypes.c_ulonglong),
                                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
                mem = MEMORYSTATUSEX()
                mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
                info += f"RAM: {mem.ullTotalPhys // (1024**3)} GB (in use {mem.dwMemoryLoad}%)\n"
            except Exception:
                pass

            # שטח דיסק דרך shutil (פייתון טהור)
            try:
                import shutil
                total, used, free = shutil.disk_usage("C:\\")
                info += f"Disk C: {total // (1024**3)} GB total, {free // (1024**3)} GB free\n"
            except Exception:
                pass

            return ["OK", info]
        except Exception as e:
            return ["ERROR", str(e)]

    def do_message(self, text):
        try:
            print(f"Message: {text}")
            self.agent_app.show_notification(text)
            return ["OK"]
        except Exception as e:
            return ["ERROR", str(e)]

    def do_power(self, action):
        try:
            if action == "SHUTDOWN":
                os.system("shutdown /s /t 10")
                return ["OK"]
            elif action == "RESTART":
                os.system("shutdown /r /t 10")
                return ["OK"]
            else:
                return ["ERROR", "Unknown action"]
        except Exception as e:
            return ["ERROR", str(e)]

class FileReceiver(threading.Thread):
    """מאזין על פורט 5001 ומקבל קבצים מהמנהל, שומר ל-Downloads."""
    def __init__(self, agent_app):
        super().__init__(daemon=True)
        self.agent_app = agent_app
        self.stop_flag = False

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(("0.0.0.0", TRANSFER_PORT))
            server.listen(5)
            while not self.stop_flag:
                try:
                    server.settimeout(1)
                    client, addr = server.accept()
                    threading.Thread(target=self.handle, args=(client,), daemon=True).start()
                except socket.timeout:
                    pass
                except Exception:
                    pass
        except Exception as e:
            print(f"FileReceiver error: {e}")
        finally:
            server.close()

    def handle(self, client):
        try:
            # קורא header "filename<SEP>filesize\n"
            buf = bytearray()
            while b"\n" not in buf:
                chunk = client.recv(4096)
                if not chunk:
                    return
                buf.extend(chunk)
            header, rest = buf.split(b"\n", 1)
            filename, filesize = header.decode("utf-8").split("<SEP>")
            filesize = int(filesize)

            downloads = os.path.join(os.path.expanduser("~"), "Downloads")
            os.makedirs(downloads, exist_ok=True)
            path = os.path.join(downloads, os.path.basename(filename))
            base, ext = os.path.splitext(path)
            i = 1
            while os.path.exists(path):          # לא דורסים קובץ קיים
                path = f"{base} ({i}){ext}"
                i += 1

            received = len(rest)
            with open(path, "wb") as f:
                if rest:
                    f.write(rest)
                while received < filesize:
                    chunk = client.recv(min(65536, filesize - received))
                    if not chunk:
                        break
                    f.write(chunk)
                    received += len(chunk)

            name = os.path.basename(path)
            self.agent_app.after(0, lambda: self.agent_app.log_message(f"File received: {name}"))
        except Exception as e:
            print(f"File recv error: {e}")
        finally:
            client.close()


class AgentApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ControlIt - Managed Machine")
        self.geometry("500x300")
        self.configure(bg="#1a1a1a")

        self.broadcaster = UDPBroadcaster()
        self.broadcaster.start()

        self.server = CommandServer(self)
        self.server.start()

        self.file_receiver = FileReceiver(self)
        self.file_receiver.start()

        self.setup_ui()

    def setup_ui(self):
        header = tk.Frame(self, bg="#0a0a0a")
        header.pack(fill="x", padx=20, pady=15)

        title = tk.Label(header, text="User Mode Active",
                        font=("Arial", 16, "bold"),
                        bg="#0a0a0a", fg="#00ff00")
        title.pack()

        info_frame = tk.Frame(self, bg="#1a1a1a")
        info_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(info_frame, text=f"Hostname: {socket.gethostname()}",
                font=("Arial", 11),
                bg="#1a1a1a", fg="#ffffff").pack(anchor="w", pady=3)

        tk.Label(info_frame, text=f"IP: {socket.gethostbyname(socket.gethostname())}",
                font=("Arial", 11),
                bg="#1a1a1a", fg="#ffffff").pack(anchor="w", pady=3)

        tk.Label(info_frame, text=f"Status: Broadcasting on LAN (UDP:{DISCOVERY_PORT})",
                font=("Arial", 10),
                bg="#1a1a1a", fg="#00ff00").pack(anchor="w", pady=3)

        tk.Label(info_frame, text=f"Listening on TCP:{CMD_PORT}",
                font=("Arial", 10),
                bg="#1a1a1a", fg="#00ff00").pack(anchor="w", pady=3)

        status_frame = tk.Frame(self, bg="#1a1a1a")
        status_frame.pack(fill="both", expand=True, padx=20, pady=15)

        self.status_text = tk.Text(status_frame, height=10, width=50,
                                  bg="#0a0a0a", fg="#00ff00",
                                  font=("Consolas", 10))
        self.status_text.pack(fill="both", expand=True)

        self.log_message("Agent started successfully")
        self.log_message("Broadcasting availability to LAN...")
        self.log_message("Waiting for admin commands...")

        btn_frame = tk.Frame(self, bg="#1a1a1a")
        btn_frame.pack(fill="x", padx=20, pady=10)

        tk.Button(btn_frame, text="Exit",
                 font=("Arial", 10),
                 bg="#cc0000", fg="white",
                 command=self.on_exit).pack(side="right", padx=5)

    def log_message(self, msg):
        self.status_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.status_text.see("end")

    def show_notification(self, text):
        messagebox.showinfo("Message from Admin", text)
        self.log_message(f"Received message: {text}")

    def on_exit(self):
        self.broadcaster.stop_flag = True
        self.server.stop_flag = True
        self.file_receiver.stop_flag = True
        self.destroy()

if __name__ == "__main__":
    app = AgentApp()
    app.mainloop()
```

---

## 📄 main_menu.py  (403 שורות)

```python
import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext
import socket
import sys
import subprocess
import threading
import time
import base64
import io
from datetime import datetime
from PIL import Image, ImageTk
from net_utils import send_msg, recv_msg
import os
from tkinter import filedialog
from config import CMD_PORT, DISCOVERY_PORT, AGENT_TIMEOUT_SEC, TRANSFER_PORT

def open_window(mode, *args):
    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable, mode] + list(args))
    else:
        scripts = {
            "agent": "agent_gui.py",
            "login": "login_page.py",
            "controller": "main_menu.py",
            "script": "script.py",
            "transfer": "file_transfer.py",
        }
        subprocess.Popen([sys.executable, scripts[mode]] + list(args))

class UDPListener(threading.Thread):
    def __init__(self, callback):
        super().__init__(daemon=True)
        self.callback = callback
        self.stop_flag = False

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", DISCOVERY_PORT))
        except Exception:
            print("UDP bind error")
            return

        sock.settimeout(2)
        while not self.stop_flag:
            try:
                data, addr = sock.recvfrom(1024)
                try:
                    msg = data.decode('utf-8')
                    parts = msg.split('|')
                    if len(parts) >= 3:
                        info = {
                            'role': parts[0],
                            'name': parts[1],
                            'ip': addr[0]
                        }
                        self.callback(addr[0], info)
                except Exception:
                    pass
            except socket.timeout:
                pass
            except Exception:
                pass

class CyberDashboard(tk.Tk):
    def __init__(self, username):
        super().__init__()
        self.title("ControlIt - Admin Panel")
        self.geometry("900x700")
        self.configure(bg="#1a1a1a")
        self.username = username
        self.selected_agent = None
        self.agents = {}           # ip → {ip, name, role, last_seen}
        self.agent_sock = None
        self.stop_listener = False

        self.discovery = UDPListener(self._on_discovery)
        self.discovery.start()

        self.setup_ui()
        self.start_refresh_loop()

    def setup_ui(self):
        header = tk.Frame(self, bg="#0a0a0a")
        header.pack(fill="x", padx=20, pady=10)

        title = tk.Label(header, text="ControlIt Admin Dashboard",
                        font=("Arial", 18, "bold"),
                        bg="#0a0a0a", fg="#e74c3c")
        title.pack(side="left")

        user_label = tk.Label(header, text=f"Logged in: {self.username}",
                             font=("Arial", 10),
                             bg="#0a0a0a", fg="#666666")
        user_label.pack(side="right")

        agent_frame = tk.Frame(self, bg="#1a1a1a")
        agent_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(agent_frame, text="Online Users:",
                font=("Arial", 11, "bold"),
                bg="#1a1a1a", fg="#ffffff").pack(anchor="w")

        btn_frame = tk.Frame(agent_frame, bg="#1a1a1a")
        btn_frame.pack(fill="x", pady=(5, 10))

        tk.Button(btn_frame, text="Refresh",
                 font=("Arial", 10),
                 bg="#e74c3c", fg="white",
                 command=self.refresh_agents).pack(side="left", padx=5)

        tk.Label(btn_frame, text="",
                bg="#1a1a1a", fg="#999999").pack(side="left", padx=5)
        self.selected_label = tk.Label(btn_frame, text="No selection",
                                       bg="#1a1a1a", fg="#999999",
                                       font=("Arial", 10))
        self.selected_label.pack(side="left")

        self.agents_listbox = tk.Listbox(agent_frame, height=4,
                                        bg="#0a0a0a", fg="#ffffff",
                                        font=("Arial", 10))
        self.agents_listbox.pack(fill="x")

        actions_frame = tk.Frame(self, bg="#1a1a1a")
        actions_frame.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(actions_frame, text="Actions:",
                font=("Arial", 11, "bold"),
                bg="#1a1a1a", fg="#ffffff").pack(anchor="w", pady=(0, 10))

        grid = tk.Frame(actions_frame, bg="#1a1a1a")
        grid.pack(fill="both", expand=True)

        self.create_action_button(grid, 0, 0, "Screenshot", self.take_screenshot)
        self.create_action_button(grid, 0, 1, "Shell", self.open_shell)
        self.create_action_button(grid, 0, 2, "File Transfer", self.open_file_transfer)
        self.create_action_button(grid, 1, 0, "System Info", self.get_sysinfo)
        self.create_action_button(grid, 1, 1, "Send Message", self.send_message)
        self.create_action_button(grid, 1, 2, "Power", self.power_menu)

    def create_action_button(self, parent, row, col, text, cmd):
        btn = tk.Button(parent, text=text,
                       font=("Arial", 12, "bold"),
                       bg="#e74c3c", fg="white",
                       height=3, width=15,
                       command=cmd)
        btn.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        parent.grid_rowconfigure(row, weight=1)
        parent.grid_columnconfigure(col, weight=1)

    def _on_discovery(self, ip, info):
        """נקרא מה-UDP listener thread בכל פעם שמגיע broadcast."""
        if info.get('role') == 'user':
            self.agents[ip] = {
                'ip':        ip,
                'name':      info.get('name', 'User'),
                'role':      'user',
                'last_seen': time.time()   # ← מתי נראה לאחרונה
            }
            self.after(0, self.refresh_agents)

    def refresh_agents(self):
        """מסנן agents שלא שלחו broadcast מעל AGENT_TIMEOUT_SEC שניות."""
        now = time.time()
        # הסר agents שנעלמו
        stale = [ip for ip, info in self.agents.items()
                 if now - info.get('last_seen', 0) > AGENT_TIMEOUT_SEC]
        for ip in stale:
            del self.agents[ip]
            # אם ה-agent שנעלם הוא הנבחר — אפס בחירה
            if self.selected_agent and self.selected_agent.get('ip') == ip:
                self.selected_agent = None
                self.selected_label.config(text="No selection")

        self.agents_listbox.delete(0, "end")
        for ip, info in self.agents.items():
            self.agents_listbox.insert("end", f"{info['name']} ({ip})")
        self.agents_listbox.bind("<<ListboxSelect>>", self.on_select)

    def on_select(self, event):
        sel = self.agents_listbox.curselection()
        if sel:
            ip = list(self.agents.keys())[sel[0]]
            self.selected_agent = self.agents[ip]
            self.selected_label.config(text=f"Selected: {self.selected_agent['name']}")

    def _connect_agent(self):
        if not self.selected_agent:
            messagebox.showwarning("Error", "Select an agent first")
            return False
        try:
            self.agent_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.agent_sock.settimeout(5)
            self.agent_sock.connect((self.selected_agent['ip'], CMD_PORT))
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Cannot connect: {e}")
            self.agent_sock = None
            return False

    def send_command(self, cmd):
        """שולח פקודה ומחכה לתשובה. חייב לרוץ בthread נפרד (לא ב-GUI thread)."""
        if not self.selected_agent:
            self.after(0, lambda: messagebox.showwarning("Error", "Select an agent first"))
            return None

        if not self.agent_sock:
            if not self._connect_agent():
                return None

        try:
            send_msg(self.agent_sock, cmd)
            response = recv_msg(self.agent_sock)
            return response
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Command failed: {e}"))
            self.agent_sock = None
            return None

    # ── Screenshot ────────────────────────────────────────────────────────────
    def take_screenshot(self):
        threading.Thread(target=self._screenshot_thread, daemon=True).start()

    def _screenshot_thread(self):
        resp = self.send_command("CMD|SCREENSHOT|")
        if not resp or len(resp) < 2:
            self.after(0, lambda: messagebox.showerror("Error", "No response"))
            return
        try:
            img_data = base64.b64decode(resp[1])
            img = Image.open(io.BytesIO(img_data))
            self.after(0, lambda i=img: self._show_screenshot(i))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _show_screenshot(self, img):
        win = tk.Toplevel(self)
        win.title("Screenshot")
        win.configure(bg="#0a0a0a")
        img.thumbnail((1000, 600))
        tk_img = ImageTk.PhotoImage(img)
        lbl = tk.Label(win, image=tk_img, bg="black")
        lbl.image = tk_img
        lbl.pack()

    # ── Shell ─────────────────────────────────────────────────────────────────
    def open_shell(self):
        win = tk.Toplevel(self)
        win.title("Remote Shell")
        win.geometry("500x400")
        win.configure(bg="#1a1a1a")

        text = scrolledtext.ScrolledText(win, height=15, width=60,
                                        bg="#0a0a0a", fg="#00ff00",
                                        font=("Consolas", 10))
        text.pack(padx=10, pady=10, fill="both", expand=True)

        cmd_frame = tk.Frame(win, bg="#1a1a1a")
        cmd_frame.pack(fill="x", padx=10, pady=5)

        cmd_entry = tk.Entry(cmd_frame, bg="#0a0a0a", fg="#ffffff",
                            font=("Consolas", 10))
        cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        def run_cmd():
            cmd = cmd_entry.get().strip()
            if not cmd:
                return
            text.insert("end", f"\n$ {cmd}\n")
            text.see("end")
            cmd_entry.delete(0, "end")

            def _thread():
                resp = self.send_command(f"CMD|SHELL|{cmd}")
                output = resp[1] if resp and len(resp) > 1 else "No response"
                self.after(0, lambda: (text.insert("end", output + "\n"), text.see("end")))

            threading.Thread(target=_thread, daemon=True).start()

        cmd_entry.bind("<Return>", lambda e: run_cmd())
        tk.Button(cmd_frame, text="Run",
                 bg="#e74c3c", fg="white",
                 command=run_cmd).pack(side="right")

    # ── File Transfer ─────────────────────────────────────────────────────────
    def open_file_transfer(self):
        if not self.selected_agent:
            messagebox.showwarning("Error", "Select an agent first")
            return
        path = filedialog.askopenfilename(title="Choose a file to send")
        if not path:
            return

        def _thread():
            try:
                filename = os.path.basename(path)
                filesize = os.path.getsize(path)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(15)
                sock.connect((self.selected_agent['ip'], TRANSFER_PORT))
                sock.sendall(f"{filename}<SEP>{filesize}\n".encode("utf-8"))
                with open(path, "rb") as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        sock.sendall(chunk)
                sock.close()
                self.after(0, lambda: messagebox.showinfo(
                    "Success", f"Sent '{filename}' ({filesize} bytes).\nSaved to the user's Downloads folder."))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Transfer failed: {e}"))

        threading.Thread(target=_thread, daemon=True).start()

    # ── System Info ───────────────────────────────────────────────────────────
    def get_sysinfo(self):
        """רץ בthread כדי לא לקפיא את ה-GUI."""
        def _thread():
            resp = self.send_command("CMD|SYSINFO|")
            if resp and len(resp) > 1:
                self.after(0, lambda: messagebox.showinfo("System Info", resp[1]))
            else:
                self.after(0, lambda: messagebox.showerror("Error", "No response"))
        threading.Thread(target=_thread, daemon=True).start()

    # ── Send Message ──────────────────────────────────────────────────────────
    def send_message(self):
        msg = simpledialog.askstring("Message", "Enter message:")
        if not msg:
            return

        def _thread():
            resp = self.send_command(f"CMD|MSG|{msg}")
            if resp and resp[0] == "OK":
                self.after(0, lambda: messagebox.showinfo("Success", "Message sent"))
            else:
                self.after(0, lambda: messagebox.showerror("Error", "Failed to send"))
        threading.Thread(target=_thread, daemon=True).start()

    # ── Power ─────────────────────────────────────────────────────────────────
    def power_menu(self):
        win = tk.Toplevel(self)
        win.title("Power Options")
        win.geometry("300x150")
        win.configure(bg="#1a1a1a")   # תיקון: תואם את העיצוב

        tk.Label(win, text="Choose action:",
                font=("Arial", 12),
                bg="#1a1a1a", fg="#ffffff").pack(pady=20)

        tk.Button(win, text="Shutdown",
                 font=("Arial", 11),
                 bg="#cc0000", fg="white",
                 height=2, width=20,
                 command=lambda: self._power_cmd("SHUTDOWN", win)).pack(pady=5)

        tk.Button(win, text="Restart",
                 font=("Arial", 11),
                 bg="#cc8800", fg="white",
                 height=2, width=20,
                 command=lambda: self._power_cmd("RESTART", win)).pack(pady=5)

    def _power_cmd(self, action, win):
        if not messagebox.askyesno("Confirm", f"Execute {action}?"):
            return
        win.destroy()

        def _thread():
            resp = self.send_command(f"CMD|POWER|{action}")
            if resp and resp[0] == "OK":
                self.after(0, lambda: messagebox.showinfo("Success", f"{action} command sent"))
        threading.Thread(target=_thread, daemon=True).start()

    # ── Refresh loop ──────────────────────────────────────────────────────────
    def start_refresh_loop(self):
        """פועל ברקע — מרענן רשימת agents כל 3 שניות ומסיר שנעלמו."""
        def loop():
            while not self.stop_listener:
                time.sleep(3)
                try:
                    self.after(0, self.refresh_agents)
                except Exception:
                    pass
        threading.Thread(target=loop, daemon=True).start()

    def on_closing(self):
        self.stop_listener = True
        self.discovery.stop_flag = True
        if self.agent_sock:
            try:
                self.agent_sock.close()
            except Exception:
                pass
        self.destroy()

if __name__ == "__main__":
    user = sys.argv[1] if len(sys.argv) > 1 else "Admin"
    app = CyberDashboard(user)
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
```

---

**סה"כ: 9 קבצים, 1513 שורות קוד.**
