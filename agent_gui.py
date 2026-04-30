import tkinter as tk
import socket
import threading
import subprocess
import platform
import os
import sys
import time
import base64
import io
from PIL import ImageGrab
from tkinter import messagebox
from net_utils import send_msg, recv_msg

class UDPBroadcaster(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.stop_flag = False

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while not self.stop_flag:
            try:
                msg = f"user|{socket.gethostname()}|{socket.gethostbyname(socket.gethostname())}"
                sock.sendto(msg.encode('utf-8'), ("<broadcast>", 5556))
                time.sleep(3)
            except Exception:
                pass

class CommandServer(threading.Thread):
    def __init__(self, agent_app):
        super().__init__(daemon=True)
        self.agent_app = agent_app
        self.stop_flag = False

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(("0.0.0.0", 5555))
            server.listen(5)
            print("Server listening on port 5555...")

            while not self.stop_flag:
                try:
                    server.settimeout(1)
                    client, addr = server.accept()
                    threading.Thread(target=self.handle_client, args=(client, addr), daemon=True).start()
                except socket.timeout:
                    pass
                except Exception:
                    pass
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            server.close()

    def handle_client(self, client, addr):
        try:
            print(f"Client connected: {addr}")
            while True:
                msg = recv_msg(client)
                if not msg:
                    break

                response = self.process_command(msg)
                send_msg(client, response)
        except Exception as e:
            print(f"Client error: {e}")
        finally:
            client.close()

    def process_command(self, msg):
        try:
            if isinstance(msg, list):
                cmd = msg[0] if msg else "UNKNOWN"
            else:
                cmd = msg

            print(f"Command: {cmd}")

            if cmd == "CMD" and len(msg) > 1:
                action = msg[1] if len(msg) > 1 else ""

                if action == "SCREENSHOT":
                    return self.do_screenshot()
                elif action == "SHELL" and len(msg) > 2:
                    return self.do_shell(msg[2])
                elif action == "SYSINFO":
                    return self.do_sysinfo()
                elif action == "MSG" and len(msg) > 2:
                    return self.do_message(msg[2])
                elif action == "POWER" and len(msg) > 2:
                    return self.do_power(msg[2])
                else:
                    return ["ERROR", "Unknown action"]
            else:
                return ["ERROR", "Invalid command"]
        except Exception as e:
            return ["ERROR", str(e)]

    def do_screenshot(self):
        try:
            print("Taking screenshot...")
            img = ImageGrab.grab()
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            img_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return ["OK", img_data]
        except Exception as e:
            return ["ERROR", str(e)]

    def do_shell(self, cmd):
        try:
            print(f"Executing: {cmd}")
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            output = result.stdout + result.stderr
            return ["OK", output[:2000]]
        except Exception as e:
            return ["ERROR", str(e)]

    def do_sysinfo(self):
        try:
            info = f"System: {platform.system()} {platform.release()}\n"
            info += f"Machine: {platform.machine()}\n"
            info += f"Processor: {platform.processor()}\n"
            info += f"Hostname: {socket.gethostname()}\n"

            try:
                cpu = os.popen('wmic os get TotalVisibleMemorySize').read().split('\n')[1].strip()
                ram_mb = int(cpu) // 1024
                info += f"RAM: {ram_mb} MB\n"
            except Exception:
                pass

            try:
                disk = os.popen('wmic logicaldisk get size /value').read()
                info += f"Disk: {disk[:50]}\n"
            except Exception:
                pass

            return ["OK", info]
        except Exception as e:
            return ["ERROR", str(e)]

    def do_message(self, text):
        try:
            print(f"Message: {text}")
            self.agent_app.show_notification(text)
            return ["OK"]
        except Exception as e:
            return ["ERROR", str(e)]

    def do_power(self, action):
        try:
            if action == "SHUTDOWN":
                os.system("shutdown /s /t 10")
                return ["OK"]
            elif action == "RESTART":
                os.system("shutdown /r /t 10")
                return ["OK"]
            else:
                return ["ERROR", "Unknown action"]
        except Exception as e:
            return ["ERROR", str(e)]

class AgentApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ControlIt - Managed Machine")
        self.geometry("500x300")
        self.configure(bg="#1a1a1a")

        self.broadcaster = UDPBroadcaster()
        self.broadcaster.start()

        self.server = CommandServer(self)
        self.server.start()

        self.setup_ui()

    def setup_ui(self):
        header = tk.Frame(self, bg="#0a0a0a")
        header.pack(fill="x", padx=20, pady=15)

        title = tk.Label(header, text="User Mode Active",
                        font=("Arial", 16, "bold"),
                        bg="#0a0a0a", fg="#00ff00")
        title.pack()

        info_frame = tk.Frame(self, bg="#1a1a1a")
        info_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(info_frame, text=f"Hostname: {socket.gethostname()}",
                font=("Arial", 11),
                bg="#1a1a1a", fg="#ffffff").pack(anchor="w", pady=3)

        tk.Label(info_frame, text=f"IP: {socket.gethostbyname(socket.gethostname())}",
                font=("Arial", 11),
                bg="#1a1a1a", fg="#ffffff").pack(anchor="w", pady=3)

        tk.Label(info_frame, text="Status: Broadcasting on LAN (UDP:5556)",
                font=("Arial", 10),
                bg="#1a1a1a", fg="#00ff00").pack(anchor="w", pady=3)

        tk.Label(info_frame, text="Listening on TCP:5555",
                font=("Arial", 10),
                bg="#1a1a1a", fg="#00ff00").pack(anchor="w", pady=3)

        status_frame = tk.Frame(self, bg="#1a1a1a")
        status_frame.pack(fill="both", expand=True, padx=20, pady=15)

        self.status_text = tk.Text(status_frame, height=10, width=50,
                                  bg="#0a0a0a", fg="#00ff00",
                                  font=("Consolas", 10))
        self.status_text.pack(fill="both", expand=True)

        self.log_message("Agent started successfully")
        self.log_message("Broadcasting availability to LAN...")
        self.log_message("Waiting for admin commands...")

        btn_frame = tk.Frame(self, bg="#1a1a1a")
        btn_frame.pack(fill="x", padx=20, pady=10)

        tk.Button(btn_frame, text="Exit",
                 font=("Arial", 10),
                 bg="#cc0000", fg="white",
                 command=self.on_exit).pack(side="right", padx=5)

    def log_message(self, msg):
        self.status_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        self.status_text.see("end")

    def show_notification(self, text):
        messagebox.showinfo("Message from Admin", text)
        self.log_message(f"Received message: {text}")

    def on_exit(self):
        self.broadcaster.stop_flag = True
        self.server.stop_flag = True
        self.destroy()

if __name__ == "__main__":
    app = AgentApp()
    app.mainloop()
