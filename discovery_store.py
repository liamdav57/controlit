# ============================================================
#  discovery_store.py - שמירת זיכרון של מכונות גילויות
#  שמור את רשימת ה-machines בין הפעלות
# ============================================================

import json
import os
import time


class DiscoveryStore:
    """שמור ויטען רשימת User machines שנמצאו בעבר"""

    def __init__(self, filename="discovered_machines.json"):
        # שמור בצד ה-script או exe
        if getattr(__import__('sys'), 'frozen', False):
            self.filepath = os.path.join(
                os.path.dirname(sys.executable),
                filename
            )
        else:
            self.filepath = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                filename
            )
        self.data = self._load()

    def _load(self):
        """טען JSON משמור קודם"""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"users": {}, "relays": {}}

    def save(self):
        """שמור JSON לדיסק"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def remember_user(self, ip, name):
        """זכור User machine"""
        self.data["users"][ip] = {
            "name": name,
            "last_seen": time.time()
        }
        self.save()

    def remember_relay(self, ip, name):
        """זכור Relay server"""
        self.data["relays"][ip] = {
            "name": name,
            "last_seen": time.time()
        }
        self.save()

    def get_remembered_users(self):
        """חזור רשימת User machines שנשמרו"""
        return list(self.data.get("users", {}).keys())

    def get_remembered_relays(self):
        """חזור רשימת Relays שנשמרו"""
        return list(self.data.get("relays", {}).keys())

    def get_user_info(self, ip):
        """חזור info של User ספציפי"""
        return self.data.get("users", {}).get(ip)

    def get_relay_info(self, ip):
        """חזור info של Relay ספציפי"""
        return self.data.get("relays", {}).get(ip)

    def clear_users(self):
        """נקה את רשימת ה-users"""
        self.data["users"] = {}
        self.save()

    def clear_relays(self):
        """נקה את רשימת ה-relays"""
        self.data["relays"] = {}
        self.save()
