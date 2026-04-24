# ============================================================
#  net_utils.py - פונקציות תקשורת משותפות לכל חלקי המערכת
#  send_msg / recv_msg משמשות ב-relay_server, agent_gui, main_menu
# ============================================================

import json
from crypto import encrypt, decrypt


def send_msg(conn, data):
    """מצפין ושולח הודעת JSON (מסתיימת בשורה חדשה)"""
    if isinstance(data, dict):
        data = json.dumps(data)
    encrypted = encrypt(data)
    conn.sendall((encrypted + "\n").encode("utf-8"))


def recv_msg(conn):
    """
    מקבל ומפענח הודעת JSON עד לשורה חדשה.
    קורא בלוקים של 4096 בייט במקום בייט-בייט — יעיל הרבה יותר.
    """
    buf = bytearray()
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            return None
        buf.extend(chunk)
        if b"\n" in buf:
            line, _ = buf.split(b"\n", 1)
            text = bytes(line).decode("utf-8").strip()
            if not text:
                return None
            return json.loads(decrypt(text))
