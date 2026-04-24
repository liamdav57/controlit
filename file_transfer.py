# ============================================================
#  file_transfer.py - העברת קבצים בין מחשבים
#  מאפשר לשלוח קבצים למחשב הנשלט, או לקבל קבצים ממנו
#  משתמש בחיבור TCP ישיר על פורט 5001
# ============================================================

import customtkinter as ctk
import socket
import threading
import os
import sys
from tkinter import filedialog, messagebox
from PIL import Image

# --- הגדרות עיצוב כלליות ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

COLORS = {
    "bg":           "#030308",
    "card":         "#0c0c1e",
    "card_border":  "#1a1a3e",
    "glass":        "#ffffff08",
    "text":         "#f1f5f9",
    "text_dim":     "#475569",
    "transfer":     "#2dd4bf",      # טורקיז
    "transfer_hov": "#0f766e",
    "success":      "#4ade80",
    "error":        "#f43f5e",
    "neon_blue":    "#22d3ee",
    "neon_purple":  "#c084fc",
    "log_bg":       "#000000",
}


class FileTransferApp(ctk.CTk):
    def __init__(self, target_ip=""):
        super().__init__()
        self.title("ControlIt - Secure File Transfer")
        self.geometry("880x680")
        self.configure(fg_color=COLORS["bg"])
        self.resizable(False, False)

        self.initial_target_ip = target_ip
        self.server_running = False
        self.server_socket = None

        # טעינת הלוגו
        self.logo_image = None
        try:
            img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.jpeg")
            if os.path.exists(img_path):
                pil_image = Image.open(img_path)
                self.logo_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(50, 50))
        except Exception as e:
            print(f"Error loading logo: {e}")

        self.setup_ui()

    def setup_ui(self):
        """בונה את הממשק הראשי עם header ושתי לשוניות"""
        # ---- Header ----
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=32, pady=(28, 20))

        if self.logo_image:
            ctk.CTkLabel(header, text="", image=self.logo_image).pack(side="left", padx=(0, 16))
        else:
            ctk.CTkLabel(header, text="📂", font=("Arial", 36),
                         text_color=COLORS["transfer"]).pack(side="left", padx=(0, 16))

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left")

        ctk.CTkLabel(title_frame, text="FILE TRANSFER", font=("Roboto", 22, "bold"),
                     text_color=COLORS["transfer"]).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="SECURE P2P PROTOCOL", font=("Consolas", 11),
                     text_color=COLORS["text_dim"]).pack(anchor="w")

        # ---- Glow wrapper for tab view ----
        glow_wrap = ctk.CTkFrame(self, fg_color="#071719", corner_radius=26)
        glow_wrap.pack(fill="both", expand=True, padx=24, pady=(0, 24))

        # ---- Tab view ----
        self.tab_view = ctk.CTkTabview(
            glow_wrap,
            fg_color=COLORS["card"],
            segmented_button_fg_color="#050510",
            segmented_button_selected_color=COLORS["transfer"],
            segmented_button_selected_hover_color=COLORS["transfer_hov"],
            segmented_button_unselected_color="#050510",
            segmented_button_unselected_hover_color=COLORS["card"],
            corner_radius=22,
            border_width=1,
            border_color=COLORS["card_border"]
        )
        self.tab_view.pack(fill="both", expand=True, padx=3, pady=3)
        self.tab_view.add("  SEND FILES  ")
        self.tab_view.add("  RECEIVE FILES  ")

        self.setup_send_tab()
        self.setup_receive_tab()

    def setup_send_tab(self):
        """בונה את לשונית שליחת הקבצים"""
        tab = self.tab_view.tab("  SEND FILES  ")

        # ---- שדה כתובת IP יעד ----
        ctk.CTkLabel(tab, text="TARGET IP ADDRESS", font=("Roboto", 11, "bold"),
                     text_color=COLORS["text_dim"]).pack(anchor="w", padx=32, pady=(28, 6))

        self.target_ip_entry = ctk.CTkEntry(
            tab,
            placeholder_text="e.g. 192.168.1.10",
            width=420,
            height=48,
            font=("Consolas", 14),
            fg_color="#08081a",
            border_color=COLORS["card_border"],
            border_width=2,
            text_color=COLORS["text"],
            corner_radius=15
        )
        self.target_ip_entry.pack(anchor="w", padx=32)

        if self.initial_target_ip:
            self.target_ip_entry.insert(0, self.initial_target_ip)

        # ---- בחירת קובץ לשליחה ----
        ctk.CTkLabel(tab, text="SELECTED FILE", font=("Roboto", 11, "bold"),
                     text_color=COLORS["text_dim"]).pack(anchor="w", padx=32, pady=(24, 6))

        file_frame = ctk.CTkFrame(tab, fg_color="transparent")
        file_frame.pack(fill="x", padx=32)

        self.file_path_lbl = ctk.CTkLabel(
            file_frame,
            text="No file selected...",
            font=("Consolas", 12),
            text_color=COLORS["text_dim"],
            fg_color="#08081a",
            corner_radius=15,
            height=48,
            width=520,
            anchor="w"
        )
        self.file_path_lbl.pack(side="left", fill="x", expand=True, padx=(0, 14))

        ctk.CTkButton(
            file_frame, text="BROWSE",
            command=self.browse_file,
            width=110, height=48,
            fg_color=COLORS["card_border"],
            hover_color="#2a2a5e",
            font=("Roboto", 12, "bold"),
            corner_radius=25
        ).pack(side="right")

        # ---- סרגל התקדמות ----
        ctk.CTkFrame(tab, height=1, fg_color=COLORS["card_border"]).pack(fill="x", padx=32, pady=(28, 0))

        self.progress_bar = ctk.CTkProgressBar(
            tab, height=15,
            progress_color=COLORS["transfer"],
            fg_color="#08081a",
            corner_radius=8
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=32, pady=(16, 8))

        self.status_lbl = ctk.CTkLabel(tab, text="Ready to initiate transfer",
                                       font=("Roboto", 12), text_color=COLORS["text_dim"])
        self.status_lbl.pack(pady=(4, 0))

        # ---- כפתור שליחה ----
        ctk.CTkButton(
            tab,
            text="⬆  INITIATE TRANSFER",
            command=self.start_transfer,
            width=280,
            height=52,
            font=("Roboto", 15, "bold"),
            fg_color=COLORS["transfer"],
            hover_color=COLORS["transfer_hov"],
            corner_radius=30
        ).pack(pady=30)

    def setup_receive_tab(self):
        """בונה את לשונית קבלת הקבצים"""
        tab = self.tab_view.tab("  RECEIVE FILES  ")

        # ---- כרטיס סטטוס שרת ----
        srv_glow = ctk.CTkFrame(tab, fg_color="#06161e", corner_radius=22)
        srv_glow.pack(fill="x", padx=32, pady=(28, 0))

        status_frame = ctk.CTkFrame(srv_glow, fg_color="#08081a", corner_radius=20,
                                    border_width=1, border_color=COLORS["card_border"])
        status_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.server_status_lbl = ctk.CTkLabel(
            status_frame,
            text="SERVER OFFLINE",
            font=("Roboto", 17, "bold"),
            text_color=COLORS["error"]
        )
        self.server_status_lbl.pack(pady=(22, 6))

        try:
            my_ip = socket.gethostbyname(socket.gethostname())
        except Exception:
            my_ip = "Unknown"

        ctk.CTkLabel(status_frame,
                     text=f"Listening on  {my_ip}  |  Port 5001",
                     font=("Consolas", 12),
                     text_color=COLORS["text_dim"]).pack(pady=(0, 22))

        # ---- לוג פעילות ----
        ctk.CTkLabel(tab, text="ACTIVITY LOG", font=("Roboto", 11, "bold"),
                     text_color=COLORS["text_dim"]).pack(anchor="w", padx=32, pady=(22, 6))

        log_glow = ctk.CTkFrame(tab, fg_color="#081310", corner_radius=18)
        log_glow.pack(fill="x", padx=32)

        self.log_box = ctk.CTkTextbox(
            log_glow,
            height=190,
            font=("Consolas", 12),
            fg_color=COLORS["log_bg"],
            text_color=COLORS["success"],
            border_color=COLORS["card_border"],
            border_width=1,
            corner_radius=16
        )
        self.log_box.pack(fill="x", padx=2, pady=2)

        # ---- כפתור הפעלת שרת ----
        self.toggle_server_btn = ctk.CTkButton(
            tab,
            text="▶  START LISTENING",
            command=self.toggle_server,
            width=280,
            height=52,
            font=("Roboto", 15, "bold"),
            fg_color=COLORS["success"],
            hover_color="#15803d",
            corner_radius=30
        )
        self.toggle_server_btn.pack(pady=28)

    def browse_file(self):
        """פותח חלון בחירת קובץ"""
        filename = filedialog.askopenfilename()
        if filename:
            self.selected_file = filename
            self.file_path_lbl.configure(text=os.path.basename(filename), text_color=COLORS["text"])

    def start_transfer(self):
        """מתחיל שליחת קובץ בThread נפרד"""
        if not hasattr(self, 'selected_file'):
            messagebox.showerror("Error", "Please select a file first!")
            return

        ip = self.target_ip_entry.get()
        if not ip:
            messagebox.showwarning("Error", "Enter target IP!")
            return

        threading.Thread(target=self.send_file_thread, args=(ip, self.selected_file)).start()

    def send_file_thread(self, ip, filename):
        """שולח את הקובץ דרך TCP עם עדכון סרגל התקדמות"""
        try:
            self.status_lbl.configure(text="Establishing connection...", text_color="#fbbf24")
            self.progress_bar.set(0)

            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((ip, 5001))

            file_size = os.path.getsize(filename)
            name = os.path.basename(filename)

            # שליחת header עם שם הקובץ וגודלו
            s.send(f"{name}<SEPARATOR>{file_size}".encode())

            self.status_lbl.configure(text="Sending data...", text_color=COLORS["neon_blue"])
            with open(filename, "rb") as f:
                sent = 0
                while True:
                    bytes_read = f.read(4096)
                    if not bytes_read:
                        break
                    s.sendall(bytes_read)
                    sent += len(bytes_read)
                    self.progress_bar.set(sent / file_size)

            s.close()
            self.status_lbl.configure(text="Transfer Complete!", text_color=COLORS["success"])
            messagebox.showinfo("Success", "File Sent Successfully!")

        except Exception as e:
            self.status_lbl.configure(text=f"Error: {e}", text_color=COLORS["error"])
            self.progress_bar.set(0)

    def toggle_server(self):
        """מפעיל או מכבה את שרת הקבלה"""
        if not self.server_running:
            self.server_running = True
            self.toggle_server_btn.configure(text="■  STOP SERVER",
                                             fg_color=COLORS["error"], hover_color="#991b1b")
            self.server_status_lbl.configure(text="SERVER LISTENING", text_color=COLORS["success"])
            self.log("Server started on port 5001...")
            threading.Thread(target=self.start_server_thread, daemon=True).start()
        else:
            self.server_running = False
            self.toggle_server_btn.configure(text="▶  START LISTENING",
                                             fg_color=COLORS["success"], hover_color="#15803d")
            self.server_status_lbl.configure(text="SERVER OFFLINE", text_color=COLORS["error"])
            self.log("Server stopped.")

    def start_server_thread(self):
        """מאזין לחיבורים נכנסים ומטפל בכל קובץ שמגיע"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            server.bind(("0.0.0.0", 5001))
            server.listen(5)
            server.settimeout(1)

            while self.server_running:
                try:
                    client, addr = server.accept()
                    self.log(f"Connection from {addr[0]}")
                    threading.Thread(target=self.handle_receive, args=(client,)).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    self.log(f"Server Error: {e}")
                    break

        except Exception as e:
            self.log(f"Bind Error: {e}")

        finally:
            server.close()

    def handle_receive(self, client):
        """מקבל ושומר קובץ שנשלח מהצד השני"""
        try:
            received = client.recv(4096).decode()

            if "<SEPARATOR>" in received:
                filename, filesize = received.split("<SEPARATOR>")
                filesize = int(filesize)
                filename = os.path.basename(filename)
                save_path = os.path.join(os.environ['USERPROFILE'], 'Downloads', filename)
                self.log(f"Receiving: {filename} ({filesize} bytes)")

                with open(save_path, "wb") as f:
                    total = 0
                    while total < filesize:
                        bytes_read = client.recv(4096)
                        if not bytes_read:
                            break
                        f.write(bytes_read)
                        total += len(bytes_read)

                self.log(f"Saved to: Downloads/{filename}")
            else:
                self.log(f"Unknown data received: {received}")

            client.close()

        except Exception as e:
            self.log(f"Receive Error: {e}")

    def log(self, msg):
        """מוסיף שורה ללוג הפעילות"""
        self.log_box.insert("end", f"> {msg}\n")
        self.log_box.see("end")


if __name__ == "__main__":
    target_ip = sys.argv[1] if len(sys.argv) > 1 else ""
    app = FileTransferApp(target_ip)
    app.mainloop()
