# ============================================================
#  login_page.py - מסך התחברות והרשמה
#  המשתמש מזין שם משתמש וסיסמה כדי להיכנס למערכת
#  אפשר גם ליצור חשבון חדש מאותו מסך
# ============================================================

import customtkinter as ctk
from tkinter import messagebox
import sys
import os
import subprocess
from PIL import Image
from my_connector import login, register, save_user_machine, create_tables

# יצירת טבלאות SQLite אם לא קיימות
create_tables()


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

# --- הגדרות עיצוב כלליות ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

COLORS = {
    "bg":           "#030308",
    "card":         "#0c0c1e",
    "card_border":  "#1a1a3e",
    "left_panel":   "#07070e",
    "text":         "#f1f5f9",
    "text_dim":     "#475569",
    "accent":       "#3b82f6",
    "accent_hover": "#1d4ed8",
    "neon_blue":    "#22d3ee",
    "neon_purple":  "#c084fc",
    "input_bg":     "#0a0a1a",
}



class LoginApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("ControlIt - Secure Access")
        self.geometry("960x660")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg"])

        # מצב נוכחי: התחברות או הרשמה
        self.is_login_mode = True

        # טעינת הלוגו
        self.logo_image = None
        try:
            img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.jpeg")
            if os.path.exists(img_path):
                pil_image = Image.open(img_path)
                self.logo_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(240, 96))
        except Exception as e:
            print(f"Error loading logo: {e}")

        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ----------------------------------------------------------------
        # צד שמאל: לוגו ומיתוג
        # ----------------------------------------------------------------
        self.left_frame = ctk.CTkFrame(self, fg_color=COLORS["left_panel"], corner_radius=0)
        self.left_frame.grid(row=0, column=0, sticky="nsew")

        logo_content = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        logo_content.place(relx=0.5, rely=0.5, anchor="center")

        # מסגרת glow סביב הלוגו
        logo_glow = ctk.CTkFrame(logo_content,
                                 fg_color="#06161e",
                                 corner_radius=30)
        logo_glow.pack(pady=(0, 28), padx=10)

        logo_inner = ctk.CTkFrame(logo_glow, fg_color=COLORS["card"], corner_radius=28,
                                  border_width=1, border_color=COLORS["card_border"])
        logo_inner.pack(padx=3, pady=3)

        if self.logo_image:
            ctk.CTkLabel(logo_inner, text="", image=self.logo_image).pack(padx=30, pady=22)
        else:
            ctk.CTkLabel(logo_inner, text="⚡", font=("Arial", 64),
                         text_color=COLORS["neon_blue"]).pack(pady=(20, 4))
            ctk.CTkLabel(logo_inner, text="ControlIt",
                         font=("Roboto", 42, "bold"),
                         text_color=COLORS["text"]).pack(padx=30, pady=(0, 20))

        ctk.CTkLabel(
            logo_content,
            text="SECURE CYBER ACCESS",
            font=("Consolas", 13, "bold"),
            text_color=COLORS["neon_blue"]
        ).pack(pady=(6, 4))

        ctk.CTkLabel(
            logo_content,
            text="End-to-end encrypted control suite",
            font=("Roboto", 11),
            text_color=COLORS["text_dim"]
        ).pack()

        # ---- decorative dots ----
        dots_frame = ctk.CTkFrame(logo_content, fg_color="transparent")
        dots_frame.pack(pady=(24, 0))
        for color in [COLORS["neon_blue"], COLORS["neon_purple"], COLORS["accent"]]:
            ctk.CTkLabel(dots_frame, text="●", font=("Arial", 10), text_color=color).pack(side="left", padx=4)

        # ----------------------------------------------------------------
        # צד ימין: טופס התחברות
        # ----------------------------------------------------------------
        self.right_frame = ctk.CTkFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        self.right_frame.grid(row=0, column=1, sticky="nsew")

        self.form = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.form.place(relx=0.5, rely=0.5, anchor="center")

        # כותרת הטופס
        self.header = ctk.CTkLabel(self.form, text="Welcome Back",
                                   font=("Roboto", 30, "bold"), text_color=COLORS["text"])
        self.header.pack(anchor="w", pady=(0, 6))

        self.subheader = ctk.CTkLabel(self.form, text="Sign in to your account",
                                      font=("Roboto", 13), text_color=COLORS["text_dim"])
        self.subheader.pack(anchor="w", pady=(0, 28))

        # ---- שדה שם משתמש ----
        ctk.CTkLabel(self.form, text="USERNAME", font=("Roboto", 11, "bold"),
                     text_color=COLORS["text_dim"]).pack(anchor="w", pady=(0, 5))

        self.user_entry = ctk.CTkEntry(
            self.form, width=320, height=50,
            fg_color=COLORS["input_bg"],
            border_color=COLORS["card_border"],
            border_width=2,
            text_color=COLORS["text"],
            corner_radius=15,
            font=("Roboto", 14)
        )
        self.user_entry.pack(pady=(0, 16))

        # ---- שדה סיסמה ----
        ctk.CTkLabel(self.form, text="PASSWORD", font=("Roboto", 11, "bold"),
                     text_color=COLORS["text_dim"]).pack(anchor="w", pady=(0, 5))

        self.pass_entry = ctk.CTkEntry(
            self.form, width=320, height=50, show="•",
            fg_color=COLORS["input_bg"],
            border_color=COLORS["card_border"],
            border_width=2,
            text_color=COLORS["text"],
            corner_radius=15,
            font=("Roboto", 14)
        )
        self.pass_entry.pack(pady=(0, 16))

        # ---- שדה אישור סיסמה (נראה רק בהרשמה) ----
        self.confirm_lbl = ctk.CTkLabel(self.form, text="CONFIRM PASSWORD",
                                        font=("Roboto", 11, "bold"),
                                        text_color=COLORS["text_dim"])

        self.confirm_entry = ctk.CTkEntry(
            self.form, width=320, height=50, show="•",
            fg_color=COLORS["input_bg"],
            border_color=COLORS["card_border"],
            border_width=2,
            text_color=COLORS["text"],
            corner_radius=15,
            font=("Roboto", 14)
        )

        # ---- כפתור פעולה ראשי ----
        self.btn = ctk.CTkButton(
            self.form, text="LOG IN",
            command=self.handle_action,
            width=320, height=50,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            font=("Roboto", 15, "bold"),
            corner_radius=25
        )
        self.btn.pack(pady=22)

        # ---- קישור מעבר בין מצבים ----
        self.toggle_frame = ctk.CTkFrame(self.form, fg_color="transparent")
        self.toggle_frame.pack()

        self.toggle_txt = ctk.CTkLabel(self.toggle_frame, text="Don't have an account?",
                                       text_color=COLORS["text_dim"], font=("Roboto", 12))
        self.toggle_txt.pack(side="left", padx=5)

        self.toggle_btn = ctk.CTkButton(
            self.toggle_frame,
            text="Create Account",
            command=self.toggle_mode,
            fg_color="transparent",
            text_color=COLORS["accent"],
            width=0,
            hover=False,
            font=("Roboto", 12, "bold")
        )
        self.toggle_btn.pack(side="left")

        # לחיצה על Enter מפעילה את הכפתור הראשי
        self.bind("<Return>", lambda e: self.handle_action())

    def toggle_mode(self):
        """מחליף בין מצב לוגין למצב הרשמה"""
        self.is_login_mode = not self.is_login_mode

        if self.is_login_mode:
            # חזרה למצב לוגין
            self.header.configure(text="Welcome Back")
            self.subheader.configure(text="Sign in to your account")
            self.btn.configure(text="LOG IN")
            self.toggle_txt.configure(text="Don't have an account?")
            self.toggle_btn.configure(text="Create Account")
            self.confirm_lbl.pack_forget()
            self.confirm_entry.pack_forget()
        else:
            # מעבר למצב הרשמה
            self.header.configure(text="Create Account")
            self.subheader.configure(text="Register a new user")
            self.btn.configure(text="SIGN UP")
            self.toggle_txt.configure(text="Already have an account?")
            self.toggle_btn.configure(text="Log In")
            self.btn.pack_forget()
            self.toggle_frame.pack_forget()
            self.confirm_lbl.pack(anchor="w", pady=(0, 5))
            self.confirm_entry.pack(pady=(0, 16))
            self.btn.pack(pady=22)
            self.toggle_frame.pack()

    def handle_action(self):
        """מטפל בלחיצה על הכפתור - לוגין או הרשמה לפי המצב"""
        u = self.user_entry.get()
        p = self.pass_entry.get()

        if not u or not p:
            messagebox.showerror("Error", "Please fill all fields")
            return

        if self.is_login_mode:
            # ניסיון התחברות — שינוי טקסט לאינדיקציה
            self.btn.configure(text="LOGGING IN...", state="disabled")
            self.update()

            res = login(u, p)
            if res.get('success'):
                save_user_machine(u)
                self.destroy()
                open_window("launcher", u)
            else:
                self.btn.configure(text="LOG IN", state="normal")
                messagebox.showerror("Failed", res.get('message', "Error"))
        else:
            # ניסיון הרשמה
            if p != self.confirm_entry.get():
                messagebox.showerror("Error", "Passwords mismatch")
                return

            self.btn.configure(text="CREATING...", state="disabled")
            self.update()

            res = register(u, p)
            if res.get('success'):
                save_user_machine(u)
                messagebox.showinfo("Success", "Account created! Logging in...")
                self.destroy()
                open_window("launcher", u)
            else:
                self.btn.configure(text="SIGN UP", state="normal")
                messagebox.showerror("Failed", res.get('message', "Error"))


if __name__ == "__main__":
    app = LoginApp()
    app.mainloop()
