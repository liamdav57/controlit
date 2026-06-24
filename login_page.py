import tkinter as tk
from tkinter import messagebox, font
import sys
import subprocess
from my_connector import login, register, save_user_machine, create_tables, db_available

try:
    create_tables()
except Exception as e:
    print(f"DB init error: {e}")

def open_window(mode, *args):
    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable, mode] + list(args))
    else:
        scripts = {
            "agent": "agent_gui.py",
            "login": "login_page.py",
            "launcher": "launcher.py",
            "controller": "main_menu.py",
        }
        subprocess.Popen([sys.executable, scripts[mode]] + list(args))

class LoginApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ControlIt - Access")
        self.geometry("1000x600")
        self.configure(bg="#0a0a0a")
        self.resizable(False, False)

        self.setup_ui()

    def setup_ui(self):
        # Left panel - Login
        left = tk.Frame(self, bg="#1a1a1a", width=500)
        left.pack(side="left", fill="both", expand=True)

        # Right panel - Register
        right = tk.Frame(self, bg="#0a0a0a", width=500)
        right.pack(side="right", fill="both", expand=True)

        # ===== LEFT PANEL: LOGIN =====
        login_title = tk.Label(left, text="LOGIN",
                              font=("Arial", 22, "bold"),
                              bg="#1a1a1a", fg="#e74c3c")
        login_title.pack(pady=(60, 10))

        tk.Label(left, text="Sign in to your account",
                font=("Arial", 10),
                bg="#1a1a1a", fg="#888888").pack()

        # Login username
        tk.Label(left, text="Username:",
                font=("Arial", 11, "bold"),
                bg="#1a1a1a", fg="#ffffff").pack(anchor="w", padx=40, pady=(30, 5))

        self.login_user = tk.Entry(left, font=("Arial", 11),
                                   bg="#222222", fg="#ffffff",
                                   width=35, bd=0)
        self.login_user.pack(padx=40, pady=(0, 15), ipady=8)

        # Login password
        tk.Label(left, text="Password:",
                font=("Arial", 11, "bold"),
                bg="#1a1a1a", fg="#ffffff").pack(anchor="w", padx=40, pady=(0, 5))

        self.login_pass = tk.Entry(left, show="•", font=("Arial", 11),
                                   bg="#222222", fg="#ffffff",
                                   width=35, bd=0)
        self.login_pass.pack(padx=40, pady=(0, 30), ipady=8)

        tk.Button(left, text="SIGN IN",
                 font=("Arial", 12, "bold"),
                 bg="#e74c3c", fg="white",
                 width=25, bd=0, padx=20, pady=10,
                 command=self.handle_login).pack()

        # ===== RIGHT PANEL: REGISTER =====
        reg_title = tk.Label(right, text="CREATE ACCOUNT",
                            font=("Arial", 22, "bold"),
                            bg="#0a0a0a", fg="#e74c3c")
        reg_title.pack(pady=(60, 10))

        tk.Label(right, text="Join ControlIt today",
                font=("Arial", 10),
                bg="#0a0a0a", fg="#888888").pack()

    # Register username
        tk.Label(right, text="Username:",
                font=("Arial", 11, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(anchor="w", padx=40, pady=(30, 5))

        self.reg_user = tk.Entry(right, font=("Arial", 11),
                                bg="#222222", fg="#ffffff",
                                width=35, bd=0)
        self.reg_user.pack(padx=40, pady=(0, 15), ipady=8)

        # Register password
        tk.Label(right, text="Password:",
                font=("Arial", 11, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(anchor="w", padx=40, pady=(0, 5))

        self.reg_pass = tk.Entry(right, show="•", font=("Arial", 11),
                                bg="#222222", fg="#ffffff",
                                width=35, bd=0)
        self.reg_pass.pack(padx=40, pady=(0, 15), ipady=8)

        # Confirm password
        tk.Label(right, text="Confirm Password:",
                font=("Arial", 11, "bold"),
                bg="#0a0a0a", fg="#ffffff").pack(anchor="w", padx=40, pady=(0, 5))

        self.reg_confirm = tk.Entry(right, show="•", font=("Arial", 11),
                                   bg="#222222", fg="#ffffff",
                                   width=35, bd=0)
        self.reg_confirm.pack(padx=40, pady=(0, 30), ipady=8)

        tk.Button(right, text="SIGN UP",
                 font=("Arial", 12, "bold"),
                 bg="#e74c3c", fg="white",
                 width=25, bd=0, padx=20, pady=10,
                 command=self.handle_register).pack()

        self.bind("<Return>", lambda e: self.handle_login())

    def handle_login(self):
        u = self.login_user.get().strip()
        p = self.login_pass.get()

        if not u or not p:
            messagebox.showerror("Error", "Fill all fields")
            return

        # בדיקה מהירה (עם timeout) אם יש שרת מסד נתונים.
        # בלי זה, login() היה נתקע על מחשב ללא MySQL ומקפיא את המסך.
        if not db_available():
            # מצב לא-מקוון — כל יכולות השליטה מרחוק עובדות בלי מסד;
            # רק שמירת חשבונות והיסטוריה מושבתת.
            messagebox.showinfo(
                "Offline Mode",
                "אין חיבור למסד נתונים — נכנס במצב לא-מקוון.\n"
                "כל יכולות השליטה מרחוק זמינות כרגיל.")
            self._enter(u)
            return

        res = login(u, p)
        if res.get('success'):
            try:
                save_user_machine(u)
            except Exception:
                pass
            self._enter(u)
        else:
            messagebox.showerror("Failed", res.get('message', "Invalid credentials"))

    def _enter(self, username):
        """סוגר את מסך הכניסה ופותח את מסך בחירת המצב."""
        self.destroy()
        import launcher
        launcher.ControlItLauncher(username).mainloop()

    def handle_register(self):
        u = self.reg_user.get().strip()
        p = self.reg_pass.get()
        c = self.reg_confirm.get()

        if not u or not p or not c:
            messagebox.showerror("Error", "Fill all fields")
            return

        if p != c:
            messagebox.showerror("Error", "Passwords don't match")
            return

        # אם אין שרת מסד נתונים — אין הרשמה, פשוט נכנסים עם שם כלשהו
        if not db_available():
            messagebox.showinfo(
                "Offline Mode",
                "אין מסד נתונים זמין — אין צורך בהרשמה.\n"
                "התחבר עם שם כלשהו בצד שמאל כדי להיכנס.")
            return

        res = register(u, p)
        if res.get('success'):
            messagebox.showinfo("Success", "Account created! Now login.")
            self.reg_user.delete(0, "end")
            self.reg_pass.delete(0, "end")
            self.reg_confirm.delete(0, "end")
            self.login_user.delete(0, "end")
            self.login_pass.delete(0, "end")
            self.login_user.insert(0, u)
        elif res.get('message') == 'User exists':
            messagebox.showerror("Failed", "User exists")
        else:
            # אין מסד נתונים — אין צורך בהרשמה, פשוט נכנסים עם שם כלשהו
            messagebox.showinfo(
                "Offline Mode",
                "אין מסד נתונים זמין — אין צורך בהרשמה.\n"
                "התחבר עם שם כלשהו בצד שמאל כדי להיכנס.")

if __name__ == "__main__":
    app = LoginApp()
    app.mainloop()
