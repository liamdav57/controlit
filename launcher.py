    # ============================================================
#  launcher.py - מסך בחירת מצב (CONTROLLER / CONTROLLED)
#  המשתמש בוחר אם הוא השולט (Controller) או הנשלט (Controlled)
# ============================================================

import customtkinter as ctk
import subprocess
import sys
import os
import ctypes
import threading
from tkinter import messagebox
from PIL import Image


def open_window(mode, *args):
    """פותח חלון חדש — עובד גם כסקריפט Python וגם כ-exe מאוחד"""
    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable, mode] + list(args))
    else:
        scripts = {
            "agent":      "agent_gui.py",
            "login":      "login_page.py",
            "launcher":   "launcher.py",
            "controller": "main_menu.py",
            "script":     "script.py",
            "transfer":   "file_transfer.py",
        }
        subprocess.Popen([sys.executable, scripts[mode]] + list(args))


ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

COLORS = {
    "bg":          "#030308",
    "card":        "#0c0c1e",
    "card_border": "#1a1a3e",
    "text":        "#f1f5f9",
    "text_dim":    "#475569",
    "cyan":        "#22d3ee",
    "cyan_dark":   "#0e7490",
    "cyan_glow":   "#06161e",
    "red":         "#f43f5e",
    "red_dark":    "#9f1239",
    "red_glow":    "#1a0910",
    "purple":      "#c084fc",
}


class ControlItLauncher(ctk.CTk):
    def __init__(self, username="User"):
        super().__init__()
        self.username = username
        self.title("ControlIt - Select Mode")
        self.geometry("780x520")
        self.configure(fg_color=COLORS["bg"])
        self.resizable(False, False)
        self.setup_ui()

    def setup_ui(self):
        # ---- לוגו + כותרת ----
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(pady=(40, 30))

        ctk.CTkLabel(top, text="⚡", font=("Arial", 36)).pack()
        ctk.CTkLabel(top, text="CONTROLIT",
                     font=("Consolas", 32, "bold"),
                     text_color=COLORS["purple"]).pack(pady=(4, 0))
        ctk.CTkLabel(top,
                     text=f"Welcome, {self.username}  —  choose your mode",
                     font=("Roboto", 13),
                     text_color=COLORS["text_dim"]).pack(pady=(6, 0))

        # ---- שני כרטיסים ----
        cards_row = ctk.CTkFrame(self, fg_color="transparent")
        cards_row.pack(fill="both", expand=True, padx=60)
        cards_row.grid_columnconfigure(0, weight=1)
        cards_row.grid_columnconfigure(1, weight=1)

        self._make_card(
            parent=cards_row, col=0,
            icon="🖥",
            title="ADMIN",
            desc="Manage & command\nmachines on network",
            color=COLORS["cyan"],
            dark=COLORS["cyan_dark"],
            glow=COLORS["cyan_glow"],
            cmd=self.launch_admin
        )

        self._make_card(
            parent=cards_row, col=1,
            icon="📡",
            title="USER",
            desc="Run as a managed\nendpoint",
            color=COLORS["red"],
            dark=COLORS["red_dark"],
            glow=COLORS["red_glow"],
            cmd=self.launch_user
        )

        # ---- שורת תחתית ----
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(side="bottom", pady=22, fill="x", padx=50)

        ctk.CTkLabel(bottom, text="v1.0  ·  Cyber Control Suite",
                     font=("Consolas", 10),
                     text_color=COLORS["text_dim"]).pack(side="right")

    def _make_card(self, parent, col, icon, title, desc, color, dark, glow, cmd):
        """יוצר כרטיס בועתי מלבני"""
        # עטיפת glow
        wrap = ctk.CTkFrame(parent, fg_color=glow, corner_radius=28)
        wrap.grid(row=0, column=col, padx=12, pady=10, sticky="nsew")

        # הכרטיס עצמו
        card = ctk.CTkFrame(wrap, fg_color=color, corner_radius=24,
                            border_width=4, border_color=dark)
        card.pack(fill="both", expand=True, padx=3, pady=3)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(expand=True, pady=28, padx=24)

        ctk.CTkLabel(inner, text=icon, font=("Arial", 52)).pack()
        ctk.CTkLabel(inner, text=title,
                     font=("Consolas", 20, "bold"),
                     text_color="white").pack(pady=(12, 4))
        ctk.CTkLabel(inner, text=desc,
                     font=("Roboto", 12),
                     text_color="white",
                     justify="center").pack()

        # hover
        def on_enter(e):
            wrap.configure(fg_color=dark)
            card.configure(border_width=5)

        def on_leave(e):
            wrap.configure(fg_color=glow)
            card.configure(border_width=4)

        # כל הכרטיס לחיץ
        for w in [card, inner] + inner.winfo_children():
            w.bind("<Button-1>", lambda e: cmd())
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)

    # ---- פונקציות השקה ----

    def launch_admin(self):
        """פותח את לוח הבקרה עבור מצב ADMIN"""
        try:
            import main_menu
            self.destroy()
            app = main_menu.CyberDashboard(self.username)
            app.mainloop()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Admin panel:\n{e}")

    def launch_user(self):
        """פותח את ממשק ה-User עבור מצב USER"""
        try:
            import agent_gui
            self.destroy()
            app = agent_gui.AgentApp()
            app.mainloop()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open User panel:\n{e}")


if __name__ == "__main__":
    user = sys.argv[1] if len(sys.argv) > 1 else "Guest"
    app = ControlItLauncher(user)
    app.mainloop()
