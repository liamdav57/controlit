# ============================================================
#  agent_gui.py - ממשק צד ה-Agent (המחשב הנשלט)
#  מתחבר לשרת הריליי אוטומטית ברקע
#  מחכה לפקודות מה-Controller ומבצע אותן
# ============================================================

import customtkinter as ctk
import socket
import threading
import json
import subprocess
import platform
import os
import sys
import time
import base64
import io
import heapq
import psutil
from PIL import ImageGrab
from tkinter import messagebox
from datetime import datetime
from net_utils import send_msg, recv_msg
from discovery_utils import DiscoveryListener, DiscoveryBroadcaster
from discovery_store import DiscoveryStore

# ──────────────────────────────────────────
#  הגדרת שרת הריליי — שנה לכתובת שלך
# ──────────────────────────────────────────
RELAY_HOST = "127.0.0.1"   # ← שנה לכתובת ה-IP הציבורית של השרת
RELAY_PORT = 5555

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

COLORS = {
    "bg":           "#030308",
    "card":         "#0c0c1e",
    "card_border":  "#1a1a3e",
    "text":         "#f1f5f9",
    "text_dim":     "#475569",
    "online":       "#4ade80",
    "offline":      "#f43f5e",
    "warning":      "#fbbf24",
    "neon_blue":    "#22d3ee",
    "neon_purple":  "#c084fc",
    "glow_blue":    "#06161e",
    "glow_green":   "#0a1813",
    "glow_red":     "#1a0910",
}


class AgentApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ControlIt - User")
        self.geometry("600x580")
        self.configure(fg_color=COLORS["bg"])
        self.resizable(False, False)

        self.sock         = None
        self.agent_id     = None
        self.is_connected = False
        self._pulse_state = True
        self._invite_code = None
        self._relay_host  = RELAY_HOST
        self._relay_port  = RELAY_PORT

        # UDP Discovery — לזיהוי שרתי Relay ברשת המקומית
        self.discovered_relays = {}
        self.store = DiscoveryStore()
        self.discovery = DiscoveryListener(callback=self._on_relay_discovery)
        self.discovery.start()

        # UDP Broadcast — להודיע למכונות אחרות שיש User machine כאן
        my_ip = self._get_local_ip()
        self.broadcaster = DiscoveryBroadcaster(
            role="user",
            name=socket.gethostname(),
            ip=my_ip,
            port=5555  # משתמש באותו פורט כמו relay
        )
        self.broadcaster.start()

        self.setup_ui()
        self.start_pulse()

    # ──────────────────────────────────────
    #  בניית הממשק
    # ──────────────────────────────────────

    def setup_ui(self):
        # ---- כותרת ----
        header = ctk.CTkFrame(self, fg_color=COLORS["card"],
                              corner_radius=0, border_width=0)
        header.pack(fill="x")

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=24, pady=14)

        ctk.CTkLabel(header_inner, text="USER MODE",
                     font=("Consolas", 15, "bold"),
                     text_color=COLORS["neon_purple"]).pack(side="left")

        self.id_label = ctk.CTkLabel(header_inner, text="ID: —",
                                     font=("Consolas", 13),
                                     text_color=COLORS["text_dim"])
        self.id_label.pack(side="right")

        # ---- כרטיס חיבור (שרת + קוד) ----
        code_glow = ctk.CTkFrame(self, fg_color=COLORS["glow_blue"], corner_radius=22)
        code_glow.pack(fill="x", padx=24, pady=(20, 8))

        code_card = ctk.CTkFrame(code_glow, fg_color=COLORS["card"], corner_radius=20,
                                 border_width=1, border_color=COLORS["card_border"])
        code_card.pack(fill="both", expand=True, padx=2, pady=2)

        code_inner = ctk.CTkFrame(code_card, fg_color="transparent")
        code_inner.pack(fill="x", padx=20, pady=14)

        # שדה כתובת שרת
        ctk.CTkLabel(code_inner, text="SERVER ADDRESS",
                     font=("Roboto", 10, "bold"),
                     text_color=COLORS["text_dim"]).pack(anchor="w", pady=(0, 6))

        server_row = ctk.CTkFrame(code_inner, fg_color="transparent")
        server_row.pack(fill="x", pady=(0, 12))

        self.host_entry = ctk.CTkEntry(
            server_row,
            placeholder_text="e.g.  6.tcp.ngrok.io",
            height=40,
            font=("Consolas", 13),
            fg_color="#08081a",
            border_color=COLORS["card_border"],
            border_width=2,
            text_color=COLORS["text"],
            corner_radius=15,
        )
        self.host_entry.insert(0, RELAY_HOST)
        self.host_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self.port_entry = ctk.CTkEntry(
            server_row,
            placeholder_text="Port",
            height=40,
            width=90,
            font=("Consolas", 13),
            fg_color="#08081a",
            border_color=COLORS["card_border"],
            border_width=2,
            text_color=COLORS["text"],
            corner_radius=15,
            justify="center"
        )
        self.port_entry.insert(0, str(RELAY_PORT))
        self.port_entry.pack(side="right")

        # כפתור CONNECT
        self.connect_btn = ctk.CTkButton(
            code_card, text="⟳  CONNECT TO RELAY",
            command=self.start_connect,
            height=44,
            fg_color=COLORS["neon_blue"],
            hover_color="#0ea5e9",
            text_color="#030308",
            font=("Roboto", 13, "bold"),
            corner_radius=20
        )
        self.connect_btn.pack(padx=20, pady=(12, 14), fill="x")

        self.code_error = ctk.CTkLabel(code_card, text="",
                                       font=("Roboto", 11),
                                       text_color=COLORS["offline"])
        self.code_error.pack(anchor="w", padx=20, pady=(0, 10))

        # ---- כרטיס סטטוס ----
        status_glow = ctk.CTkFrame(self, fg_color=COLORS["glow_red"], corner_radius=22)
        status_glow.pack(fill="x", padx=24, pady=(8, 8))

        self.status_card = ctk.CTkFrame(status_glow, fg_color=COLORS["card"],
                                        corner_radius=20, border_width=1,
                                        border_color=COLORS["card_border"])
        self.status_card.pack(fill="both", expand=True, padx=2, pady=2)

        status_inner = ctk.CTkFrame(self.status_card, fg_color="transparent")
        status_inner.pack(pady=18, padx=24, fill="x")

        self.status_dot = ctk.CTkLabel(status_inner, text="●",
                                       font=("Arial", 22),
                                       text_color=COLORS["offline"])
        self.status_dot.pack(side="left", padx=(0, 14))

        col = ctk.CTkFrame(status_inner, fg_color="transparent")
        col.pack(side="left")

        ctk.CTkLabel(col, text="RELAY CONNECTION",
                     font=("Roboto", 10, "bold"),
                     text_color=COLORS["text_dim"]).pack(anchor="w")

        self.status_text = ctk.CTkLabel(col, text="DISCONNECTED",
                                        font=("Roboto", 15, "bold"),
                                        text_color=COLORS["offline"])
        self.status_text.pack(anchor="w")

        self.server_label = ctk.CTkLabel(col,
                                         text=f"{RELAY_HOST}:{RELAY_PORT}",
                                         font=("Consolas", 11),
                                         text_color=COLORS["text_dim"])
        self.server_label.pack(anchor="w")

        # ---- כרטיס מידע מחשב ----
        info_glow = ctk.CTkFrame(self, fg_color=COLORS["glow_blue"], corner_radius=22)
        info_glow.pack(fill="x", padx=24, pady=8)

        info_card = ctk.CTkFrame(info_glow, fg_color=COLORS["card"],
                                 corner_radius=20, border_width=1,
                                 border_color=COLORS["card_border"])
        info_card.pack(fill="both", expand=True, padx=2, pady=2)

        info_inner = ctk.CTkFrame(info_card, fg_color="transparent")
        info_inner.pack(padx=24, pady=16, fill="x")

        pc_name = socket.gethostname()
        os_name = f"{platform.system()} {platform.release()}"

        self._info_row(info_inner, "HOSTNAME", pc_name)
        self._info_row(info_inner, "OS",       os_name)

        # ---- לוג פעילות ----
        ctk.CTkLabel(self, text="ACTIVITY LOG",
                     font=("Roboto", 11, "bold"),
                     text_color=COLORS["text_dim"]).pack(anchor="w", padx=26, pady=(12, 4))

        log_glow = ctk.CTkFrame(self, fg_color="#03120a", corner_radius=18)
        log_glow.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        self.log_box = ctk.CTkTextbox(log_glow,
                                      font=("Consolas", 12),
                                      fg_color="#020202",
                                      text_color="#00ff41",
                                      border_width=0,
                                      corner_radius=16)
        self.log_box.pack(fill="both", expand=True, padx=2, pady=2)

    def _info_row(self, parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=3)
        ctk.CTkLabel(row, text=label, font=("Roboto", 10, "bold"),
                     text_color=COLORS["text_dim"], width=90,
                     anchor="w").pack(side="left")
        ctk.CTkLabel(row, text=value, font=("Consolas", 13),
                     text_color=COLORS["text"]).pack(side="left")

    # ──────────────────────────────────────
    #  אנימציית פולס
    # ──────────────────────────────────────

    def start_pulse(self):
        def pulse():
            if self.is_connected:
                c = COLORS["online"] if self._pulse_state else "#88ffbb"
                self.status_dot.configure(text_color=c)
                self._pulse_state = not self._pulse_state
            self.after(700, pulse)
        pulse()

    # ──────────────────────────────────────
    #  עדכון סטטוס (thread-safe)
    # ──────────────────────────────────────

    def set_status(self, connected, message=""):
        self.is_connected = connected
        color = COLORS["online"] if connected else COLORS["offline"]
        glow  = COLORS["glow_green"] if connected else COLORS["glow_red"]
        text  = message if message else ("CONNECTED" if connected else "DISCONNECTED")

        def _update():
            self.status_dot.configure(text_color=color)
            self.status_text.configure(text=text, text_color=color)
            self.status_card.configure(border_color=color)
            # עדכון glow wrapper (parent של status_card)
            self.status_card.master.configure(fg_color=glow)

        self.after(0, _update)

    def _show_code_error(self, message):
        """מציג שגיאה ומאפשר ניסיון מחדש"""
        self.code_error.configure(text=f"✗ {message}")
        self.host_entry.configure(state="normal")
        self.port_entry.configure(state="normal")

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        def _update():
            self.log_box.insert("end", f"[{ts}] {msg}\n")
            self.log_box.see("end")
        self.after(0, _update)

    # ──────────────────────────────────────
    #  כפתור CONNECT — מתחיל חיבור
    # ──────────────────────────────────────

    def start_connect(self):
        """נקרא כשהמשתמש לוחץ CONNECT — מתחבר לריליי"""
        host = self.host_entry.get().strip()
        port_str = self.port_entry.get().strip()

        if not host:
            self.code_error.configure(text="Please enter relay server address")
            return
        try:
            port = int(port_str)
        except ValueError:
            self.code_error.configure(text="Invalid port number")
            return

        self._relay_host  = host
        self._relay_port  = port

        # עדכון תווית הכתובת בכרטיס הסטטוס
        self.server_label.configure(text=f"{host}:{port}")

        self.host_entry.configure(state="disabled")
        self.port_entry.configure(state="disabled")
        self.code_error.configure(text="")

        threading.Thread(target=self.connect_loop, daemon=True).start()

    # ──────────────────────────────────────
    #  Helper methods
    # ──────────────────────────────────────

    def _get_local_ip(self):
        """קבל את כתובת ה-IP המקומית של המכונה"""
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"

    # ──────────────────────────────────────
    #  UDP Discovery callback
    # ──────────────────────────────────────

    def _on_relay_discovery(self, ip, info):
        """נקרא כשנמצא Relay Server ברשת"""
        if info.get("role") == "relay":
            self.discovered_relays[ip] = info
            self.store.remember_relay(ip, info.get("name", "Relay"))
            # אם השדה ריק, מלא אוטומטית עם ה-IP של ה-Relay שנמצא
            if not self._relay_host or self._relay_host == "127.0.0.1":
                self.after(0, lambda: self.host_entry.delete(0, "end"))
                self.after(0, lambda: self.host_entry.insert(0, ip))

    # ──────────────────────────────────────
    #  לולאת חיבור (reconnect אוטומטי)
    # ──────────────────────────────────────

    def connect_loop(self):
        while True:
            try:
                host = self._relay_host
                port = self._relay_port
                self.set_status(False, "CONNECTING...")
                self.log(f"Connecting to relay {host}:{port}...")

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((host, port))
                sock.settimeout(None)

                # רישום ה-User עם שם המחשב
                send_msg(sock, {
                    "role": "user",
                    "name": socket.gethostname(),
                    "os":   f"{platform.system()} {platform.release()}"
                })

                response = recv_msg(sock)
                if not response or response.get("status") != "ok":
                    err = response.get("message", "Connection failed") if response else "No response"
                    self.after(0, lambda e=err: self._show_code_error(e))
                    return

                self.sock     = sock
                self.agent_id = response.get("id")
                self.after(0, lambda: self.id_label.configure(
                    text=f"ID: {self.agent_id}"))

                # מסתיר את שדה הקוד אחרי חיבור מוצלח
                self.after(0, lambda: self.connect_btn.configure(
                    text="CONNECTED", fg_color=COLORS["online"],
                    text_color="#030308"))

                self.set_status(True)
                self.log(f"Registered as {socket.gethostname()} (ID: {self.agent_id})")

                # לולאת פקודות
                self.command_loop(sock)

            except Exception as e:
                self.log(f"Connection error: {e}")
                self.set_status(False)

            self.sock = None
            self.log("Reconnecting in 5 seconds...")
            time.sleep(5)

    # ──────────────────────────────────────
    #  לולאת ביצוע פקודות
    # ──────────────────────────────────────

    def command_loop(self, sock):
        while True:
            msg = recv_msg(sock)
            if msg is None:
                break

            cmd_type = msg.get("type")

            if cmd_type == "cmd":
                cmd_data = msg.get("data", "")
                self.log(f"CMD received: {cmd_data}")
                result = self.execute(cmd_data)
                self.log(f"Result: {str(result)[:80]}")
                send_msg(sock, {"type": "response", "data": str(result)})

            elif cmd_type == "ping":
                send_msg(sock, {"type": "pong"})

    # ──────────────────────────────────────
    #  ביצוע פקודות
    # ──────────────────────────────────────

    def execute(self, cmd):
        if not cmd.startswith("CMD:"):
            return "Unknown command format"

        cmd = cmd[4:]

        if cmd == "SHUTDOWN":
            subprocess.Popen(["shutdown", "/s", "/t", "5"])
            return "Shutdown in 5 seconds"

        elif cmd == "RESTART":
            subprocess.Popen(["shutdown", "/r", "/t", "5"])
            return "Restart in 5 seconds"

        elif cmd.startswith("MSG:"):
            msg_text = cmd[4:]
            self.after(0, lambda: messagebox.showinfo(
                "Message from Controller", msg_text))
            return "Message shown"

        elif cmd == "SCREENSHOT":
            # צילום מסך, דחיסה ל-JPEG ושליחה כ-Base64
            try:
                img = ImageGrab.grab()
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=50)
                b64 = base64.b64encode(buf.getvalue()).decode()
                return f"SCREENSHOT:{b64}"
            except Exception as e:
                return f"Screenshot error: {e}"

        elif cmd == "SYSINFO":
            # איסוף מידע על המערכת — CPU, RAM, דיסק
            try:
                cpu  = psutil.cpu_percent(interval=1)
                ram  = psutil.virtual_memory()
                disk = psutil.disk_usage('C:\\')
                info = (
                    f"CPU Usage:   {cpu}%\n"
                    f"RAM:         {ram.percent}%  "
                    f"({ram.used // 1024 // 1024} MB / {ram.total // 1024 // 1024} MB)\n"
                    f"Disk (C:):   {disk.percent}%  "
                    f"({disk.used // 1024 // 1024 // 1024} GB / {disk.total // 1024 // 1024 // 1024} GB)\n"
                    f"Platform:    {platform.system()} {platform.release()}\n"
                    f"Hostname:    {socket.gethostname()}"
                )
                return info
            except Exception as e:
                return f"Sysinfo error: {e}"

        else:
            # הרצת פקודת CMD רגילה ומחזיר פלט
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                out = subprocess.check_output(
                    cmd, shell=True,
                    stderr=subprocess.STDOUT,
                    timeout=15,
                    startupinfo=si
                )
                return out.decode("utf-8", errors="ignore")[:2000]
            except subprocess.CalledProcessError as e:
                return e.output.decode("utf-8", errors="ignore")[:2000]
            except Exception as e:
                return f"Error: {e}"


if __name__ == "__main__":
    app = AgentApp()
    try:
        app.mainloop()
    finally:
        # עצור את broadcaster וdiscovery כשהחלון נסגר
        if hasattr(app, 'broadcaster'):
            app.broadcaster.stop()
        if hasattr(app, 'discovery'):
            app.discovery.stop()
