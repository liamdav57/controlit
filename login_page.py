import tkinter as tk
from tkinter import messagebox
import sys
import subprocess
from my_connector import login, register, save_user_machine, create_tables

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
            "script": "script.py",
            "transfer": "file_transfer.py",
        }
        subprocess.Popen([sys.executable, scripts[mode]] + list(args))

class LoginApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ControlIt - Login")
        self.geometry("500x400")
        self.configure(bg="#1a1a1a")
        self.resizable(False, False)

        self.is_login_mode = True
        self.setup_ui()

    def setup_ui(self):
        header = tk.Frame(self, bg="#0a0a0a")
        header.pack(fill="x", padx=20, pady=20)

        title = tk.Label(header, text="ControlIt",
                        font=("Arial", 24, "bold"),
                        bg="#0a0a0a", fg="#ff9900")
        title.pack()

        subtitle = tk.Label(header, text="Remote Control Suite",
                           font=("Arial", 11),
                           bg="#0a0a0a", fg="#666666")
        subtitle.pack()

        form = tk.Frame(self, bg="#1a1a1a")
        form.pack(fill="both", expand=True, padx=40, pady=20)

        self.title_label = tk.Label(form, text="Login",
                                    font=("Arial", 16, "bold"),
                                    bg="#1a1a1a", fg="#ffffff")
        self.title_label.pack(pady=(0, 20))

        tk.Label(form, text="Username:",
                font=("Arial", 11),
                bg="#1a1a1a", fg="#ffffff").pack(anchor="w", pady=(0, 5))

        self.user_entry = tk.Entry(form, font=("Arial", 12),
                                  bg="#0a0a0a", fg="#ffffff",
                                  width=30)
        self.user_entry.pack(pady=(0, 15))

        tk.Label(form, text="Password:",
                font=("Arial", 11),
                bg="#1a1a1a", fg="#ffffff").pack(anchor="w", pady=(0, 5))

        self.pass_entry = tk.Entry(form, show="*",
                                  font=("Arial", 12),
                                  bg="#0a0a0a", fg="#ffffff",
                                  width=30)
        self.pass_entry.pack(pady=(0, 5))

        self.confirm_label = tk.Label(form, text="Confirm Password:",
                                      font=("Arial", 11),
                                      bg="#1a1a1a", fg="#ffffff")

        self.confirm_entry = tk.Entry(form, show="*",
                                     font=("Arial", 12),
                                     bg="#0a0a0a", fg="#ffffff",
                                     width=30)

        self.main_btn = tk.Button(form, text="Login",
                                 font=("Arial", 12, "bold"),
                                 bg="#0066cc", fg="white",
                                 width=25,
                                 command=self.handle_action)
        self.main_btn.pack(pady=20)

        toggle_frame = tk.Frame(form, bg="#1a1a1a")
        toggle_frame.pack(pady=10)

        self.toggle_label = tk.Label(toggle_frame, text="No account?",
                                    font=("Arial", 10),
                                    bg="#1a1a1a", fg="#999999")
        self.toggle_label.pack(side="left", padx=5)

        self.toggle_btn = tk.Button(toggle_frame, text="Sign up",
                                   font=("Arial", 10),
                                   bg="#1a1a1a", fg="#0066cc",
                                   border=0,
                                   command=self.toggle_mode)
        self.toggle_btn.pack(side="left")

        self.bind("<Return>", lambda e: self.handle_action())

    def toggle_mode(self):
        self.is_login_mode = not self.is_login_mode

        if self.is_login_mode:
            self.title_label.config(text="Login")
            self.main_btn.config(text="Login")
            self.toggle_label.config(text="No account?")
            self.toggle_btn.config(text="Sign up")
            self.confirm_label.pack_forget()
            self.confirm_entry.pack_forget()
        else:
            self.title_label.config(text="Create Account")
            self.main_btn.config(text="Sign Up")
            self.toggle_label.config(text="Have account?")
            self.toggle_btn.config(text="Log in")
            self.confirm_label.pack(anchor="w", pady=(0, 5))
            self.confirm_entry.pack(pady=(0, 15))

    def handle_action(self):
        u = self.user_entry.get()
        p = self.pass_entry.get()

        if not u or not p:
            messagebox.showerror("Error", "Fill all fields")
            return

        if self.is_login_mode:
            res = login(u, p)
            if res.get('success'):
                save_user_machine(u)
                self.destroy()
                import launcher
                print(f"Launching for user: {u}")
                launcher.ControlItLauncher(u).mainloop()
            else:
                messagebox.showerror("Failed", res.get('message', "Error"))
        else:
            if p != self.confirm_entry.get():
                messagebox.showerror("Error", "Passwords don't match")
                return

            res = register(u, p)
            if res.get('success'):
                save_user_machine(u)
                messagebox.showinfo("Success", "Account created!")
                self.destroy()
                import launcher
                launcher.ControlItLauncher(u).mainloop()
            else:
                messagebox.showerror("Failed", res.get('message', "Error"))

if __name__ == "__main__":
    app = LoginApp()
    app.mainloop()
