# ============================================================
#  main_menu.py - לוח הבקרה הראשי של ה-Controller
#  מתחבר לשרת הריליי ורואה את כל ה-Agents המחוברים
#  שולח פקודות דרך הריליי — עובד מכל מקום בעולם
# ============================================================

import customtkinter as ctk
import socket
import sys
import subprocess
import threading
import time
import os
import json
import traceback
import base64
import io
from datetime import datetime
from PIL import Image, ImageTk
from tkinter import messagebox, simpledialog
from net_utils import send_msg, recv_msg
from discovery_utils import DiscoveryListener
from discovery_store import DiscoveryStore
# my_connector כבר לא נדרש כאן — ניהול ה-Agents עובר דרך הריליי


def open_window(mode, *args):
    """פותח חלון חדש — עובד גם כסקריפט Python וגם כ-exe מאוחד"""
    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable, mode] + list(args))
    else:
        scripts = {
            "agent":      "agent_gui.py",
            "login":      "login_page.py",
            "controller": "main_menu.py",
            "script":     "script.py",
            "transfer":   "file_transfer.py",
        }
        subprocess.Popen([sys.executable, scripts[mode]] + list(args))

# ──────────────────────────────────────────
#  הגדרת שרת הריליי — שנה לכתובת שלך
# ──────────────────────────────────────────
RELAY_HOST = "127.0.0.1"   # ← שנה לכתובת ה-IP הציבורית של השרת
RELAY_PORT = 5555

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

COLORS = {
    "bg":           "#030308",
    "sidebar":      "#07070e",
    "card":         "#0c0c1e",
    "card_border":  "#1a1a3e",
    "text":         "#f1f5f9",
    "text_dim":     "#475569",
    "shutdown":     "#f43f5e",
    "restart":      "#fb923c",
    "message":      "#3b82f6",
    "transfer":     "#2dd4bf",
    "script":       "#a855f7",
    "wol":          "#4ade80",
    "online":       "#4ade80",
    "offline":      "#f43f5e",
    "scanning":     "#fbbf24",
    "neon_blue":    "#22d3ee",
    "neon_purple":  "#c084fc",
    "screenshot":   "#f59e0b",
    "sysinfo":      "#6366f1",
    "processes":    "#ec4899",
}

GLOW_COLORS = {
    "#f43f5e": ("#1a0910", "#310f19"),
    "#fb923c": ("#1a100c", "#321f13"),
    "#3b82f6": ("#080f1e", "#0e1c36"),
    "#2dd4bf": ("#071719", "#0b2b29"),
    "#a855f7": ("#130b1e", "#231337"),
    "#4ade80": ("#0a1813", "#112d20"),
    "#22d3ee": ("#06161e", "#092b33"),
    "#c084fc": ("#150b1e", "#271c37"),
    "#f59e0b": ("#1b1208", "#312008"),
    "#6366f1": ("#0b0b1e", "#141437"),
    "#ec4899": ("#1e0812", "#380f22"),
}

# צבעים כהים יותר לגבול התחתון — אפקט תלת-ממד בועתי
DARK_BORDER = {
    "#f43f5e": "#9f1239",
    "#fb923c": "#c2410c",
    "#3b82f6": "#1d4ed8",
    "#2dd4bf": "#0f766e",
    "#a855f7": "#7c3aed",
    "#4ade80": "#15803d",
    "#f59e0b": "#b45309",
    "#6366f1": "#4338ca",
    "#ec4899": "#9d174d",
    "#22d3ee": "#0e7490",
}


# ──────────────────────────────────────────
#  פונקציות תקשורת עם הריליי
# ──────────────────────────────────────────

# ──────────────────────────────────────────
#  הדשבורד הראשי
# ──────────────────────────────────────────

class CyberDashboard(ctk.CTk):
    def __init__(self, username):
        super().__init__()
        self.title("ControlIt - Ops Center")
        self.geometry("1200x780")
        self.configure(fg_color=COLORS["bg"])
        self.report_callback_exception = self.show_error

        self.username          = username
        self.selected_agent    = None
        self.relay_sock        = None
        self.relay_lock        = threading.Lock()
        self.stop_status_check = False
        self._server_running   = False   # האם שרת הריליי פעיל
        self._relay_host       = RELAY_HOST
        self._relay_port       = RELAY_PORT

        self.is_online             = False
        self._pulse_state          = True
        self.connection_start_time = None
        self.commands_sent         = 0

        # UDP Discovery — לזיהוי User machines ברשת המקומית
        self.discovered_users = {}
        self.store = DiscoveryStore()
        self.discovery = DiscoveryListener(callback=self._on_user_discovery)
        self.discovery.start()

        self.setup_ui_layout()

        self.start_clock()
        self.start_pulse()
        self.update_connection_timer()

        # חיבור לריליי ורענון ראשוני
        threading.Thread(target=self._init_relay, daemon=True).start()

        self.status_thread = threading.Thread(target=self.status_checker_loop, daemon=True)
        self.status_thread.start()

    def show_error(self, exc, val, tb):
        err_msg = "".join(traceback.format_exception(exc, val, tb))
        print("Error caught:", err_msg)
        messagebox.showerror("System Error", f"An unexpected error occurred:\n{val}")

    # ──────────────────────────────────────
    #  UDP Discovery callback
    # ──────────────────────────────────────

    def _on_user_discovery(self, ip, info):
        """נקרא כשנמצא User Machine ברשת"""
        if info.get("role") == "user":
            self.discovered_users[ip] = info
            self.store.remember_user(ip, info.get("name", "User"))

    # ──────────────────────────────────────
    #  שעון, פולס, טיימר
    # ──────────────────────────────────────

    def start_clock(self):
        def tick():
            now = datetime.now()
            self.clock_label.configure(text=now.strftime("%H:%M:%S"))
            self.date_label.configure(text=now.strftime("%d/%m/%Y"))
            self.after(1000, tick)
        tick()

    def start_pulse(self):
        def pulse():
            if self.is_online:
                color = COLORS["online"] if self._pulse_state else "#88ffbb"
                self.status_dot.configure(text_color=color)
                self._pulse_state = not self._pulse_state
            self.after(700, pulse)
        pulse()

    def update_connection_timer(self):
        if self.is_online and self.connection_start_time:
            elapsed = int(time.time() - self.connection_start_time)
            h = elapsed // 3600
            m = (elapsed % 3600) // 60
            s = elapsed % 60
            self.timer_label.configure(text=f"UPTIME  {h:02d}:{m:02d}:{s:02d}")
        elif not self.is_online:
            self.timer_label.configure(text="")
        self.after(1000, self.update_connection_timer)

    # ──────────────────────────────────────
    #  בניית ממשק
    # ──────────────────────────────────────

    def setup_ui_layout(self):
        self.sidebar = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color=COLORS["sidebar"])
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.create_sidebar_content()

        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_area.pack(side="right", fill="both", expand=True, padx=40, pady=30)
        self.create_header()
        self.create_agent_browser()
        self.create_actions_grid()

    def create_sidebar_content(self):
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(pady=(30, 10), padx=20, fill="x")

        try:
            img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.jpeg")
            if os.path.exists(img_path):
                pil_image = Image.open(img_path)
                self.sidebar_logo = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(180, 70))
                ctk.CTkLabel(logo_frame, text="", image=self.sidebar_logo).pack(pady=5)
            else:
                ctk.CTkLabel(logo_frame, text="⚡", font=("Arial", 32)).pack(side="left")
                ctk.CTkLabel(logo_frame, text="ControlIt", font=("Roboto", 20, "bold"),
                             text_color=COLORS["text"]).pack()
        except Exception:
            ctk.CTkLabel(logo_frame, text="ControlIt", font=("Roboto", 20, "bold")).pack()

        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLORS["card_border"]).pack(fill="x", padx=20, pady=15)

        # שעון
        clock_card = ctk.CTkFrame(self.sidebar, fg_color=COLORS["card"], corner_radius=20,
                                  border_width=1, border_color=COLORS["card_border"])
        clock_card.pack(fill="x", padx=18, pady=8)
        self.clock_label = ctk.CTkLabel(clock_card, text="00:00:00",
                                        font=("Consolas", 28, "bold"), text_color=COLORS["neon_blue"])
        self.clock_label.pack(pady=(14, 2))
        self.date_label = ctk.CTkLabel(clock_card, text="",
                                       font=("Consolas", 12), text_color=COLORS["text_dim"])
        self.date_label.pack(pady=(0, 14))

        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLORS["card_border"]).pack(fill="x", padx=20, pady=10)

        # סטטוס
        self.status_card = ctk.CTkFrame(self.sidebar, fg_color=COLORS["card"], corner_radius=20,
                                        border_width=1, border_color=COLORS["card_border"])
        self.status_card.pack(fill="x", padx=18, pady=8)
        status_inner = ctk.CTkFrame(self.status_card, fg_color="transparent")
        status_inner.pack(padx=15, pady=14, fill="x")
        self.status_dot = ctk.CTkLabel(status_inner, text="●", font=("Arial", 20),
                                       text_color=COLORS["offline"])
        self.status_dot.pack(side="left", padx=(0, 10))
        col = ctk.CTkFrame(status_inner, fg_color="transparent")
        col.pack(side="left")
        ctk.CTkLabel(col, text="USER STATUS", font=("Roboto", 9, "bold"),
                     text_color=COLORS["text_dim"]).pack(anchor="w")
        self.status_text = ctk.CTkLabel(col, text="NO USER SELECTED",
                                        font=("Roboto", 13, "bold"), text_color=COLORS["text_dim"])
        self.status_text.pack(anchor="w")

        self.timer_label = ctk.CTkLabel(self.sidebar, text="",
                                        font=("Consolas", 11), text_color=COLORS["neon_blue"])
        self.timer_label.pack(pady=(2, 4))

        # מונה פקודות
        cmd_card = ctk.CTkFrame(self.sidebar, fg_color=COLORS["card"], corner_radius=20,
                                border_width=1, border_color=COLORS["card_border"])
        cmd_card.pack(fill="x", padx=18, pady=8)
        cmd_inner = ctk.CTkFrame(cmd_card, fg_color="transparent")
        cmd_inner.pack(padx=15, pady=12, fill="x")
        ctk.CTkLabel(cmd_inner, text="⌨", font=("Arial", 18),
                     text_color=COLORS["neon_purple"]).pack(side="left", padx=(0, 10))
        cmd_col = ctk.CTkFrame(cmd_inner, fg_color="transparent")
        cmd_col.pack(side="left")
        ctk.CTkLabel(cmd_col, text="SESSION", font=("Roboto", 9, "bold"),
                     text_color=COLORS["text_dim"]).pack(anchor="w")
        self.cmd_count_label = ctk.CTkLabel(cmd_col, text="COMMANDS  0",
                                            font=("Consolas", 12, "bold"),
                                            text_color=COLORS["neon_purple"])
        self.cmd_count_label.pack(anchor="w")

        # ---- כרטיס שרת ריליי ----
        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLORS["card_border"]).pack(fill="x", padx=20, pady=10)

        srv_card = ctk.CTkFrame(self.sidebar, fg_color=COLORS["card"], corner_radius=20,
                                border_width=1, border_color=COLORS["card_border"])
        srv_card.pack(fill="x", padx=18, pady=8)

        srv_inner = ctk.CTkFrame(srv_card, fg_color="transparent")
        srv_inner.pack(padx=15, pady=10, fill="x")

        ctk.CTkLabel(srv_inner, text="RELAY SERVER", font=("Roboto", 9, "bold"),
                     text_color=COLORS["text_dim"]).pack(anchor="w", pady=(0, 6))

        # ---- שדות IP ו-Port ----
        ip_row = ctk.CTkFrame(srv_inner, fg_color="transparent")
        ip_row.pack(fill="x", pady=(0, 4))

        self.relay_host_entry = ctk.CTkEntry(
            ip_row, placeholder_text="Server IP",
            height=30, font=("Consolas", 11),
            fg_color="#08081a", border_color=COLORS["card_border"],
            border_width=1, text_color=COLORS["text"], corner_radius=10
        )
        self.relay_host_entry.insert(0, self._relay_host)
        self.relay_host_entry.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.relay_port_entry = ctk.CTkEntry(
            ip_row, placeholder_text="Port",
            height=30, width=54, font=("Consolas", 11),
            fg_color="#08081a", border_color=COLORS["card_border"],
            border_width=1, text_color=COLORS["text"], corner_radius=10,
            justify="center"
        )
        self.relay_port_entry.insert(0, str(self._relay_port))
        self.relay_port_entry.pack(side="right")

        ctk.CTkButton(
            srv_card, text="⟳  CONNECT",
            command=self.connect_to_relay,
            height=30, corner_radius=14,
            fg_color=COLORS["message"], hover_color="#1d4ed8",
            font=("Roboto", 10, "bold")
        ).pack(padx=12, pady=(0, 6), fill="x")

        ctk.CTkFrame(srv_card, height=1, fg_color=COLORS["card_border"]).pack(fill="x", padx=12, pady=2)

        # ---- סטטוס + START SERVER ----
        self.server_status_label = ctk.CTkLabel(srv_inner, text="● STOPPED",
                                                font=("Consolas", 11, "bold"),
                                                text_color=COLORS["offline"])
        self.server_status_label.pack(anchor="w", pady=(6, 2))

        self.server_ip_label = ctk.CTkLabel(srv_inner, text="",
                                            font=("Consolas", 10),
                                            text_color=COLORS["text_dim"])
        self.server_ip_label.pack(anchor="w")

        self.server_btn = ctk.CTkButton(
            srv_card, text="▶  START SERVER",
            command=self.toggle_relay_server,
            height=34, corner_radius=16,
            fg_color=COLORS["wol"], hover_color="#15803d",
            text_color="#030308", font=("Roboto", 11, "bold")
        )
        self.server_btn.pack(padx=12, pady=(4, 12), fill="x")

        # כפתור יציאה
        self.logout_btn = ctk.CTkButton(
            self.sidebar, text="LOG OUT", command=self.logout,
            fg_color="transparent", border_width=1, border_color=COLORS["card_border"],
            text_color=COLORS["offline"], hover_color="#2a0a10",
            corner_radius=25, font=("Roboto", 12, "bold"), height=42
        )
        self.logout_btn.pack(side="bottom", padx=20, pady=35, fill="x")

    def create_header(self):
        ctk.CTkLabel(self.main_area, text=f"Welcome back, {self.username}",
                     font=("Roboto", 34, "bold"), text_color=COLORS["text"], anchor="w").pack(fill="x")
        ctk.CTkLabel(self.main_area, text="Command & Control Center — Global Relay",
                     font=("Roboto", 13), text_color=COLORS["text_dim"], anchor="w").pack(fill="x", pady=(4, 20))

    def create_agent_browser(self):
        """פאנל בחירת Agent מהריליי — במקום הקלדת IP"""
        glow_wrap = ctk.CTkFrame(self.main_area, fg_color=GLOW_COLORS["#22d3ee"][0], corner_radius=26)
        glow_wrap.pack(fill="x", pady=(0, 20))

        panel = ctk.CTkFrame(glow_wrap, fg_color=COLORS["card"], corner_radius=22,
                             border_width=1, border_color=COLORS["card_border"])
        panel.pack(fill="both", expand=True, padx=2, pady=2)

        # כותרת + כפתורים
        top_row = ctk.CTkFrame(panel, fg_color="transparent")
        top_row.pack(fill="x", padx=20, pady=(16, 8))

        ctk.CTkLabel(top_row, text="🌐  ONLINE USERS",
                     font=("Roboto", 13, "bold"),
                     text_color=COLORS["neon_blue"]).pack(side="left")

        ctk.CTkButton(
            top_row, text="⟳  REFRESH", command=self.refresh_agents,
            width=110, height=34, fg_color=COLORS["message"],
            hover_color="#1d4ed8", corner_radius=20,
            font=("Roboto", 11, "bold")
        ).pack(side="right", padx=5)

        # תווית agent נבחר
        self.selected_label = ctk.CTkLabel(
            panel,
            text="No user selected — click REFRESH and choose one",
            font=("Consolas", 11),
            text_color=COLORS["text_dim"]
        )
        self.selected_label.pack(anchor="w", padx=22, pady=(0, 6))

        # רשימת agents
        self.agents_scroll = ctk.CTkScrollableFrame(
            panel, fg_color="transparent", height=90, corner_radius=0
        )
        self.agents_scroll.pack(fill="x", padx=12, pady=(0, 14))

    def create_actions_grid(self):
        self.grid_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.grid_frame.pack(fill="both", expand=True)
        self.grid_frame.grid_columnconfigure((0, 1), weight=1)  # 2 columns
        self.grid_frame.grid_rowconfigure((0, 1, 2), weight=1)  # 3 rows

        self.create_card(0, 0, "SCREENSHOT",  "Capture remote screen", "📷", COLORS["screenshot"], self.take_screenshot)
        self.create_card(0, 1, "REMOTE SHELL", "Run Command",           "⌨",  COLORS["script"],     self.open_script_console)
        self.create_card(1, 0, "FILE TRANSFER","Share files",           "📂", COLORS["transfer"],   self.open_file_transfer)
        self.create_card(1, 1, "SYSTEM INFO", "CPU, RAM & Disk",       "📊", COLORS["sysinfo"],    self.get_sysinfo)
        self.create_card(2, 0, "MESSAGE",     "Send alert popup",      "💬", COLORS["message"],    self.ask_message)
        self.create_card(2, 1, "POWER",       "Shutdown/Restart",      "⏻",  COLORS["shutdown"],   self.open_power_menu)

    def _bind_recursive(self, widget, enter_fn, leave_fn):
        widget.bind("<Enter>", enter_fn)
        widget.bind("<Leave>", leave_fn)
        for child in widget.winfo_children():
            self._bind_recursive(child, enter_fn, leave_fn)

    def create_card(self, row, col, title, desc, icon, color, cmd):
        """כרטיס בסגנון בועתי — רקע צבעוני, גבול כהה, אייקון + טקסט"""
        border_color  = DARK_BORDER.get(color, "#000000")
        glow_normal   = GLOW_COLORS.get(color, (COLORS["card_border"], "#2a2a5e"))[0]
        glow_hover    = GLOW_COLORS.get(color, (COLORS["card_border"], "#2a2a5e"))[1]

        # עטיפת glow חיצונית
        glow = ctk.CTkFrame(self.grid_frame, fg_color=glow_normal, corner_radius=28)
        glow.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

        # הכרטיס עצמו — רקע בצבע הניאון, גבול כהה לאפקט תלת-ממד
        card = ctk.CTkFrame(glow, fg_color=color, corner_radius=24,
                            border_width=4, border_color=border_color)
        card.pack(fill="both", expand=True, padx=3, pady=3)

        # תוכן — אייקון משמאל, טקסט מימין
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=18, pady=18)

        ctk.CTkLabel(content, text=icon, font=("Arial", 38),
                     text_color="white").pack(side="left", padx=(0, 16))

        text_col = ctk.CTkFrame(content, fg_color="transparent")
        text_col.pack(side="left", fill="both", expand=True)

        ctk.CTkLabel(text_col, text=title, font=("Roboto", 15, "bold"),
                     text_color="white", anchor="w").pack(anchor="w")
        ctk.CTkLabel(text_col, text=desc, font=("Roboto", 11),
                     text_color="white", anchor="w").pack(anchor="w", pady=(2, 0))

        # כל הכרטיס לחיץ
        def on_click(e):
            cmd()

        def on_enter(e):
            glow.configure(fg_color=glow_hover)
            card.configure(border_width=5)

        def on_leave(e):
            glow.configure(fg_color=glow_normal)
            card.configure(border_width=4)

        self._bind_recursive(card, on_enter, on_leave)
        card.bind("<Button-1>", on_click)
        for child in card.winfo_children():
            child.bind("<Button-1>", on_click)
            for sub in child.winfo_children():
                sub.bind("<Button-1>", on_click)

    # ──────────────────────────────────────
    #  חיבור לריליי
    # ──────────────────────────────────────

    def _connect_relay(self):
        """מחבר ל-Relay Server ומחזיר True אם הצליח"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((self._relay_host, self._relay_port))
            sock.settimeout(None)
            send_msg(sock, {"role": "controller", "username": self.username})
            resp = recv_msg(sock)
            if resp and resp.get("status") == "ok":
                self.relay_sock = sock
                return True
        except Exception:
            pass
        return False

    def relay_request(self, msg, timeout=10):
        """שולח בקשה לריליי ומחזיר תשובה (thread-safe)"""
        with self.relay_lock:
            try:
                if not self.relay_sock:
                    if not self._connect_relay():
                        return {"error": "Cannot reach relay server"}
                self.relay_sock.settimeout(timeout)
                send_msg(self.relay_sock, msg)
                return recv_msg(self.relay_sock)
            except Exception as e:
                self.relay_sock = None
                return {"error": str(e)}

    def _init_relay(self):
        """חיבור ראשוני + רענון רשימת agents"""
        if self._connect_relay():
            self.after(0, self.refresh_agents)

    def connect_to_relay(self):
        """מתחבר לריליי לפי ה-IP והפורט שהוזנו בשדות"""
        host = self.relay_host_entry.get().strip()
        port_str = self.relay_port_entry.get().strip()

        if not host:
            messagebox.showerror("Error", "Enter relay server IP address")
            return
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Error", "Invalid port number")
            return

        self._relay_host = host
        self._relay_port = port

        # סגור חיבור קיים
        with self.relay_lock:
            if self.relay_sock:
                try:
                    self.relay_sock.close()
                except Exception:
                    pass
                self.relay_sock = None

        threading.Thread(target=self._init_relay, daemon=True).start()

    # ──────────────────────────────────────
    #  ניהול Agents
    # ──────────────────────────────────────

    def refresh_agents(self):
        """מרענן את רשימת ה-Agents המחוברים"""
        threading.Thread(target=self._refresh_thread, daemon=True).start()

    def _refresh_thread(self):
        result = self.relay_request({"action": "list"})
        if result and "agents" in result:
            self.after(0, lambda: self._update_agent_list(result["agents"]))
        else:
            err = result.get("error", "Unknown error") if result else "No response"
            self.after(0, lambda: messagebox.showerror(
                "Relay Error", f"Cannot reach relay server:\n{err}"))

    def _update_agent_list(self, agents):
        """מרענן את הכרטיסים בפאנל ה-agents"""
        for widget in self.agents_scroll.winfo_children():
            widget.destroy()

        if not agents:
            ctk.CTkLabel(self.agents_scroll,
                         text="No agents online — make sure agent_gui.py is running on the target machine",
                         font=("Roboto", 11), text_color=COLORS["text_dim"]).pack(pady=8)
            return

        for agent in agents:
            self._add_agent_row(agent)

    def _add_agent_row(self, agent):
        """יוצר שורת agent בפאנל"""
        is_selected = (self.selected_agent and self.selected_agent["id"] == agent["id"])
        border_color = COLORS["neon_blue"] if is_selected else COLORS["card_border"]

        row_glow = ctk.CTkFrame(self.agents_scroll,
                                fg_color=GLOW_COLORS["#22d3ee"][1 if is_selected else 0],
                                corner_radius=16)
        row_glow.pack(fill="x", pady=4, padx=4)

        row = ctk.CTkFrame(row_glow, fg_color="#0a0f1e", corner_radius=14,
                           border_width=1, border_color=border_color)
        row.pack(fill="both", expand=True, padx=2, pady=2)

        # מידע על ה-agent
        info_col = ctk.CTkFrame(row, fg_color="transparent")
        info_col.pack(side="left", padx=14, pady=10)

        uptime = agent.get("uptime", 0)
        h, m = uptime // 3600, (uptime % 3600) // 60
        uptime_str = f"{h:02d}:{m:02d} uptime"

        ctk.CTkLabel(info_col, text=f"🖥  {agent['name']}",
                     font=("Consolas", 13, "bold"),
                     text_color=COLORS["neon_blue"] if is_selected else COLORS["text"]).pack(anchor="w")
        ctk.CTkLabel(info_col,
                     text=f"{agent['os']}  ·  {agent.get('addr', '?')}  ·  {uptime_str}",
                     font=("Roboto", 10), text_color=COLORS["text_dim"]).pack(anchor="w")

        # כפתור בחירה
        btn_text  = "✓ SELECTED" if is_selected else "SELECT"
        btn_color = COLORS["neon_blue"] if is_selected else COLORS["card_border"]
        ctk.CTkButton(
            row, text=btn_text, width=95, height=32,
            fg_color=btn_color, hover_color="#0ea5e9",
            corner_radius=15, font=("Roboto", 11, "bold"),
            command=lambda a=agent: self.select_agent(a)
        ).pack(side="right", padx=12, pady=10)

    def select_agent(self, agent):
        """בוחר agent — כל הפקודות ישלחו אליו"""
        self.selected_agent = agent
        self.selected_label.configure(
            text=f"Selected: {agent['name']}  ({agent['os']})",
            text_color=COLORS["neon_blue"]
        )
        self.refresh_agents()

    # ──────────────────────────────────────
    #  בדיקת סטטוס
    # ──────────────────────────────────────

    def status_checker_loop(self):
        """בודק כל 5 שניות אם ה-agent הנבחר עדיין מחובר לריליי"""
        while not self.stop_status_check:
            time.sleep(5)
            if not self.selected_agent:
                continue
            result = self.relay_request({"action": "list"})
            if result and "agents" in result:
                ids = [a["id"] for a in result["agents"]]
                is_online = self.selected_agent["id"] in ids
                color = COLORS["online"] if is_online else COLORS["offline"]
                text  = "CONNECTED" if is_online else "DISCONNECTED"
                try:
                    self.after(0, lambda c=color, t=text: self.update_status_ui(c, t))
                except Exception:
                    break

    def update_status_ui(self, color, text):
        self.is_online = (text == "CONNECTED")
        if self.is_online and self.connection_start_time is None:
            self.connection_start_time = time.time()
        elif not self.is_online:
            self.connection_start_time = None
        self.status_dot.configure(text_color=color)
        self.status_text.configure(
            text=text,
            text_color=color if self.is_online else COLORS["text_dim"]
        )
        self.status_card.configure(border_color=color if self.is_online else COLORS["card_border"])

    # ──────────────────────────────────────
    #  שליחת פקודות דרך הריליי
    # ──────────────────────────────────────

    def send_cmd(self, command):
        """שולח פקודה ל-agent הנבחר דרך שרת הריליי"""
        if not self.selected_agent:
            messagebox.showwarning("No Agent", "Select an agent first (click REFRESH)")
            return

        if command in ["SHUTDOWN", "RESTART"]:
            if not messagebox.askyesno("Confirm", f"{command} {self.selected_agent['name']}?"):
                return

        threading.Thread(
            target=self._send_cmd_thread,
            args=(f"CMD:{command}",),
            daemon=True
        ).start()

    def _send_cmd_thread(self, cmd_data):
        result = self.relay_request({
            "action":   "cmd",
            "agent_id": self.selected_agent["id"],
            "data":     cmd_data
        })
        if not result:
            self.after(0, lambda: messagebox.showerror("Error", "No response from relay"))
            return

        if "error" in result:
            self.after(0, lambda: messagebox.showerror("Error", result["error"]))
        else:
            self.commands_sent += 1
            n = self.commands_sent
            self.after(0, lambda: self.cmd_count_label.configure(text=f"COMMANDS  {n}"))
            response_text = result.get("data", "Command sent")
            # הצג תשובה קצרה ב-messagebox
            short = str(response_text)[:300]
            self.after(0, lambda: messagebox.showinfo("Response", short))

    def ask_message(self):
        msg = simpledialog.askstring("Message", "Enter text to send:")
        if msg:
            self.send_cmd(f"MSG:{msg}")

    def open_power_menu(self):
        """פותח popup עם אפשרויות Power — Shutdown ו-Restart"""
        if not self.selected_agent:
            messagebox.showwarning("No User", "Select a user first")
            return

        win = ctk.CTkToplevel(self)
        win.title("Power Options")
        win.geometry("300x150")
        win.configure(fg_color=COLORS["bg"])
        win.grab_set()
        win.resizable(False, False)

        ctk.CTkLabel(win, text="Choose action:", font=("Roboto", 14),
                     text_color=COLORS["text"]).pack(pady=20)

        ctk.CTkButton(
            win, text="⏻  SHUTDOWN",
            command=lambda: (self.send_cmd("SHUTDOWN"), win.destroy()),
            fg_color=COLORS["shutdown"], hover_color="#be123c",
            height=40, corner_radius=20, font=("Roboto", 12, "bold")
        ).pack(padx=20, pady=5, fill="x")

        ctk.CTkButton(
            win, text="↻  RESTART",
            command=lambda: (self.send_cmd("RESTART"), win.destroy()),
            fg_color=COLORS["restart"], hover_color="#d97706",
            height=40, corner_radius=20, font=("Roboto", 12, "bold")
        ).pack(padx=20, pady=5, fill="x")

    def perform_wol(self):
        """Wake on LAN — שולח Magic Packet לכתובת MAC"""
        mac = simpledialog.askstring("Wake on LAN", "Enter MAC address (e.g. AA:BB:CC:DD:EE:FF):")
        if not mac:
            return
        try:
            clean = mac.replace(":", "").replace("-", "")
            data  = bytes.fromhex("FF" * 6 + clean * 16)
            sock  = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(data, ("255.255.255.255", 9))
            messagebox.showinfo("WoL", f"Magic Packet sent to {mac}!")
        except Exception as e:
            messagebox.showerror("Error", f"WoL Error: {e}")

    def take_screenshot(self):
        """מצלם מסך של ה-Agent ומציג בחלון נפרד"""
        if not self.selected_agent:
            messagebox.showwarning("No Agent", "Select an agent first")
            return
        threading.Thread(target=self._screenshot_thread, daemon=True).start()

    def _screenshot_thread(self):
        result = self.relay_request(
            {"action": "cmd", "agent_id": self.selected_agent["id"], "data": "CMD:SCREENSHOT"},
            timeout=30
        )
        if not result or "error" in result:
            err = result.get("error", "No response") if result else "No response"
            self.after(0, lambda: messagebox.showerror("Error", err))
            return

        data = result.get("data", "")
        if not data.startswith("SCREENSHOT:"):
            self.after(0, lambda: messagebox.showerror("Error", data))
            return

        b64 = data[len("SCREENSHOT:"):]
        img_bytes = base64.b64decode(b64)
        img = Image.open(io.BytesIO(img_bytes))
        self.after(0, lambda: self._show_screenshot(img))

    def _show_screenshot(self, img):
        """מציג את צילום המסך בחלון"""
        win = ctk.CTkToplevel(self)
        win.title(f"Screenshot — {self.selected_agent['name']}")
        win.configure(fg_color=COLORS["bg"])

        # כיווץ לגודל מקסימלי של 1000x600
        img.thumbnail((1000, 600))
        tk_img = ImageTk.PhotoImage(img)

        lbl = ctk.CTkLabel(win, text="", image=tk_img)
        lbl.image = tk_img   # מניעת garbage collection
        lbl.pack(padx=10, pady=10)

        ctk.CTkButton(win, text="CLOSE", command=win.destroy,
                      fg_color=COLORS["card_border"], corner_radius=20,
                      width=120, height=36).pack(pady=(0, 10))

    def get_sysinfo(self):
        """מבקש נתוני CPU, RAM ודיסק מה-Agent"""
        if not self.selected_agent:
            messagebox.showwarning("No Agent", "Select an agent first")
            return
        threading.Thread(target=self._sysinfo_thread, daemon=True).start()

    def _sysinfo_thread(self):
        result = self.relay_request(
            {"action": "cmd", "agent_id": self.selected_agent["id"], "data": "CMD:SYSINFO"}
        )
        if not result or "error" in result:
            err = result.get("error", "No response") if result else "No response"
            self.after(0, lambda: messagebox.showerror("Error", err))
            return
        info = result.get("data", "No data")
        self.after(0, lambda: self._show_sysinfo(info))

    def _show_sysinfo(self, info):
        """מציג את מידע המערכת בחלון מעוצב"""
        win = ctk.CTkToplevel(self)
        win.title(f"System Info — {self.selected_agent['name']}")
        win.geometry("420x320")
        win.configure(fg_color=COLORS["bg"])
        win.resizable(False, False)

        ctk.CTkLabel(win, text="SYSTEM INFORMATION",
                     font=("Roboto", 15, "bold"),
                     text_color=COLORS["sysinfo"]).pack(pady=(24, 16))

        glow = ctk.CTkFrame(win, fg_color=GLOW_COLORS["#6366f1"][0], corner_radius=20)
        glow.pack(fill="x", padx=24)

        card = ctk.CTkFrame(glow, fg_color=COLORS["card"], corner_radius=18,
                            border_width=1, border_color=COLORS["card_border"])
        card.pack(fill="both", expand=True, padx=2, pady=2)

        ctk.CTkLabel(card, text=info,
                     font=("Consolas", 13),
                     text_color=COLORS["text"],
                     justify="left").pack(padx=24, pady=20, anchor="w")

        ctk.CTkButton(win, text="CLOSE", command=win.destroy,
                      fg_color=COLORS["sysinfo"], hover_color="#4338ca",
                      corner_radius=20, width=120, height=36,
                      font=("Roboto", 12, "bold")).pack(pady=20)

    def open_script_console(self):
        """פותח את מסוף הפקודות — מעביר relay info ו-agent_id"""
        if not self.selected_agent:
            messagebox.showwarning("No Agent", "Select an agent first")
            return
        try:
            open_window("script",
                        self._relay_host, str(self._relay_port),
                        self.selected_agent["id"],
                        self.selected_agent["name"])
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def open_file_transfer(self):
        """פותח העברת קבצים — מעביר IP ישיר של ה-agent"""
        if not self.selected_agent:
            messagebox.showwarning("No Agent", "Select an agent first")
            return
        try:
            open_window("transfer", self.selected_agent.get("addr", ""))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ──────────────────────────────────────
    #  הפעלה/עצירה של שרת הריליי
    # ──────────────────────────────────────

    def toggle_relay_server(self):
        """מפעיל או עוצר את שרת הריליי"""
        if self._server_running:
            self._stop_relay_server()
        else:
            self._start_relay_server()

    def _start_relay_server(self):
        """מפעיל את שרת הריליי ב-Thread ברקע"""
        import relay_server   # import מאוחר — מונע circular import בעת טעינת המודול

        def _run():
            try:
                relay_server.main()
            except Exception as e:
                self.after(0, lambda: self.server_status_label.configure(
                    text=f"ERROR: {e}", text_color=COLORS["offline"]))
                self._server_running = False

        self._server_running = True
        threading.Thread(target=_run, daemon=True).start()

        # מציג את ה-IP המקומי
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            local_ip = "127.0.0.1"

        self.server_status_label.configure(text="● RUNNING", text_color=COLORS["online"])
        self.server_ip_label.configure(text=f"{local_ip}:{RELAY_PORT}")
        self.server_btn.configure(text="■  STOP SERVER",
                                  fg_color=COLORS["offline"],
                                  hover_color="#be123c",
                                  text_color="white")

    def _stop_relay_server(self):
        """עוצר את שרת הריליי — Thread daemon ייסגר עם הסגירה"""
        self._server_running = False
        self.server_status_label.configure(text="● STOPPED", text_color=COLORS["offline"])
        self.server_ip_label.configure(text="")
        self.server_btn.configure(text="▶  START SERVER",
                                  fg_color=COLORS["wol"],
                                  hover_color="#15803d",
                                  text_color="#030308")
        messagebox.showinfo("Server", "Relay server stopped.\nActive agents will disconnect.")

    def logout(self):
        self.stop_status_check = True
        if self.discovery:
            self.discovery.stop()
        if self.relay_sock:
            try:
                self.relay_sock.close()
            except Exception:
                pass
        self.destroy()
        import login_page
        login_page.LoginApp().mainloop()


if __name__ == "__main__":
    if len(sys.argv) <= 1:
        try:
            subprocess.Popen([sys.executable, "login_page.py"])
        except Exception:
            pass
    else:
        app = CyberDashboard(sys.argv[1])
        try:
            app.mainloop()
        finally:
            # עצור את discovery כשהחלון נסגר
            if hasattr(app, 'discovery'):
                app.discovery.stop()
