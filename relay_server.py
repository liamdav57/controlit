# ============================================================
#  relay_server.py - שרת ריליי מרכזי
#  מריצים אותו על שרת ציבורי (VPS / PC עם IP ציבורי)
#  כל ה-Agents וה-Controllers מתחברים אליו
#  השרת מנתב פקודות בין Controller לבין Agent
# ============================================================

import socket
import threading
import json
import uuid
import time
import queue
from net_utils import send_msg, recv_msg
from discovery_utils import DiscoveryBroadcaster

PORT = 5555

# רשימת ה-Users המחוברים
# id -> {"conn", "name", "os", "addr", "cmd_q", "resp_q", "connected_at"}
users = {}
users_lock = threading.Lock()


def gen_id():
    return str(uuid.uuid4())[:6].upper()


# ──────────────────────────────────────────
#  טיפול ב-Agent
# ──────────────────────────────────────────

def handle_user(conn, addr, init_msg):
    """
    כל User שמתחבר מקבל ID ייחודי ומחכה לפקודות.
    """
    agent_id = gen_id()
    cmd_q  = queue.Queue()
    resp_q = queue.Queue()

    info = {
        "conn":         conn,
        "name":         init_msg.get("name", f"PC-{agent_id}"),
        "os":           init_msg.get("os", "Unknown"),
        "addr":         addr[0],
        "cmd_q":        cmd_q,
        "resp_q":       resp_q,
        "connected_at": time.time(),
    }

    with users_lock:
        users[agent_id] = info

    send_msg(conn, {"status": "ok", "id": agent_id})
    print(f"[+] User: {info['name']} ({agent_id}) from {addr[0]}")

    try:
        while True:
            # ממתין לפקודה מהController (דרך התור)
            cmd = cmd_q.get()
            if cmd is None:
                break

            # שולח פקודה לאגנט
            send_msg(conn, {"type": "cmd", "data": cmd})

            # מקבל תשובה מהאגנט
            response = recv_msg(conn)
            if response is None:
                break

            resp_q.put(response)

    except Exception as e:
        print(f"[!] User error ({info['name']}): {e}")
    finally:
        with users_lock:
            users.pop(agent_id, None)
        conn.close()
        print(f"[-] User disconnected: {info['name']} ({agent_id})")


# ──────────────────────────────────────────
#  ניתוב פקודה לאגנט ספציפי
# ──────────────────────────────────────────

def route_cmd(agent_id, cmd_data, timeout=15):
    """שולח פקודה לאגנט ומחזיר את התשובה שלו"""
    with users_lock:
        agent = users.get(agent_id)
    if not agent:
        return {"error": "Agent offline"}
    try:
        agent["cmd_q"].put(cmd_data)
        response = agent["resp_q"].get(timeout=timeout)
        return response
    except queue.Empty:
        return {"error": "Timeout — agent did not respond"}
    except Exception as e:
        return {"error": str(e)}


# ──────────────────────────────────────────
#  טיפול ב-Controller
# ──────────────────────────────────────────

def handle_admin(conn, addr, init_msg):
    """
    Admin יכול לשלוח:
      {"action": "list"}                              — רשימת Users בעלי זכות גישה
      {"action": "cmd", "agent_id": X, "data": Y}   — פקודה ל-user
    """
    username = init_msg.get("username", "unknown")
    send_msg(conn, {"status": "ok"})
    print(f"[+] Admin: {username} from {addr[0]}")

    try:
        while True:
            msg = recv_msg(conn)
            if msg is None:
                break

            action = msg.get("action")

            if action == "list":
                # מחזיר את כל ה-Users המחוברים
                with users_lock:
                    agent_list = [
                        {
                            "id":      k,
                            "name":    v["name"],
                            "os":      v["os"],
                            "addr":    v["addr"],
                            "uptime":  int(time.time() - v["connected_at"]),
                        }
                        for k, v in users.items()
                    ]
                send_msg(conn, {"agents": agent_list})

            elif action == "cmd":
                agent_id = msg.get("agent_id")
                with users_lock:
                    agent = users.get(agent_id)
                if not agent:
                    send_msg(conn, {"error": "User not found"})
                    continue
                result = route_cmd(agent_id, msg.get("data", ""))
                send_msg(conn, result)

            else:
                send_msg(conn, {"error": f"Unknown action: {action}"})

    except Exception as e:
        print(f"[!] Admin error: {e}")
    finally:
        conn.close()
        print(f"[-] Admin disconnected: {addr[0]}")


# ──────────────────────────────────────────
#  קבלת חיבורים
# ──────────────────────────────────────────

def handle_connection(conn, addr):
    """מזהה האם החיבור הוא Agent או Controller לפי הודעת הפתיחה"""
    try:
        conn.settimeout(10)
        msg = recv_msg(conn)
        if not msg:
            conn.close()
            return
        conn.settimeout(None)

        role = msg.get("role")
        if role == "agent" or role == "user":
            handle_user(conn, addr, msg)
        elif role == "controller" or role == "admin":
            handle_admin(conn, addr, msg)
        else:
            conn.close()

    except Exception as e:
        print(f"[!] Connection error from {addr}: {e}")
        conn.close()


# ──────────────────────────────────────────
#  הפעלת השרת
# ──────────────────────────────────────────

def main():
    """מריץ את שרת הריליי — אפשר להפעיל כסקריפט עצמאי או מתוך ה-GUI"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", PORT))
    server.listen(100)

    my_ip = socket.gethostbyname(socket.gethostname())
    print("=" * 50)
    print("  ControlIt Relay Server")
    print(f"  Listening on port {PORT}")
    print(f"  Local IP: {my_ip}")
    print("=" * 50)

    # התחל שידור UDP כדי שמכונות ברשת יוכלו למצוא את השרת
    broadcaster = DiscoveryBroadcaster(
        role="relay",
        name="ControlIt-Relay",
        ip=my_ip,
        port=PORT
    )
    broadcaster.start()

    try:
        while True:
            try:
                conn, addr = server.accept()
                threading.Thread(target=handle_connection, args=(conn, addr), daemon=True).start()
            except Exception:
                break
    finally:
        broadcaster.stop()
        server.close()


if __name__ == "__main__":
    main()
