import tkinter as tk
from tkinter import messagebox, simpledialog, scrolledtext
import socket
import sys
import subprocess
import threading
import time
import base64
import io
from datetime import datetime
from PIL import Image, ImageTk
from net_utils import send_msg, recv_msg

def open_window(mode, *args):
    if getattr(sys, 'frozen', False):
        subprocess.Popen([sys.executable, mode] + list(args))
    else:
        scripts = {
            "agent": "agent_gui.py",
            "login": "login_page.py",
            "controller": "main_menu.py",
            "script": "script.py",
            "transfer": "file_transfer.py",
        }
        subprocess.Popen([sys.executable, scripts[mode]] + list(args))

class UDPListener(threading.Thread):
    def __init__(self, callback):
        super().__init__(daemon=True)
        self.callback = callback
        self.stop_flag = False

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", 5556))
        except Exception:
            print("UDP bind error")
            return

        sock.settimeout(2)
        while not self.stop_flag:
            try:
                data, addr = sock.recvfrom(1024)
                try:
                    msg = data.decode('utf-8')
                    parts = msg.split('|')
                    if len(parts) >= 3:
                        info = {
                            'role': parts[0],
                            'name': parts[1],
                            'ip': addr[0]
                        }
                        self.callback(addr[0], info)
                except Exception:
                    pass
            except socket.timeout:
                pass
            except Exception:
                pass

class CyberDashboard(tk.Tk):
    def __init__(self, username):
        super().__init__()
        self.title("ControlIt - Admin Panel")
        self.geometry("900x700")
        self.configure(bg="#1a1a1a")
        self.username = username
        self.selected_agent = None
        self.agents = {}
        self.agent_sock = None
        self.stop_listener = False

        self.discovery = UDPListener(self._on_discovery)
        self.discovery.start()

        self.setup_ui()
        self.start_refresh_loop()

    def setup_ui(self):
        header = tk.Frame(self, bg="#0a0a0a")
        header.pack(fill="x", padx=20, pady=10)

        title = tk.Label(header, text="ControlIt Admin Dashboard",
                        font=("Arial", 18, "bold"),
                        bg="#0a0a0a", fg="#e74c3c")
        title.pack(side="left")

        user_label = tk.Label(header, text=f"Logged in: {self.username}",
                             font=("Arial", 10),
                             bg="#0a0a0a", fg="#666666")
        user_label.pack(side="right")

        agent_frame = tk.Frame(self, bg="#1a1a1a")
        agent_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(agent_frame, text="Online Users:",
                font=("Arial", 11, "bold"),
                bg="#1a1a1a", fg="#ffffff").pack(anchor="w")

        btn_frame = tk.Frame(agent_frame, bg="#1a1a1a")
        btn_frame.pack(fill="x", pady=(5, 10))

        tk.Button(btn_frame, text="Refresh",
                 font=("Arial", 10),
                 bg="#e74c3c", fg="white",
                 command=self.refresh_agents).pack(side="left", padx=5)

        tk.Label(btn_frame, text="",
                bg="#1a1a1a", fg="#999999").pack(side="left", padx=5)
        self.selected_label = tk.Label(btn_frame, text="No selection",
                                       bg="#1a1a1a", fg="#999999",
                                       font=("Arial", 10))
        self.selected_label.pack(side="left")

        self.agents_listbox = tk.Listbox(agent_frame, height=4,
                                        bg="#0a0a0a", fg="#ffffff",
                                        font=("Arial", 10))
        self.agents_listbox.pack(fill="x")

        actions_frame = tk.Frame(self, bg="#1a1a1a")
        actions_frame.pack(fill="both", expand=True, padx=20, pady=10)

        tk.Label(actions_frame, text="Actions:",
                font=("Arial", 11, "bold"),
                bg="#1a1a1a", fg="#ffffff").pack(anchor="w", pady=(0, 10))

        grid = tk.Frame(actions_frame, bg="#1a1a1a")
        grid.pack(fill="both", expand=True)

        self.create_action_button(grid, 0, 0, "Screenshot", self.take_screenshot)
        self.create_action_button(grid, 0, 1, "Shell", self.open_shell)
        self.create_action_button(grid, 0, 2, "File Transfer", self.open_file_transfer)
        self.create_action_button(grid, 1, 0, "System Info", self.get_sysinfo)
        self.create_action_button(grid, 1, 1, "Send Message", self.send_message)
        self.create_action_button(grid, 1, 2, "Power", self.power_menu)

    def create_action_button(self, parent, row, col, text, cmd):
        btn = tk.Button(parent, text=text,
                       font=("Arial", 12, "bold"),
                       bg="#e74c3c", fg="white",
                       height=3, width=15,
                       command=cmd)
        btn.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        parent.grid_rowconfigure(row, weight=1)
        parent.grid_columnconfigure(col, weight=1)

    def _on_discovery(self, ip, info):
        if info.get('role') == 'user' and ip not in self.agents:
            self.agents[ip] = {
                'ip': ip,
                'name': info.get('name', 'User'),
                'role': 'user'
            }
            self.refresh_agents()

    def refresh_agents(self):
        self.agents_listbox.delete(0, "end")
        for ip, info in self.agents.items():
            self.agents_listbox.insert("end", f"{info['name']} ({ip})")
        self.agents_listbox.bind("<<ListboxSelect>>", self.on_select)

    def on_select(self, event):
        sel = self.agents_listbox.curselection()
        if sel:
            ip = list(self.agents.keys())[sel[0]]
            self.selected_agent = self.agents[ip]
            self.selected_label.config(text=f"Selected: {self.selected_agent['name']}")

    def _connect_agent(self):
        if not self.selected_agent:
            messagebox.showwarning("Error", "Select an agent first")
            return False
        try:
            self.agent_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.agent_sock.settimeout(5)
            self.agent_sock.connect((self.selected_agent['ip'], 5555))
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Cannot connect: {e}")
            self.agent_sock = None
            return False

    def send_command(self, cmd):
        if not self.selected_agent:
            messagebox.showwarning("Error", "Select an agent first")
            return None

        if not self.agent_sock:
            if not self._connect_agent():
                return None

        try:
            send_msg(self.agent_sock, cmd)
            response = recv_msg(self.agent_sock)
            return response
        except Exception as e:
            messagebox.showerror("Error", f"Command failed: {e}")
            self.agent_sock = None
            return None

    def take_screenshot(self):
        threading.Thread(target=self._screenshot_thread, daemon=True).start()

    def _screenshot_thread(self):
        resp = self.send_command("CMD|SCREENSHOT|")
        if not resp or len(resp) < 2:
            self.after(0, lambda: messagebox.showerror("Error", "No response"))
            return

        try:
            img_data = base64.b64decode(resp[1])
            img = Image.open(io.BytesIO(img_data))
            self.after(0, lambda i=img: self._show_screenshot(i))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", str(e)))

    def _show_screenshot(self, img):
        win = tk.Toplevel(self)
        win.title("Screenshot")
        img.thumbnail((1000, 600))
        tk_img = ImageTk.PhotoImage(img)
        lbl = tk.Label(win, image=tk_img, bg="black")
        lbl.image = tk_img
        lbl.pack()

    def open_shell(self):
        win = tk.Toplevel(self)
        win.title("Remote Shell")
        win.geometry("500x400")

        text = scrolledtext.ScrolledText(win, height=15, width=60,
                                        bg="#0a0a0a", fg="#00ff00",
                                        font=("Consolas", 10))
        text.pack(padx=10, pady=10, fill="both", expand=True)

        cmd_frame = tk.Frame(win, bg="#1a1a1a")
        cmd_frame.pack(fill="x", padx=10, pady=5)

        cmd_entry = tk.Entry(cmd_frame, bg="#0a0a0a", fg="#ffffff",
                            font=("Consolas", 10))
        cmd_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))

        def run_cmd():
            cmd = cmd_entry.get()
            if cmd:
                text.insert("end", f"\n$ {cmd}\n")
                text.see("end")
                resp = self.send_command(f"CMD|SHELL|{cmd}")
                if resp and len(resp) > 1:
                    text.insert("end", resp[1] + "\n")
                else:
                    text.insert("end", "No response\n")
                text.see("end")
                cmd_entry.delete(0, "end")

        tk.Button(cmd_frame, text="Run",
                 bg="#e74c3c", fg="white",
                 command=run_cmd).pack(side="right")

    def open_file_transfer(self):
        messagebox.showinfo("File Transfer", "Not implemented yet")

    def get_sysinfo(self):
        resp = self.send_command("CMD|SYSINFO|")
        if resp and len(resp) > 1:
            info_text = resp[1]
            messagebox.showinfo("System Info", info_text)
        else:
            messagebox.showerror("Error", "No response")

    def send_message(self):
        msg = simpledialog.askstring("Message", "Enter message:")
        if msg:
            resp = self.send_command(f"CMD|MSG|{msg}")
            if resp and resp[0] == "OK":
                messagebox.showinfo("Success", "Message sent")
            else:
                messagebox.showerror("Error", "Failed to send")

    def power_menu(self):
        win = tk.Toplevel(self)
        win.title("Power Options")
        win.geometry("300x150")

        tk.Label(win, text="Choose action:",
                font=("Arial", 12),
                bg="#1a1a1a", fg="#ffffff").pack(pady=20)

        tk.Button(win, text="Shutdown",
                 font=("Arial", 11),
                 bg="#cc0000", fg="white",
                 height=2, width=20,
                 command=lambda: self._power_cmd("SHUTDOWN", win)).pack(pady=5)

        tk.Button(win, text="Restart",
                 font=("Arial", 11),
                 bg="#cc8800", fg="white",
                 height=2, width=20,
                 command=lambda: self._power_cmd("RESTART", win)).pack(pady=5)

    def _power_cmd(self, action, win):
        if messagebox.askyesno("Confirm", f"Execute {action}?"):
            resp = self.send_command(f"CMD|POWER|{action}")
            win.destroy()
            if resp and resp[0] == "OK":
                messagebox.showinfo("Success", f"{action} command sent")

    def start_refresh_loop(self):
        def loop():
            while not self.stop_listener:
                time.sleep(3)
                try:
                    self.after(0, self.refresh_agents)
                except Exception:
                    pass
        threading.Thread(target=loop, daemon=True).start()

    def on_closing(self):
        self.stop_listener = True
        if self.agent_sock:
            self.agent_sock.close()
        self.destroy()

if __name__ == "__main__":
    user = sys.argv[1] if len(sys.argv) > 1 else "Admin"
    app = CyberDashboard(user)
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
