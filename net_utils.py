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
