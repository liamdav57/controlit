# ============================================================
#  script.py - מסוף פקודות מרחוק
#  מאפשר להקליד פקודות ולשלוח אותן למחשב הנשלט
#  המחשב הנשלט מריץ את הפקודה ומחזיר תוצאה
# ============================================================

import customtkinter as ctk
import socket
import sys
import threading
from net_utils import send_msg, recv_msg

# --- הגדרות עיצוב כלליות ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

COLORS = {
    "bg":           "#030308",
    "card":         "#0c0c1e",
    "card_border":  "#1a1a3e",
    "terminal_bg":  "#020202",
    "terminal_fg":  "#00ff41",    # ירוק קלאסי של טרמינל
    "terminal_dim": "#007a1e",
    "script":       "#a855f7",
    "script_hover": "#7c3aed",
    "neon_blue":    "#22d3ee",
    "neon_purple":  "#c084fc",
    "text":         "#f1f5f9",
    "text_dim":     "#475569",
}


class ScriptConsoleApp(ctk.CTk):
    def __init__(self, target_ip, relay_port=None, agent_id=None, agent_name=None):
        super().__init__()

        self.target_ip  = target_ip
        self.relay_port = relay_port
        self.agent_id   = agent_id
        self.relay_sock = None
        title_target = agent_name or target_ip
        self.title(f"REMOTE SHELL  >>  {title_target}")
        self.geometry("860x640")
        self.configure(fg_color=COLORS["bg"])

        self.setup_ui()

    def setup_ui(self):
        """בונה את הממשק: header, terminal titlebar, עורך פקודות, כפתורי פעולה"""

        # ---- Header bar ----
        header = ctk.CTkFrame(self, fg_color=COLORS["card"], corner_radius=0,
                              border_width=0)
        header.pack(fill="x")

        header_inner = ctk.CTkFrame(header, fg_color="transparent")
        header_inner.pack(fill="x", padx=20, pady=12)

        ctk.CTkLabel(
            header_inner,
            text="TERMINAL ACCESS",
            font=("Consolas", 15, "bold"),
            text_color=COLORS["script"]
        ).pack(side="left")

        ctk.CTkLabel(
            header_inner,
            text=f"TARGET  {self.target_ip}",
            font=("Consolas", 13),
            text_color=COLORS["text_dim"]
        ).pack(side="right")

        # ---- Main content area ----
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=22, pady=18)

        # ---- Terminal glow wrapper ----
        terminal_glow = ctk.CTkFrame(content, fg_color="#03120a", corner_radius=20)
        terminal_glow.pack(fill="both", expand=True)

        # ---- Fake terminal title bar ----
        title_bar = ctk.CTkFrame(terminal_glow, fg_color="#0a0a0a", corner_radius=0,
                                 height=36)
        title_bar.pack(fill="x", padx=2, pady=(2, 0))
        title_bar.pack_propagate(False)

        title_bar_inner = ctk.CTkFrame(title_bar, fg_color="transparent")
        title_bar_inner.pack(fill="x", padx=14, pady=0)
        title_bar_inner.pack_propagate(False)

        # ● ● ● dots
        dots_frame = ctk.CTkFrame(title_bar_inner, fg_color="transparent")
        dots_frame.pack(side="left", pady=8)
        for dot_color in ["#ff5f57", "#febc2e", "#28c840"]:
            ctk.CTkLabel(dots_frame, text="●", font=("Arial", 11),
                         text_color=dot_color).pack(side="left", padx=3)

        ctk.CTkLabel(
            title_bar_inner,
            text=f"bash — remote@{self.target_ip}",
            font=("Consolas", 11),
            text_color=COLORS["text_dim"]
        ).pack(side="left", padx=18, pady=8)

        # ---- Terminal text box ----
        self.console_input = ctk.CTkTextbox(
            terminal_glow,
            font=("Consolas", 13),
            fg_color=COLORS["terminal_bg"],
            text_color=COLORS["terminal_fg"],
            border_width=0,
            corner_radius=0
        )
        self.console_input.pack(fill="both", expand=True, padx=2, pady=(0, 2))
        self.console_input.insert(
            "0.0",
            "REM  Ready to execute commands...\n"
            "REM  Type your command below  (e.g., ipconfig, dir)\n\n"
        )

        # ---- Bottom panel ----
        bottom_glow = ctk.CTkFrame(self, fg_color="#0f0919", corner_radius=20)
        bottom_glow.pack(fill="x", padx=22, pady=(0, 18))

        bottom_panel = ctk.CTkFrame(bottom_glow, fg_color=COLORS["card"],
                                    corner_radius=18, border_width=1,
                                    border_color=COLORS["card_border"])
        bottom_panel.pack(fill="x", padx=2, pady=2)

        bottom_inner = ctk.CTkFrame(bottom_panel, fg_color="transparent")
        bottom_inner.pack(fill="x", padx=18, pady=14)

        self.status_lbl = ctk.CTkLabel(
            bottom_inner,
            text="● Ready",
            font=("Consolas", 12),
            text_color=COLORS["text_dim"]
        )
        self.status_lbl.pack(side="left", padx=4)

        # כפתור ניקוי
        self.clear_btn = ctk.CTkButton(
            bottom_inner,
            text="CLEAR",
            command=lambda: self.console_input.delete("0.0", "end"),
            font=("Roboto", 12, "bold"),
            fg_color="transparent",
            border_width=1,
            border_color=COLORS["card_border"],
            text_color=COLORS["text_dim"],
            hover_color=COLORS["card_border"],
            height=42,
            width=90,
            corner_radius=25
        )
        self.clear_btn.pack(side="right", padx=6)

        # כפתור הרצה
        self.run_btn = ctk.CTkButton(
            bottom_inner,
            text="▶  EXECUTE",
            command=self.run_script,
            font=("Roboto", 13, "bold"),
            fg_color=COLORS["script"],
            hover_color=COLORS["script_hover"],
            height=42,
            corner_radius=25
        )
        self.run_btn.pack(side="right", padx=6)

    def run_script(self):
        """קורא את הפקודה מהתיבה ושולח אותה למחשב הנשלט"""
        script_content = self.console_input.get("0.0", "end").strip()
        if not script_content:
            return

        # מסנן שורות ריקות והערות REM
        commands = [
            line for line in script_content.split('\n')
            if line.strip() and not line.strip().upper().startswith("REM")
        ]

        if not commands:
            self.status_lbl.configure(text="● No commands found", text_color="#fbbf24")
            return

        # שולח רק את הפקודה האחרונה
        final_command = commands[-1]

        self.status_lbl.configure(text="● Sending...", text_color="#fbbf24")
        self.run_btn.configure(state="disabled")

        threading.Thread(target=self._send_thread, args=(final_command,)).start()

    def _send_thread(self, command):
        """שולח פקודה — דרך relay אם יש agent_id, אחרת TCP ישיר"""
        try:
            if self.agent_id and self.relay_port:
                # מצב relay
                result = self._relay_cmd(f"CMD:{command}")
                if result and "error" in result:
                    raise Exception(result["error"])
                output = result.get("data", "OK") if result else "Sent"
                self.after(0, lambda: self.status_lbl.configure(
                    text=f"● Sent: {command}", text_color=COLORS["terminal_fg"]))
                self.after(0, lambda o=output: self.console_input.insert("end", f"\n>> {o}\n"))
            else:
                # מצב TCP ישיר (legacy)
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(5)
                s.connect((self.target_ip, 5001))
                s.send(f"CMD:{command}".encode())
                s.close()
                self.after(0, lambda: self.status_lbl.configure(
                    text=f"● Sent: {command}", text_color=COLORS["terminal_fg"]))
                self.after(0, lambda: self.console_input.insert("end", f"\n>> Sent successfully.\n"))

        except Exception as e:
            self.after(0, lambda: self.status_lbl.configure(
                text="● Connection Failed", text_color="#f43f5e"))
            self.after(0, lambda: self.console_input.insert("end", f"\n>> Error: {e}\n"))

        finally:
            self.after(0, lambda: self.run_btn.configure(state="normal"))
            self.after(0, lambda: self.console_input.see("end"))

    def _relay_cmd(self, cmd_data):
        """שולח פקודה דרך relay ומחזיר תשובה"""
        try:
            if not self.relay_sock:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((self.target_ip, self.relay_port))
                sock.settimeout(None)
                send_msg(sock, {"role": "controller", "username": "script"})
                recv_msg(sock)  # קבלת אישור
                self.relay_sock = sock

            send_msg(self.relay_sock, {"action": "cmd", "agent_id": self.agent_id, "data": cmd_data})
            return recv_msg(self.relay_sock)
        except Exception as e:
            self.relay_sock = None
            return {"error": str(e)}


if __name__ == "__main__":
    # מקבל: script.py RELAY_HOST RELAY_PORT AGENT_ID AGENT_NAME
    # או:    script.py IP  (מצב ישיר ישן)
    if len(sys.argv) >= 4:
        target_ip   = sys.argv[1]   # relay host
        relay_port  = int(sys.argv[2])
        agent_id    = sys.argv[3]
        agent_name  = sys.argv[4] if len(sys.argv) > 4 else agent_id
        app = ScriptConsoleApp(target_ip, relay_port=relay_port, agent_id=agent_id, agent_name=agent_name)
    else:
        target_ip = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
        app = ScriptConsoleApp(target_ip)
    app.mainloop()
