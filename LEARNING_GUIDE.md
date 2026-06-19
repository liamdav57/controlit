# ControlIt — מדריך למידה מאפס 🎓

> **למי הקובץ הזה?** לי (ליאם), כדי ללמוד את הפרויקט שלי מ-0 ולהתכונן להגנה.
> אפשר גם לתת אותו ל-AI אחר ולבקש שילמד אותי לפיו.

---

## 🤖 הוראות ל-AI שמלמד אותי (תן לו את הקטע הזה)

> אתה מורה פרטי שמלמד אותי את פרויקט ControlIt. השתמש במסמך הזה כספר הלימוד.
> לְמד אותי **לפי הסדר** (רמה 1 → 4). לכל קובץ:
> 1. הסבר לי בקצרה מה הוא עושה ולמה הוא קיים.
> 2. עבור על הקוד **בלוק אחר בלוק** והסבר כל שורה במילים פשוטות.
> 3. שאל אותי 3-5 שאלות ותן לי לענות לפני שתמשיך.
> 4. אם טעיתי — תקן אותי בעדינות והסבר שוב.
> אל תקפוץ קדימה — ודא שהבנתי כל רמה לפני המעבר לבאה. דבר עברית.

---

## 🗺️ חלק 1 — התמונה הגדולה (קרא ראשון!)

ControlIt היא מערכת **שליטה מרחוק ברשת מקומית (LAN)** — כמו TeamViewer מוקטן, לכיתת מחשבים.
יש **3 חלקים**:

```
┌─────────────┐         TCP 5555 (פקודות מוצפנות)        ┌─────────────┐
│   מנהל       │ ◄──────────────────────────────────────► │   נשלט       │
│  (Admin)    │                                          │  (Agent)    │
│ main_menu.py│ ◄────────  UDP 5556 (גילוי)  ───────────  │ agent_gui.py│
└─────────────┘                                          └─────────────┘
       │                                                        
       ▼ אימות                                                  
   MySQL (controlit_db)                                        
```

**זרם הכניסה:**
```
login_page.py  →  launcher.py  →  ┬→ main_menu.py  (אם בחרת ADMIN)
 (התחברות)        (בחירת מצב)      └→ agent_gui.py  (אם בחרת USER)
```

**עיקרון מרכזי:** אין שרת ביניים (relay). המנהל מתחבר **ישירות** לנשלט ב-LAN.

---

## 📚 חלק 2 — סדר הלמידה (חשוב!)

לְמד מהקטן לגדול. כל קובץ נשען על הקודמים:

| רמה | קבצים | למה כאן |
|-----|-------|---------|
| **1 — היסוד** | `config.py` → `crypto.py` → `net_utils.py` | קטנים, בלי תלויות, הבסיס של הכל |
| **2 — מסד נתונים** | `my_connector.py` | כל הקשר עם MySQL |
| **3 — זרם הכניסה** | `login_page.py` → `launcher.py` → `main.py` | המסכים הראשונים |
| **4 — הלב** | `agent_gui.py` → `main_menu.py` | הקבצים הגדולים, השאר לסוף |

---

# 🧱 רמה 1 — היסוד

## 1.1 `config.py` — מרכז ההגדרות (~26 שורות)

**תפקיד:** מרכז את כל ה"מספרי קסם" — פורטים, סיסמת MySQL, timeout — במקום אחד. לשנות פורט = לשנות שורה אחת.

```python
import os
try:
    from dotenv import load_dotenv
    load_dotenv()                  # טוען מ-.env אם קיים
except ImportError:
    pass                           # אם dotenv לא מותקן — לא נורא

# ── MySQL ──
DB_HOST     = os.environ.get("DB_HOST",     "localhost")
DB_USER     = os.environ.get("DB_USER",     "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "Liamfort5")   # fallback לפיתוח
DB_NAME     = os.environ.get("DB_NAME",     "controlit_db")

# ── רשת ──
CMD_PORT       = int(os.environ.get("CMD_PORT",       5555))  # TCP: פקודות
DISCOVERY_PORT = int(os.environ.get("DISCOVERY_PORT", 5556))  # UDP: גילוי
TRANSFER_PORT  = int(os.environ.get("TRANSFER_PORT",  5001))  # TCP: קבצים

# ── אבטחה ──
AGENT_TIMEOUT_SEC = int(os.environ.get("AGENT_TIMEOUT_SEC", 10))
```

**מושגי מפתח:**
- `os.environ.get("X", default)` — מחזיר משתנה סביבה X, או את ה-default אם אין.
- `.env` — קובץ מקומי עם סודות, **לא עולה ל-GitHub** → הסיסמה לא זולגת.
- `int(...)` — פורט חייב להיות מספר; `environ.get` מחזיר טקסט, אז ממירים.

**שאלות לתרגול:**
1. אם מוחקים את `.env` — התוכנית קורסת או ממשיכה? *(ממשיכה — נופלת ל-fallback)*
2. למה `int()` סביב הפורטים אבל לא סביב הסיסמה? *(פורט = מספר, סיסמה = טקסט)*
3. איזה פורט אחראי על גילוי ובאיזה פרוטוקול? *(5556, UDP)*

---

## 1.2 `crypto.py` — הצפנה (~25 שורות)

**תפקיד:** מצפין ומפענח כל הודעה שעוברת ברשת. שיטה: XOR עם מפתח שנגזר מ-SHA-256.

```python
import hashlib, base64

_SECRET_PASSWORD = b"ControlIt-SecretKey-2024"
_raw_key = hashlib.sha256(_SECRET_PASSWORD).digest()   # → 32 bytes קבועים

def encrypt(text: str) -> str:
    data = text.encode('utf-8')                # str → bytes
    key = _raw_key
    result = bytearray()
    for i, byte in enumerate(data):
        result.append(byte ^ key[i % len(key)])    # XOR בייט-בייט
    return base64.b64encode(bytes(result)).decode('utf-8')   # → טקסט בטוח

def decrypt(text: str) -> str:
    data = base64.b64decode(text.encode('utf-8'))
    key = _raw_key
    result = bytearray()
    for i, byte in enumerate(data):
        result.append(byte ^ key[i % len(key)])    # אותו XOR בדיוק!
    return bytes(result).decode('utf-8')
```

**איך זה עובד — 3 שלבים:**
1. **SHA-256** גוזר 32 בייטים קבועים מהסיסמה → זה המפתח.
2. **XOR** — כל בייט בהודעה עובר XOR מול בייט במפתח. `i % len(key)` מגלגל את המפתח כשההודעה ארוכה מ-32.
3. **Base64** — תוצאת ה-XOR היא בייטים אקראיים (חלקם שבורים לרשת); Base64 ממיר לטקסט בטוח.

**הפלא של XOR:** אותה פעולה בדיוק מצפינה ומפענחת! `(A ^ K) ^ K = A`. לכן `encrypt` ו-`decrypt` זהות חוץ מ-Base64.

**חולשה ידועה (חשוב להגנה!):** המפתח קבוע ובקוד הפתוח. מי שמכיר את הקוד יכול לגזור אותו. שדרוג עתידי: AES-256.

**שאלות לתרגול:**
1. למה צריך Base64 *אחרי* ה-XOR? *(תוצאת XOR = בייטים שבורים לרשת)*
2. מה היתרון של XOR שמאפשר לאותה פונקציה להצפין ולפענח?
3. מה החולשה המרכזית של ההצפנה הזו?

---

## 1.3 `net_utils.py` — שכבת ההודעות (~71 שורות)

**תפקיד:** `send_msg` ו-`recv_msg` — הדרך שכל הודעה נשלחת ומתקבלת. משתמש ב-crypto.

**הבעיה שהוא פותר:** TCP הוא **זרם** בייטים, לא הודעות. אם שלחת "שלום" ו"עולם", הצד השני יכול לקבל "שלוםעו" ואז "לם". צריך **גבול הודעה** — כאן זה תו `\n` בסוף כל הודעה.

```python
from crypto import encrypt, decrypt

def send_msg(conn, data):
    # נרמול: רשימה/מילון/מחרוזת → מחרוזת אחת
    if isinstance(data, list):
        data = '|'.join(str(x) for x in data)        # ["CMD","SHOT"] → "CMD|SHOT"
    elif isinstance(data, dict):
        data = '|'.join(f"{k}={v}" for k, v in data.items())
    encrypted = encrypt(data)
    conn.sendall((encrypted + "\n").encode("utf-8"))  # שולח + \n

def recv_msg(conn):
    buf = bytearray()
    while True:
        chunk = conn.recv(4096)        # קורא עד 4096 בייט
        if not chunk:
            return None                # חיבור נסגר
        buf.extend(chunk)
        if b"\n" in buf:               # יש הודעה שלמה?
            line, _ = buf.split(b"\n", 1)
            decrypted = decrypt(line.decode("utf-8").strip())
            return decrypted.split('|')   # "OK|data" → ["OK","data"]
```

**הפרוטוקול (דוגמאות):**
```
מנהל שולח:  "CMD|SCREENSHOT|"   →  סוכן מחזיר: "OK|<base64_png>"
מנהל שולח:  "CMD|SHELL|dir"     →  סוכן מחזיר: "OK|<פלט>"
מנהל שולח:  "CMD|POWER|SHUTDOWN" → סוכן מחזיר: "OK"
```

**שאלות לתרגול:**
1. למה צריך את ה-`\n`? מה הבעיה שהוא פותר? *(TCP = זרם, אין גבולות הודעה)*
2. מה `recv_msg` מחזיר אם החיבור נסגר? *(None)*
3. איך הודעה ארוכה מ-4096 בייט מתקבלת? *(נצברת ב-buf על פני כמה recv)*

---

# 🗄️ רמה 2 — מסד הנתונים

## 2.1 `my_connector.py` — כל הקשר עם MySQL (~260 שורות)

**תפקיד:** כל הפעולות מול מסד הנתונים — התחברות, הרשמה, יצירת טבלאות, גיבוב סיסמאות.
**עדכון אחרון:** נוסף **מצב לא־מקוון** — אם אין שרת MySQL, המערכת לא קורסת.

```python
import hashlib
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

# אם הדרייבר לא מותקן — לא קורסים, עוברים למצב לא-מקוון
try:
    import mysql.connector
    _MYSQL_DRIVER = True
except ImportError:
    mysql = None
    _MYSQL_DRIVER = False

DB_CONFIG = {'host': DB_HOST, 'user': DB_USER,
             'password': DB_PASSWORD, 'database': DB_NAME}

def get_connection():
    if not _MYSQL_DRIVER:
        raise RuntimeError("offline mode")
    return mysql.connector.connect(**DB_CONFIG)

def db_available():
    """בדיקה מהירה אם שרת MySQL זמין."""
    if not _MYSQL_DRIVER:
        return False
    try:
        conn = mysql.connector.connect(host=DB_CONFIG['host'], user=DB_CONFIG['user'],
                                       password=DB_CONFIG['password'], connection_timeout=3)
        conn.close()
        return True
    except Exception:
        return False
```

**שלוש הטבלאות:**
```sql
users          → user_id, username, password(SHA-256), created_at, last_login, is_active
user_machines  → id, username, ip_address, login_time          (יומן כניסות)
saved_targets  → id, owner_username, computer_name, ip_address, mac_address  (מועדפים)
```

**גיבוב סיסמאות:**
```python
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()   # "mypass" → "a665..." (64 תווי hex)

def verify_password(plain, hashed) -> bool:
    return hashlib.sha256(plain.encode('utf-8')).hexdigest() == hashed
```
הסיסמה **לעולם לא נשמרת כטקסט** — רק ה-hash. גיבוב חד-כיווני: אי אפשר לשחזר.

**התחברות + הגנה מ-SQL Injection:**
```python
def login(username, password):
    cursor.execute("SELECT * FROM users WHERE username=%s", (username,))   # %s = פרמטר בטוח!
    row = cursor.fetchone()
    if row and verify_password(password, row['password']):
        cursor.execute("UPDATE users SET last_login=NOW() WHERE username=%s", (username,))
        return {'success': True, 'username': username}
    return {'success': False, 'message': 'Invalid credentials'}
```
**ה-`%s` הוא ההגנה:** הקלט נשלח כ**ערך** נפרד, לא משורשר לתוך ה-SQL → הזרקה בלתי אפשרית.

**מושגי מפתח:**
- כל פונקציה פותחת חיבור, עובדת, וסוגרת — פשוט ובטוח.
- `cursor(dictionary=True)` — מחזיר שורה כ-dict (`row['password']`) במקום tuple.
- `db_available()` — מאפשר למסך הכניסה לדעת אם להיכנס למצב לא־מקוון.

**שאלות לתרגול:**
1. למה הסיסמה נשמרת כ-SHA-256 ולא כטקסט? *(גיבוב חד-כיווני, גם DBA לא רואה אותה)*
2. מה ההגנה מ-SQL Injection ואיך היא עובדת? *(פרמטרים %s — קלט כערך לא כקוד)*
3. מה החולשה של גיבוב בלי salt? *(שתי סיסמאות זהות = אותו hash)*

---

# 🚪 רמה 3 — זרם הכניסה

## 3.1 `login_page.py` — מסך כניסה והרשמה (~185 שורות)

**תפקיד:** המסך הראשון. שני פאנלים: התחברות (שמאל) והרשמה (ימין).
**עדכון אחרון:** אם אין מסד נתונים → נכנסים ב**מצב לא־מקוון** במקום להיתקע.

```python
def handle_login(self):
    u = self.login_user.get().strip()
    p = self.login_pass.get()
    if not u or not p:
        messagebox.showerror("Error", "Fill all fields"); return

    res = login(u, p)                          # קורא ל-my_connector
    if res.get('success'):
        try: save_user_machine(u)
        except Exception: pass
        self._enter(u)                          # נכנס למערכת
    elif res.get('message') == 'Invalid credentials':
        messagebox.showerror("Failed", "Invalid credentials")
    else:
        # אין מסד נתונים → מצב לא-מקוון (כל הפיצ'רים עובדים בלי DB)
        messagebox.showinfo("Offline Mode", "אין חיבור למסד נתונים — נכנס במצב לא-מקוון.")
        self._enter(u)

def _enter(self, username):
    self.destroy()                              # סוגר את חלון הכניסה
    import launcher
    launcher.ControlItLauncher(username).mainloop()
```

**מושגי מפתח:**
- `self.destroy()` סוגר את החלון לפני שפותחים את הבא — שלא יהיו שני חלונות ראשיים.
- מצב לא־מקוון: ההבחנה היא לפי ההודעה — `'Invalid credentials'` = סיסמה שגויה (DB עובד); כל הודעה אחרת = DB לא זמין → מצב לא־מקוון.

**שאלות לתרגול:**
1. איך הקוד מבדיל בין "סיסמה שגויה" ל"אין מסד נתונים"? *(לפי תוכן ההודעה)*
2. למה `self.destroy()` לפני פתיחת ה-launcher?
3. מה קורה למשתמש שמוריד את ה-EXE בלי MySQL? *(נכנס במצב לא-מקוון, הכל עובד)*

---

## 3.2 `launcher.py` — בחירת מצב (~84 שורות)

**תפקיד:** שני כפתורים — ADMIN או USER.

```python
def launch_admin(self):
    import main_menu                    # import מקומי (lazy) — לא טוען מה שלא צריך
    self.destroy()
    main_menu.CyberDashboard(self.username).mainloop()

def launch_user(self):
    import agent_gui
    self.destroy()
    agent_gui.AgentApp().mainloop()
```

**למה ה-`import` בתוך הפונקציה?** `main_menu` גורר את PIL ו-`agent_gui` פותח sockets. אין סיבה לטעון את שניהם כשבוחרים רק אחד (lazy import).

---

## 3.3 `main.py` — נתב ה-EXE (~65 שורות)

**תפקיד:** כשהמערכת ארוזה כ-EXE יחיד, אין קבצי `.py` נפרדים. main.py מנתב לפי פרמטר.

```python
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "agent":        AgentApp().mainloop()
    elif mode == "login":      LoginApp().mainloop()
    elif mode == "controller": CyberDashboard(sys.argv[2]).mainloop()
    elif mode == "launcher":   ControlItLauncher(sys.argv[2]).mainloop()
    else:                      LoginApp().mainloop()    # ברירת מחדל
```
כל הקוד עטוף ב-`try/except` שמציג חלון שגיאה — ב-EXE עם `--windowed` אין קונסול, אז בלי זה קריסה הייתה שקטה.

**מושג מפתח — `sys.frozen`:**
```python
if getattr(sys, 'frozen', False):   # True רק כש-EXE
    subprocess.Popen([sys.executable, "agent"])     # ControlIt.exe agent
else:                               # פיתוח רגיל
    subprocess.Popen(["python", "agent_gui.py"])
```

---

# ❤️ רמה 4 — הלב

## 4.1 `agent_gui.py` — המחשב הנשלט (~249 שורות)

**תפקיד:** רץ על המחשב שנשלטים עליו. 3 מחלקות.

### מחלקה 1: `UDPBroadcaster` — "אני כאן!"
```python
class UDPBroadcaster(threading.Thread):
    def run(self):
        sock = socket.socket(AF_INET, SOCK_DGRAM)
        sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)    # מתיר שידור broadcast
        while not self.stop_flag:
            msg = f"user|{socket.gethostname()}|{socket.gethostbyname(...)}"
            sock.sendto(msg.encode(), ("<broadcast>", 5556))   # לכל הרשת
            time.sleep(3)
```
משדר `"user|DESKTOP-ABC|192.168.1.5"` כל 3 שניות לכל המחשבים ברשת.

### מחלקה 2: `CommandServer` — מקבל פקודות
```python
class CommandServer(threading.Thread):
    def run(self):
        server = socket.socket(AF_INET, SOCK_STREAM)
        server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)  # מונע "Address in use"
        server.bind(("0.0.0.0", 5555))                  # מאזין מכל כתובת
        server.listen(5)
        while not self.stop_flag:
            server.settimeout(1)                # כל שנייה בודק stop_flag
            client, addr = server.accept()
            threading.Thread(target=self.handle_client, args=(client,addr)).start()

    def process_command(self, msg):             # msg = ["CMD","SHELL","dir"]
        action = msg[1]
        if   action == "SCREENSHOT": return self.do_screenshot()
        elif action == "SHELL":      return self.do_shell(msg[2])
        elif action == "SYSINFO":    return self.do_sysinfo()
        elif action == "MSG":        return self.do_message(msg[2])
        elif action == "POWER":      return self.do_power(msg[2])
        return ["ERROR", "Unknown action"]      # תמיד עונה!
```

### חמשת המבצעים:
```python
def do_screenshot(self):
    img = ImageGrab.grab()                    # צילום מסך (PIL)
    buffer = io.BytesIO()                     # buffer בזיכרון (לא קובץ!)
    img.save(buffer, format="PNG")
    return ["OK", base64.b64encode(buffer.getvalue()).decode()]

def do_shell(self, cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True,
                            text=True, timeout=10)        # 3 הגנות
    return ["OK", (result.stdout + result.stderr)[:2000]]  # חיתוך ל-2000

def do_power(self, action):
    if action == "SHUTDOWN": os.system("shutdown /s /t 10")   # כיבוי תוך 10 שניות
    elif action == "RESTART": os.system("shutdown /r /t 10")
    return ["OK"]
```

**מושגי מפתח:**
- `SO_BROADCAST` — בלי הדגל, ה-OS חוסם שליחה לכתובת broadcast.
- `SO_REUSEADDR` — מאפשר הפעלה מחדש מיד בלי לחכות ש-5555 ישתחרר (TIME_WAIT).
- `settimeout(1)` על accept — כדי שהלולאה תבדוק stop_flag ותוכל להיסגר.
- thread לכל לקוח — מנהל איטי לא חוסם אחרים.

**שאלות לתרגול:**
1. למה `SO_BROADCAST`? *(בלעדיו אי אפשר לשדר לכל הרשת)*
2. למה `timeout=10` ו-`[:2000]` ב-do_shell? *(נגד פקודה תקועה ונגד הצפת פלט)*
3. למה צילום מסך נשמר ל-buffer ולא לקובץ? *(לא להשאיר עקבות על הדיסק הנשלט)*

---

## 4.2 `main_menu.py` — לוח המנהל (~373 שורות, הכי מורכב)

**תפקיד:** לוח הבקרה של המנהל. גילוי מחשבים + 6 כפתורי פעולה.

### `UDPListener` — מאזין לשידורים
```python
class UDPListener(threading.Thread):
    def run(self):
        sock.bind(("0.0.0.0", 5556))            # מאזין ל-broadcasts
        while not self.stop_flag:
            data, addr = sock.recvfrom(1024)
            self.callback(addr[0], info)         # מודיע ל-Dashboard
```

### `_on_discovery` + `refresh_agents` — רשימת מחשבים חיה
```python
def _on_discovery(self, ip, info):
    if info.get('role') == 'user':
        self.agents[ip] = {'ip': ip, 'name': info['name'],
                           'last_seen': time.time()}      # ← מתי נראה לאחרונה
        self.after(0, self.refresh_agents)

def refresh_agents(self):
    now = time.time()
    stale = [ip for ip, info in self.agents.items()
             if now - info['last_seen'] > AGENT_TIMEOUT_SEC]   # לא שודר 10 שניות
    for ip in stale:
        del self.agents[ip]                      # מוחק מי שנעלם
```

### `send_command` + threading — לב הפעולות
```python
def send_command(self, cmd):
    if not self.agent_sock:
        self._connect_agent()                    # מתחבר רק כשצריך (lazy)
    send_msg(self.agent_sock, cmd)
    return recv_msg(self.agent_sock)

def get_sysinfo(self):                           # תבנית של כל כפתור
    def _thread():
        resp = self.send_command("CMD|SYSINFO|")
        self.after(0, lambda: messagebox.showinfo("Info", resp[1]))
    threading.Thread(target=_thread, daemon=True).start()
```

**שני המושגים הכי חשובים בקובץ הזה:**
- **למה thread לכל פעולה?** `send_command` מחכה לתשובה מהרשת. בלי thread נפרד — **כל החלון קופא** עד שהתשובה מגיעה.
- **למה `self.after(0, func)`?** tkinter **לא thread-safe** — אסור לגעת ב-GUI מ-thread אחר. `after(0, func)` מבקש מה-thread הראשי להריץ את func בהזדמנות הקרובה. זה הכלל שמונע קריסות אקראיות.

**שאלות לתרגול:**
1. למה כל פעולת רשת רצה ב-thread נפרד? *(שה-GUI לא יקפא)*
2. מה `self.after(0,...)` עושה ולמה הוא הכרחי? *(עדכון GUI בטוח מ-thread)*
3. מה גורם למחשב שכבה "להיעלם" מהרשימה? *(refresh_agents מוחק last_seen > 10 שניות)*

---

# 🧠 חלק 3 — מושגים חוצי-קבצים (חובה להגנה)

| מושג | בקצרה |
|------|-------|
| **TCP מול UDP** | TCP=אמין+מסודר (פקודות). UDP=מהיר+broadcast (גילוי). |
| **Thread** | חוט ביצוע נפרד. כל פעולת רשת בו, שה-GUI לא יקפא. |
| **daemon=True** | thread שמת עם התוכנית. בלעדיו — תהליך רפאים שתופס פורט. |
| **self.after(0,)** | הדרך היחידה לעדכן GUI מתוך thread (tkinter לא thread-safe). |
| **SHA-256** | גיבוב חד-כיווני. לסיסמאות (במסד) ולגזירת מפתח (בהצפנה). |
| **XOR** | הצפנה דו-כיוונית: אותה פעולה מצפינה ומפענחת. |
| **Base64** | ממיר בייטים שבורים לטקסט בטוח לשליחה. |
| **%s (פרמטרים)** | ההגנה מ-SQL Injection — קלט כערך, לא כקוד. |
| **socket** | נקודת קצה לתקשורת. `SOCK_STREAM`=TCP, `SOCK_DGRAM`=UDP. |
| **lazy import** | import בתוך פונקציה — טוען רק מה שצריך, כשצריך. |

---

# ❓ חלק 4 — בנק שאלות הגנה

**ש: הסבר את מסע פקודת Screenshot מקצה לקצה.**
ת: הכפתור מפעיל thread → `send_command("CMD|SCREENSHOT|")` → `send_msg` מצפין ב-XOR+Base64 ושולח עם `\n` → הסוכן ב-`recv_msg` מפענח ומפצל → `process_command` מנתב ל-`do_screenshot` → צילום, דחיסת PNG, Base64 → התשובה `["OK", <תמונה>]` חוזרת באותו צינור → המנהל מפענח ומציג בחלון.

**ש: למה XOR ולא AES?**
ת: בחירה מודעת — רציתי לממש בעצמי ולהבין כל בייט, בלי תלות חיצונית. אני יודע את המגבלה (מפתח קבוע בקוד) ותיעדתי שדרוג ל-AES.

**ש: מה קורה אם שני מנהלים מתחברים לאותו סוכן?**
ת: עובד — כל חיבור מקבל thread נפרד (`handle_client`). אין נעילה, וזו מגבלה מתועדת.

**ש: מה החולשה הכי גדולה במערכת?**
ת: ערוץ הפקודות לא דורש אימות — מי שעל ה-LAN ומכיר את הפרוטוקול והמפתח (גלויים בקוד) יכול לשלוח פקודות בלי login. פתרון מתוכנן: token חתום לכל פקודה.

**ש: למה MySQL ולא SQLite?**
ת: MySQL הוא מסד מבוסס-שרת שמרכז את כל הנתונים במקום אחד — חשוב במערכת רב-תחנתית. ניסיתי SQLite באמצע הפיתוח וחזרתי. (בגרסה האחרונה: אם אין MySQL, יש מצב לא־מקוון.)

**ש: מה ההבדל בין `subprocess.run` ל-`subprocess.Popen`?**
ת: `run` מחכה שהתהליך יסתיים ומחזיר תוצאה (do_shell). `Popen` מריץ ברקע ולא מחכה (פתיחת חלונות).

---

# 📝 חלק 5 — סיכום מהיר לפני בחינה

1. `login_page` → `my_connector.login()` → `launcher` → admin/user
2. **סוכן** פותח TCP server (5555) + UDP broadcast (5556)
3. **מנהל** מאזין UDP → מגלה סוכן → מתחבר TCP 5555
4. **פקודה** = encrypt → send → recv → decrypt → process → encrypt תשובה → send
5. **crypto** = SHA-256 (מפתח) + XOR + Base64
6. **DB** = MySQL, סיסמה = SHA-256, queries = `%s` פרמטרים
7. **כל פעולת רשת** = thread נפרד + `self.after(0,)` לעדכון GUI

---

> 💡 **טיפ אחרון:** הדרך הכי טובה ללמוד — פתח את הקובץ ב-PyCharm, פתח את המדריך הזה לידו,
> והרץ כל חלק (`py agent_gui.py`) כדי לראות אותו חי. אחרי כל רמה — תן ל-AI לשאול אותך
> את שאלות התרגול וענה בלי להציץ.
