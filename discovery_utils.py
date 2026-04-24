# ============================================================
#  discovery_utils.py - גילוי עצמי של מכונות ברשת
#  משדרות UDP כל 3 שניות — Admin/User מאזינים ומאתרים אחד את השני
#  אין צורך בהקלדת IP, הכל אוטומטי
# ============================================================

import socket
import json
import threading
import time

BROADCAST_PORT = 5556
BROADCAST_INTERVAL = 3  # seconds


class DiscoveryBroadcaster:
    """משדרת את נוכחות המכונה לרשת המקומית"""

    def __init__(self, role, name, ip, port=5555):
        """
        role: "admin" או "user" או "relay"
        name: שם המכונה (hostname)
        ip: כתובת IP של המכונה ברשת המקומית
        port: הפורט שעליו מאזינה המכונה
        """
        self.role = role
        self.name = name
        self.ip = ip
        self.port = port
        self.running = False

    def start(self):
        """התחל לשדר"""
        self.running = True
        threading.Thread(target=self._broadcast_loop, daemon=True).start()

    def stop(self):
        """עצור שדור"""
        self.running = False

    def _broadcast_loop(self):
        """לולאה שנוצר בתוך thread — שודר כל 3 שניות"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            msg = json.dumps({
                "type": "controlitdiscovery",
                "role": self.role,
                "name": self.name,
                "ip": self.ip,
                "port": self.port,
                "timestamp": time.time()
            }).encode("utf-8")

            while self.running:
                try:
                    sock.sendto(msg, ("<broadcast>", BROADCAST_PORT))
                except Exception:
                    pass
                time.sleep(BROADCAST_INTERVAL)
            sock.close()
        except Exception as e:
            print(f"[!] DiscoveryBroadcaster error: {e}")


class DiscoveryListener:
    """מאזינה לשידורים וניהול רשימה של מכונות גילויות"""

    def __init__(self, callback=None):
        """
        callback: פונקציה שתיקרא כשמכונה גילויה/עודכנה
                 callback(ip, info_dict)
        """
        self.callback = callback
        self.discovered = {}  # {ip: {"name": ..., "role": ..., "port": ..., "last_seen": ...}}
        self.running = False

    def start(self):
        """התחל האזנה"""
        self.running = True
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def stop(self):
        """עצור האזנה"""
        self.running = False

    def _listen_loop(self):
        """לולאה שנוצרת בתוך thread — קבלת שידורים"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", BROADCAST_PORT))

            while self.running:
                try:
                    data, (addr, _) = sock.recvfrom(1024)
                    msg = json.loads(data.decode("utf-8"))

                    if msg.get("type") == "controlitdiscovery":
                        ip = msg.get("ip")
                        if ip:
                            self.discovered[ip] = {
                                "name": msg.get("name", "Unknown"),
                                "role": msg.get("role", "unknown"),
                                "port": msg.get("port", 5555),
                                "last_seen": time.time()
                            }
                            if self.callback:
                                self.callback(ip, self.discovered[ip])
                except json.JSONDecodeError:
                    pass
                except Exception:
                    pass
            sock.close()
        except Exception as e:
            print(f"[!] DiscoveryListener error: {e}")

    def get_users(self):
        """מחזיר רשימה של כל ה-Users שנגילו (role='user')"""
        return [
            {"ip": ip, **info}
            for ip, info in self.discovered.items()
            if info.get("role") == "user"
        ]

    def get_admins(self):
        """מחזיר רשימה של כל ה-Admins שנגילו"""
        return [
            {"ip": ip, **info}
            for ip, info in self.discovered.items()
            if info.get("role") == "admin"
        ]

    def get_relays(self):
        """מחזיר רשימה של כל שרתי ה-Relay שנגילו"""
        return [
            {"ip": ip, **info}
            for ip, info in self.discovered.items()
            if info.get("role") == "relay"
        ]

    def get_all(self):
        """מחזיר את כל המכונות שנגילו"""
        return [
            {"ip": ip, **info}
            for ip, info in self.discovered.items()
        ]
