# ============================================================
#  main.py - נקודת הכניסה המאוחדת לכל האפליקציה
# ============================================================

import sys
import traceback


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""

    if mode == "agent":
        from agent_gui import AgentApp
        AgentApp().mainloop()

    elif mode == "login":
        from login_page import LoginApp
        LoginApp().mainloop()

    elif mode == "controller":
        username = sys.argv[2] if len(sys.argv) > 2 else "User"
        from main_menu import CyberDashboard
        CyberDashboard(username).mainloop()

    elif mode == "script":
        from script import ScriptConsoleApp
        if len(sys.argv) >= 5:
            target_ip  = sys.argv[2]
            relay_port = int(sys.argv[3])
            agent_id   = sys.argv[4]
            agent_name = sys.argv[5] if len(sys.argv) > 5 else agent_id
            ScriptConsoleApp(target_ip, relay_port=relay_port,
                             agent_id=agent_id, agent_name=agent_name).mainloop()
        else:
            ScriptConsoleApp("127.0.0.1").mainloop()

    elif mode == "transfer":
        from file_transfer import FileTransferApp
        target_ip = sys.argv[2] if len(sys.argv) > 2 else ""
        FileTransferApp(target_ip).mainloop()

    elif mode == "launcher":
        username = sys.argv[2] if len(sys.argv) > 2 else "User"
        from launcher import ControlItLauncher
        ControlItLauncher(username).mainloop()

    else:
        from login_page import LoginApp
        LoginApp().mainloop()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        err = traceback.format_exc()
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("ControlIt - Startup Error", err)
            root.destroy()
        except Exception:
            pass
