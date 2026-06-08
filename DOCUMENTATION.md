# ControlIt — תיעוד מלא לכל הקוד

> קובץ זה מסביר **כל קובץ, כל מחלקה, וכל פונקציה** בפרויקט.  
> קרא אותו כדי להכין את עצמך לבחינה ולהסביר לכל אחד מה הפרויקט עושה.

---

## 🗺️ ארכיטקטורה — תמונת כלל

```
login_page.py
    ↓  (אחרי login מוצלח)
launcher.py
    ├── ADMIN → main_menu.py (CyberDashboard)
    └── USER  → agent_gui.py (AgentApp)

תקשורת:
  Admin ←──TCP 5555──→ Agent   (פקודות מוצפנות)
  Admin ←──UDP 5556──← Agent   (גילוי אוטומטי)
  Admin ←──TCP 5001──→ Agent   (העברת קבצים)
```

**עיקרון מרכזי:** אין שרת ביניים (relay).  
ה-Admin מתחבר **ישירות** ל-Agent ברשת ה-LAN.

---

## 📁 מפת קבצים

| קובץ | תפקיד |
|------|--------|
| `login_page.py` | מסך כניסה + הרשמה |
| `launcher.py` | בחירת מצב Admin/User |
| `main_menu.py` | לוח בקרה של ה-Admin |
| `agent_gui.py` | תוכנת המחשב המנוהל |
| `crypto.py` | הצפנה ופענוח (XOR + SHA-256) |
| `net_utils.py` | שליחה/קבלה מוצפנת דרך socket |
| `my_connector.py` | כל הפעולות מול MySQL |
| `config.py` | הגדרות גלובליות (ports, DB) |
| `main.py` | נתב ל-EXE הבנוי |
| `.env` | סיסמאות וסביבה (לא עולה ל-GitHub) |

---

## 🔐 crypto.py — הצפנה

```python
import hashlib, base64

_SECRET_PASSWORD = b"ControlIt-SecretKey-2024"
_raw_key = hashlib.sha256(_SECRET_PASSWORD).digest()  # → 32 bytes קבועים
```

### איך זה עובד

1. **SHA-256** — ממיר את המפתח הסודי ל-32 bytes קבועים.  
   `"ControlIt-SecretKey-2024"` → `[0xA3, 0x7F, ...]` (32 מספרים)

2. **XOR** — מצפין כל byte של ההודעה עם byte תואם מהמפתח:
   ```
   הודעה:  H    e    l    l    o
   מפתח:   A3   7F   C2   ...  (חוזר על עצמו)
   XOR:    EB   1B   AE   ...  (הצופן)
   ```
   פלא של XOR: **אותה פעולה מצפינה ומפענחת!**
   ```python
   encrypt("hello") → decrypt(encrypt("hello")) == "hello"
   ```

3. **Base64** — ממיר את ה-bytes לתווים שאפשר לשלוח בטקסט:
   ```
   [0xEB, 0x1B, ...] → "6xs..."  (מחרוזת ASCII)
   ```

### פונקציות
```python
def encrypt(text: str) -> str:
    data = text.encode('utf-8')      # str → bytes
    result = bytearray()
    for i, byte in enumerate(data):
        result.append(byte ^ key[i % len(key)])   # XOR
    return base64.b64encode(bytes(result)).decode('utf-8')  # → str

def decrypt(text: str) -> str:
    data = base64.b64decode(text.encode('utf-8'))  # str → bytes
    result = bytearray()
    for i, byte in enumerate(data):
        result.append(byte ^ key[i % len(key)])   # XOR (זהה!)
    return bytes(result).decode('utf-8')
```

### חולשה ידועה
המפתח זהה לכולם וקבוע בקוד. מי שיודע שהפרוטוקול מתחיל ב-`CMD|`  
יכול לשחזר את המפתח (**Known Plaintext Attack**).  
בגרסה עתידית: AES-256 + IV אקראי.

---

## 📡 net_utils.py — שליחה וקבלה

### למה צריך את הקובץ הזה?
TCP מוסר **streams** (זרם bytes), לא **הודעות**. אם שלחת 100 bytes, recv() עשוי להחזיר 50 bytes פעמיים. צריך **מנגנון גבולות הודעה**. הפתרון כאן: `\n` בסוף כל הודעה.

```
[הודעה מוצפנת ב-Base64]\n
[הודעה מוצפנת ב-Base64]\n
```

### send_msg
```python
def send_msg(conn, data):
    # המרה לstring
    if isinstance(data, list):
        data = '|'.join(str(x) for x in data)   # ["CMD","SHOT"] → "CMD|SHOT"
    elif isinstance(data, dict):
        data = '|'.join(f"{k}={v}" for k, v in data.items())
    
    encrypted = encrypt(data)
    conn.sendall((encrypted + "\n").encode("utf-8"))  # שולח + newline
```

### recv_msg
```python
def recv_msg(conn):
    buf = bytearray()
    while True:
        chunk = conn.recv(4096)   # קורא עד 4096 bytes
        if not chunk:
            return None           # חיבור נסגר
        buf.extend(chunk)
        
        if b"\n" in buf:          # קיבלנו הודעה שלמה?
            line, _ = buf.split(b"\n", 1)
            decrypted = decrypt(line.decode('utf-8').strip())
            return decrypted.split('|')   # "OK|data" → ["OK", "data"]
```

### פרוטוקול — דוגמאות
```
Admin שולח:   "CMD|SCREENSHOT|"
Agent מחזיר: "OK|<base64_png>"

Admin שולח:   "CMD|SHELL|dir"  
Agent מחזיר: "OK| Volume in drive C..."

Admin שולח:   "CMD|POWER|SHUTDOWN"
Agent מחזיר: "OK"
```

---

## 🗄️ my_connector.py — מסד נתונים

### חיבור
```python
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME

DB_CONFIG = {'host': DB_HOST, 'user': DB_USER, 'password': DB_PASSWORD, 'database': DB_NAME}

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)
```
כל פונקציה פותחת חיבור, עושה את העבודה, וסוגרת. זה **פשוט ובטוח** — אין חיבור תקוע.

### טבלאות
```sql
users          → user_id, username, password(SHA-256), created_at, last_login, is_active
user_machines  → id, username, ip_address, login_time
saved_targets  → id, owner_username, computer_name, ip_address, mac_address, saved_at
```

### hash_password
```python
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()
    # "mypass" → "a665a45920422f9d..." (64 תווים hex)
```
**למה SHA-256 ולא bcrypt?**  
bcrypt בטוח יותר (יש לו salt + איטי מכוון), אבל SHA-256 מספיק לפרויקט בית ספרי.  
**חולשה:** אין salt — אותה סיסמה תמיד = אותו hash (Rainbow Tables).

### register
```python
def register(username, password):
    if user_exists(username):
        return {'success': False, 'message': 'User exists'}
    hashed = hash_password(password)
    cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
    # %s = parameterized query → מונע SQL Injection!
```

### login
```python
def login(username, password):
    cursor.execute("SELECT * FROM users WHERE username=%s", (username,))
    row = cursor.fetchone()
    if row and verify_password(password, row['password']):
        cursor.execute("UPDATE users SET last_login=NOW() WHERE username=%s", (username,))
        return {'success': True, 'username': username}
    return {'success': False, 'message': 'Invalid credentials'}
```

---

## 🖥️ login_page.py — מסך כניסה

### מבנה
```
LoginApp (tk.Tk)
├── LEFT PANEL  → Login (username + password + SIGN IN button)
└── RIGHT PANEL → Register (username + password + confirm + SIGN UP button)
```

### handle_login
```python
def handle_login(self):
    u = self.login_user.get().strip()
    p = self.login_pass.get()
    
    res = login(u, p)                    # קורא ל-my_connector
    if res.get('success'):
        save_user_machine(u)             # שומר IP ב-user_machines
        self.destroy()                   # סוגר את חלון ה-login
        import launcher
        launcher.ControlItLauncher(u).mainloop()   # פותח launcher
```

### handle_register
```python
def handle_register(self):
    if p != c:                           # סיסמה ≠ אישור
        messagebox.showerror("Error", "Passwords don't match")
        return
    
    res = register(u, p)
    if res.get('success'):
        # אחרי הרשמה: ממלא אוטומטית את שם המשתמש בLogin
        self.login_user.insert(0, u)
```

---

## 🚀 launcher.py — בחירת מצב

```
ControlItLauncher (tk.Tk)
├── ADMIN button → launch_admin()
└── USER button  → launch_user()
```

```python
def launch_admin(self):
    import main_menu
    self.destroy()                    # סוגר את ה-launcher
    app = main_menu.CyberDashboard(self.username)
    app.mainloop()

def launch_user(self):
    import agent_gui
    self.destroy()
    app = agent_gui.AgentApp()
    app.mainloop()
```

**דגש:** `self.destroy()` לפני `mainloop()` — חשוב שלא יהיו שני חלונות ראשיים!

---

## 👤 agent_gui.py — מחשב מנוהל

### UDPBroadcaster
```python
class UDPBroadcaster(threading.Thread):
    def run(self):
        sock = socket.socket(AF_INET, SOCK_DGRAM)
        sock.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)   # מאפשר broadcast
        while not self.stop_flag:
            msg = f"user|{socket.gethostname()}|{socket.gethostbyname(...)}"
            sock.sendto(msg.encode(), ("<broadcast>", 5556))  # לכולם ברשת!
            time.sleep(3)
```
שולח `"user|DESKTOP-ABC|192.168.1.5"` כל 3 שניות לכל המחשבים ברשת.

### CommandServer
```python
class CommandServer(threading.Thread):
    def run(self):
        server = socket.socket(AF_INET, SOCK_STREAM)
        server.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)  # מונע "Address in use"
        server.bind(("0.0.0.0", 5555))                   # מאזין מכל כתובת
        server.listen(5)                                  # תור של 5 חיבורים

        while not self.stop_flag:
            server.settimeout(1)         # כל שנייה בודק stop_flag
            client, addr = server.accept()
            threading.Thread(target=self.handle_client, args=(client,addr)).start()
```

**למה `SO_REUSEADDR`?**  
בלי זה, אחרי סגירה של התוכנה, פורט 5555 נשאר "תפוס" כמה שניות (TIME_WAIT).  
עם הדגל — ניתן להפעיל מחדש מיד.

### process_command
```python
def process_command(self, msg):
    # msg הגיע כ-list אחרי split('|')
    # לדוגמה: ["CMD", "SHELL", "dir"]
    cmd = msg[0]        # "CMD"
    
    if cmd == "CMD" and len(msg) > 1:
        action = msg[1]
        
        if action == "SCREENSHOT":
            return self.do_screenshot()
        elif action == "SHELL" and len(msg) > 2:
            return self.do_shell(msg[2])      # msg[2] = הפקודה
        elif action == "SYSINFO":
            return self.do_sysinfo()
        elif action == "MSG" and len(msg) > 2:
            return self.do_message(msg[2])
        elif action == "POWER" and len(msg) > 2:
            return self.do_power(msg[2])
```

### do_screenshot
```python
def do_screenshot(self):
    img = ImageGrab.grab()              # PIL — צולם מסך כ-Image object
    buffer = io.BytesIO()               # buffer בזיכרון (לא קובץ)
    img.save(buffer, format="PNG")      # שומר PNG ל-buffer
    img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return ["OK", img_data]             # מחרוזת Base64 — בטוחה לשליחה
```

### do_shell
```python
def do_shell(self, cmd):
    result = subprocess.run(
        cmd, shell=True,          # מריץ דרך cmd.exe
        capture_output=True,      # לוכד stdout + stderr
        text=True,                # מחזיר str ולא bytes
        timeout=10                # מגביל ל-10 שניות (מונע hang)
    )
    output = result.stdout + result.stderr
    return ["OK", output[:2000]]  # מגביל ל-2000 תווים
```

### do_power
```python
def do_power(self, action):
    if action == "SHUTDOWN":
        os.system("shutdown /s /t 10")   # כיבוי Windows תוך 10 שניות
    elif action == "RESTART":
        os.system("shutdown /r /t 10")   # restart תוך 10 שניות
```
`/s` = shutdown, `/r` = restart, `/t 10` = אחרי 10 שניות.

---

## 🎛️ main_menu.py — לוח בקרה Admin

### UDPListener
```python
class UDPListener(threading.Thread):
    def run(self):
        sock.bind(("0.0.0.0", 5556))   # מאזין ל-broadcasts
        while not self.stop_flag:
            data, addr = sock.recvfrom(1024)
            # "user|DESKTOP-ABC|192.168.1.5" → info dict
            self.callback(addr[0], info)   # קורא ל-CyberDashboard._on_discovery
```

### _on_discovery
```python
def _on_discovery(self, ip, info):
    if info.get('role') == 'user':
        self.agents[ip] = {
            'ip': ip,
            'name': info['name'],
            'last_seen': time.time()   # ← חשוב! מתי נראה לאחרונה
        }
        self.after(0, self.refresh_agents)   # עדכון GUI מ-thread
```

### refresh_agents — ניקוי agents שנכבו
```python
def refresh_agents(self):
    now = time.time()
    stale = [ip for ip, info in self.agents.items()
             if now - info['last_seen'] > AGENT_TIMEOUT_SEC]  # לא שלח broadcast מעל 10 שניות
    for ip in stale:
        del self.agents[ip]
    # ...מרענן רשימה
```

### send_command
```python
def send_command(self, cmd):
    if not self.agent_sock:
        self._connect_agent()        # מתחבר רק כשצריך (lazy connection)
    send_msg(self.agent_sock, cmd)
    return recv_msg(self.agent_sock)
```

### threading בפקודות
```python
def get_sysinfo(self):
    def _thread():
        resp = self.send_command("CMD|SYSINFO|")
        self.after(0, lambda: messagebox.showinfo("System Info", resp[1]))
    threading.Thread(target=_thread, daemon=True).start()
```
**למה thread?** `send_command` מחכה לתשובה מהרשת — בלי thread, ה-GUI קופא עד שה-Agent עונה.  
**למה `self.after(0, ...)`?** tkinter לא thread-safe — אסור לעדכן GUI מ-thread. `.after(0, func)` מבקש מה-GUI thread להריץ את `func` בהזדמנות הקרובה.

---

## 🔄 main.py — נתב ה-EXE

```python
def main():
    mode = sys.argv[1]   # "agent" / "login" / "controller" / "script" / "transfer"
    
    if mode == "agent":
        AgentApp().mainloop()
    elif mode == "login":
        LoginApp().mainloop()
    elif mode == "controller":
        username = sys.argv[2]
        CyberDashboard(username).mainloop()
    ...
```

**למה צריך את זה?**  
כש-PyInstaller בונה EXE, יש רק קובץ אחד. אי אפשר להריץ `python agent_gui.py` נפרד.  
הפתרון: `main.py` הוא "נתב" — מקבל mode כארגומנט ומפעיל את המחלקה המתאימה.

**dev mode vs frozen:**
```python
if getattr(sys, 'frozen', False):
    # EXE: sys.executable = ControlIt.exe
    subprocess.Popen([sys.executable, "agent"])   # → ControlIt.exe agent
else:
    # dev: subprocess.Popen(["python", "agent_gui.py"])
```

---

## 🔧 config.py — הגדרות מרכזיות

```python
import os
try:
    from dotenv import load_dotenv
    load_dotenv()   # טוען מ-.env אם קיים
except ImportError:
    pass

DB_HOST     = os.environ.get("DB_HOST",     "localhost")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "Liamfort5")
CMD_PORT    = int(os.environ.get("CMD_PORT", 5555))
AGENT_TIMEOUT_SEC = int(os.environ.get("AGENT_TIMEOUT_SEC", 10))
```

**יתרון:** אם רוצים לשנות port או סיסמה — משנים רק ב-`.env`.  
`.env` לא עולה ל-GitHub (יש ב-`.gitignore`) → הסיסמה לא זולגת.

---

## 🌊 זרימת נתונים — תרחישים מלאים

### תרחיש 1: Screenshot

```
Admin לוחץ Screenshot
  ↓
take_screenshot() → מריץ thread חדש
  ↓ (thread נפרד)
send_command("CMD|SCREENSHOT|")
  ↓ send_msg()
  encrypt("CMD|SCREENSHOT|") → Base64 מוצפן
  conn.sendall(encrypted + "\n")
  ↓ [ברשת TCP]
Agent מקבל ב-recv_msg()
  → decrypt → ["CMD","SCREENSHOT",""]
  ↓ process_command()
  action == "SCREENSHOT"
  ↓ do_screenshot()
  ImageGrab.grab() → PNG → Base64
  return ["OK", "<base64_data>"]
  ↓ send_msg() חזרה
  ↓ [ברשת TCP]
Admin recv_msg() → ["OK", "<base64_data>"]
  ↓ _screenshot_thread() המשך
  base64.b64decode → Image.open → ImageTk
  self.after(0, _show_screenshot)   ← GUI thread
  ↓
חלון עם screenshot נפתח
```

### תרחיש 2: Login

```
משתמש מקליד user+pass ולוחץ SIGN IN
  ↓
handle_login()
  login("alice", "1234")  ← my_connector
  ↓
  SELECT * FROM users WHERE username='alice'
  verify_password("1234", stored_hash)
    hashlib.sha256("1234") == stored_hash  ?
  ↓ כן
  UPDATE users SET last_login=NOW()
  return {'success': True}
  ↓
save_user_machine("alice")   ← שומר IP
self.destroy()               ← סוגר login window
launcher.ControlItLauncher("alice").mainloop()
```

### תרחיש 3: גילוי Agent

```
Agent מופעל
  ↓ UDPBroadcaster.run()
  כל 3 שניות:
  sendto("user|DESKTOP-ABC|192.168.1.5", ("<broadcast>", 5556))
  
Admin (main_menu) פועל
  ↓ UDPListener.run()
  recvfrom → "user|DESKTOP-ABC|192.168.1.5"
  callback(ip="192.168.1.5", info={name:"DESKTOP-ABC"})
  ↓ _on_discovery()
  agents["192.168.1.5"] = {..., last_seen: now}
  self.after(0, refresh_agents)   ← מוסיף לרשימה
  
כל 3 שניות: refresh_agents() מוחק agents ישנים (last_seen > 10 שניות)
```

---

## 🛡️ ניתוח אבטחה

| איום | הגנה קיימת | חולשה |
|------|-----------|-------|
| האזנה לרשת | XOR + Base64 | מפתח קבוע — חלש |
| גניבת DB | SHA-256 לסיסמאות | אין salt — Rainbow Tables |
| Replay Attack | אין | אין timestamp/nonce |
| גישה לא מורשית ל-Agent | LAN בלבד | כל מחשב ב-LAN יכול להתחבר |
| SQL Injection | Parameterized queries (`%s`) | ✅ מוגן לחלוטין |
| סיסמה ב-GitHub | `.env` + `.gitignore` | ✅ מוגן |

---

## ❓ שאלות בחינה נפוצות

**ש: מה ה-XOR עושה בהצפנה?**  
ת: XOR (או בלעדי) — אם שני הביטים זהים, התוצאה 0; אם שונים, 1.  
הפלא: `A XOR KEY XOR KEY = A` — אותה פעולה מצפינה ומפענחת.

**ש: למה Base64 אחרי XOR?**  
ת: XOR מוציא bytes אקראיים — חלקם לא ניתנים להדפסה ושבורים ב-JSON/TCP.  
Base64 ממיר כל 3 bytes ל-4 תווי ASCII — בטוחים לשליחה בכל פרוטוקול.

**ש: למה TCP לפקודות ו-UDP לגילוי?**  
ת: TCP — מבטיח הגעת ההודעה ובסדר הנכון (חשוב לפקודות).  
UDP — מהיר, מאפשר broadcast לכל המחשבים ברשת בו-זמנית (לא אפשרי ב-TCP).

**ש: למה `self.after(0, func)` ולא קריאה ישירה?**  
ת: tkinter לא thread-safe. אסור לעדכן widgets מ-thread שאינו ה-GUI thread.  
`.after(0, func)` מכניס את func לתור הevent loop של tkinter שרץ ב-main thread.

**ש: מה `daemon=True` בthread?**  
ת: Thread שמוגדר כ-daemon נהרג אוטומטית כשה-main thread נסגר.  
בלי זה — התוכנה לא תיסגר בגלל threads שנשארים פועלים ברקע.

**ש: מה `SO_REUSEADDR` עושה?**  
ת: אחרי סגירת socket, ה-OS שומר את הפורט במצב TIME_WAIT כמה שניות.  
`SO_REUSEADDR` מאפשר שימוש חוזר בפורט מיד — בלי להמתין.

**ש: מה ההבדל בין `subprocess.run` ל-`subprocess.Popen`?**  
ת: `run` — מחכה שהתהליך יסתיים ומחזיר תוצאה (משמש ב-do_shell).  
`Popen` — מריץ תהליך ברקע ולא מחכה (משמש לפתיחת חלונות).

**ש: מה `cursor(dictionary=True)` עושה?**  
ת: בלי זה: `cursor.fetchone()` מחזיר tuple — `(1, "alice", "hash123")`.  
עם זה: מחזיר dict — `{"user_id": 1, "username": "alice", "password": "hash123"}`.  
הרבה יותר קריא וברור.

**ש: מה `%s` בSQL ולמה לא f-string?**  
ת: `f"SELECT * FROM users WHERE username='{username}'"` — **מסוכן!**  
אם username = `alice' OR '1'='1` → SQL Injection = גישה לכל המשתמשים.  
`cursor.execute("...WHERE username=%s", (username,))` — MySQL מטפל בבריחה.

**ש: למה `.env` ולא לשים את הסיסמה ישר בקוד?**  
ת: אם ה-repo ציבורי ב-GitHub — כולם יראו את הסיסמה.  
`.env` לא עולה ל-GitHub (יש ב-`.gitignore`). הסיסמה נשארת מקומית.

---

## 🔌 פורטים — סיכום

| פורט | פרוטוקול | כיוון | תפקיד |
|------|----------|-------|--------|
| 5555 | TCP | Admin → Agent | פקודות (מוצפן XOR) |
| 5556 | UDP | Agent → כולם | גילוי אוטומטי ב-LAN |
| 5001 | TCP | Admin → Agent | העברת קבצים (לא מוצפן) |

---

## 📝 סיכום מהיר לפני בחינה

1. **login_page** → my_connector.login() → launcher
2. **launcher** → main_menu (Admin) / agent_gui (User)
3. **Agent** פותח TCP server על 5555 + UDP broadcast ל-5556
4. **Admin** מאזין ל-UDP → גלה Agent → מתחבר TCP ל-5555
5. **פקודה** = encrypt → send → recv → decrypt → process → encrypt תוצאה → send חזרה
6. **crypto** = SHA-256 key + XOR + Base64
7. **DB** = MySQL, סיסמה = SHA-256, queries = parameterized
