# ControlIt - מדריך המשתמש

## 🎯 מה זה ControlIt?

**ControlIt** היא תוכנת בקרה מרחוק של מחשבים באותה רשת מקומית (LAN).
- **Admin** שולח פקודות
- **User** מקבל פקודות ומבצע אותן
- **אין צורך בserver חיצוני** - הכל ברשת המקומית

---

## ⚡ התחלה מהירה

### דרישות
- Python 3.8+
- Windows 7/10/11
- שתי מחשבים על אותה רשת WiFi/Ethernet

### התקנה
```bash
pip install -r requirements.txt
```

### הפעלה

#### מכונה 1 - Admin (מקום הבקרה)
```bash
python launcher.py
# בחר: ADMIN
```

#### מכונה 2 - User (מחשב לבקרה)
```bash
python launcher.py
# בחר: USER
# המחשב יחפש Relay בעצמו
# לחץ CONNECT
```

---

## 🎮 פקודות Admin (6 אפשרויות)

### 📷 **Screenshot** 
- צלם את מסך המחשב הרחוק

### ⌨️ **Remote Shell**
- הרץ פקודות (cmd.exe / PowerShell)
- דוגמה: `ipconfig`, `dir C:\`

### 📂 **File Transfer**
- שלח קבצים למחשב הרחוק

### 📊 **System Info**
- צפה ב: CPU, RAM, Disk, Network

### 💬 **Message**
- שלח הודעה/התראה

### ⏻ **Power**
- Shutdown / Restart

---

## 🔍 איך זה עובד?

```
1. User מרים את agent_gui.py
   └─ משדר: "אני כאן ב-192.168.1.5"

2. Admin מרים את main_menu.py  
   └─ שומע ורואה: "User ב-192.168.1.5"

3. Admin בוחר User ושולח פקודה
   └─ User מקבל ובצע ← Response

4. (אופציונלי) Relay server מנתב בקרות מחוץ לרשת
```

---

## ⚙️ הגדרות

### Relay Server (אופציונלי)
- אם רוצים בקרה **מחוץ לרשת המקומית**
- הרץ: `python relay_server.py`
- הוא משדר את עצמו ב-UDP 5556

### מסד נתונים
- **SQLite** - נוצר בעצמו
- שומר credentials כאן
- משומר ב: `<script_folder>/local.db`

### זיכרון מכונות
- **discovered_machines.json** - נשמר אוטומטית
- רשימת User machines שנמצאו
- נוטען בעת הפעלה הבאה

---

## 🔒 אבטחה

- ✅ כל הודעות מוצפנות (Fernet)
- ✅ סיסמאות מהוצפנות (bcrypt)
- ✅ אין העברת credentials
- ✅ פועל רק ברשת מקומית (כברירת מחדל)

---

## 🛠️ בניית EXE

```bash
python build.py
# ימשוך את הקבצים ל: dist/ControlIt.exe
```

---

## 📋 בדיקות

### בדוק את זה
- [ ] אם שתי מכונות על אותה רשת
- [ ] Admin רואה User תוך 3-5 שניות
- [ ] לחץ על כל כרטיס (6 סה"כ)
- [ ] Power popup מופיע
- [ ] discovered_machines.json נוצר
- [ ] לאחר restart - המחשבים זכורים

---

## ❌ אם משהו לא עובד

### Discovery לא עובד
- ✔️ בדוק: שתי מכונות על אותה רשת
- ✔️ בדוק: Windows Firewall מאפשר UDP 5556
- ✔️ אתחל מחדש את שתי האפליקציות

### לא יכול להתחבר
- ✔️ בדוק: IP של Relay בAgent
- ✔️ בדוק: `ping <relay_ip>` עובד
- ✔️ בדוק: relay_server.py רץ

### שגיאות בקטגוריות
- ✔️ וודא: תיקייה מקומית קיימת
- ✔️ וודא: הרשאות write בתיקייה
- ✔️ וודא: קובץ קיים במקום שצוין

---

## 📞 תמיכה

- מסד נתונים: `my_connector.py` (SQLite)
- הצפנה: `crypto.py` (Fernet)
- Discovery: `discovery_utils.py` (UDP)

---

## 🚀 הפעלה ייצור

### EXE קטן אחד
```bash
python build.py
# dist/ControlIt.exe - הפצה
```

### או כ-Scripts
```bash
python launcher.py  # Admin או User
```

---

## 📝 קובץ Log

- `launcher.py` - מציג errors בקונסול
- `main_menu.py` - errors בקונסול
- `agent_gui.py` - errors בקונסול

---

## ✨ יתרונות

✅ **אין צורך בserver חיצוני**
✅ **הכל אוטומטי** - auto-discovery
✅ **אין invite codes**
✅ **בטוח** - כל הודעות מוצפנות
✅ **פשוט** - 6 פקודות בלבד
✅ **מהיר** - TCP ישיר

---

## 🎯 Version: 1.0
**כל התוכנה מוכנה להפעלה.**

---

*עוזר: Claude | תאריך: 2026-04-24*
