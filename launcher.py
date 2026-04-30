import tkinter as tk
from tkinter import messagebox
import subprocess
import sys

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

class ControlItLauncher(tk.Tk):
    def __init__(self, username="User"):
        super().__init__()
        self.username = username
        self.title("ControlIt - Select Mode")
        self.geometry("600x400")
        self.configure(bg="#1a1a1a")
        self.resizable(False, False)
        self.setup_ui()

    def setup_ui(self):
        top_frame = tk.Frame(self, bg="#1a1a1a")
        top_frame.pack(pady=30)

        title_label = tk.Label(top_frame, text="CONTROLIT",
                              font=("Arial", 28, "bold"),
                              bg="#1a1a1a", fg="#ff9900")
        title_label.pack()

        subtitle = tk.Label(top_frame, text=f"Welcome {self.username} - choose mode",
                          font=("Arial", 11),
                          bg="#1a1a1a", fg="#999999")
        subtitle.pack()

        buttons_frame = tk.Frame(self, bg="#1a1a1a")
        buttons_frame.pack(fill="both", expand=True, padx=40, pady=20)

        admin_btn = tk.Button(buttons_frame, text="ADMIN\nControl Mode",
                             font=("Arial", 14, "bold"),
                             bg="#0066cc", fg="white",
                             width=20, height=5,
                             command=self.launch_admin)
        admin_btn.pack(side="left", padx=10)

        user_btn = tk.Button(buttons_frame, text="USER\nManaged Mode",
                            font=("Arial", 14, "bold"),
                            bg="#cc0000", fg="white",
                            width=20, height=5,
                            command=self.launch_user)
        user_btn.pack(side="right", padx=10)

    def launch_admin(self):
        try:
            print("Launching ADMIN mode...")
            import main_menu
            self.destroy()
            app = main_menu.CyberDashboard(self.username)
            app.mainloop()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open Admin:\n{e}")

    def launch_user(self):
        try:
            print("Launching USER mode...")
            import agent_gui
            self.destroy()
            app = agent_gui.AgentApp()
            app.mainloop()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open User:\n{e}")

if __name__ == "__main__":
    user = sys.argv[1] if len(sys.argv) > 1 else "Guest"
    app = ControlItLauncher(user)
    app.mainloop()
