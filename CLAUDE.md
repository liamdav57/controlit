# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
py login_page.py      # Normal entry point — login/register, then opens launcher
py launcher.py        # Skip login — opens Admin/User mode selector (pass username as argv[1])
py relay_server.py    # Optional relay server (LAN routing)
py agent_gui.py       # Run directly as User (controlled machine)
py main_menu.py       # Run directly as Admin dashboard (pass username as argv[1])
```

## Building EXE

```bash
py -m pip install -r requirements.txt
py build.py           # Builds both ControlIt.exe and ControlIt-Login.exe → dist/
# Or manually:
py -m PyInstaller --onefile --windowed --name ControlIt launcher.py
```

Use `py` instead of `python` on this machine (Windows Python launcher).

## Architecture

**Full entry flow:**
```
login_page.py (LoginApp)
    → launcher.py (ControlItLauncher, receives username as argv[1])
        → ADMIN → main_menu.py (CyberDashboard)
        → USER  → agent_gui.py (AgentApp)
```

**`main.py` — frozen EXE dispatcher:**
In the built EXE, `open_window()` calls `sys.executable <mode> [args]`, which routes through `main.py`. In dev mode, it spawns individual `.py` files directly. `main.py` dispatches by `sys.argv[1]`: `agent`, `login`, `controller`, `script`, `transfer`, `launcher`.

**`open_window(mode, *args)` pattern:**
This function is duplicated in `launcher.py`, `main_menu.py`, and `login_page.py`. It handles the frozen/dev split: frozen calls `sys.executable mode args`, dev maps mode keys to script filenames. All cross-window navigation goes through this.

**Communication layer:**
- All relay TCP messages go through `net_utils.send_msg` / `recv_msg` — JSON, Fernet-encrypted, newline-delimited
- Encryption key is hardcoded in `crypto.py` (`_SECRET_PASSWORD`) — shared by all components; derived via SHA-256 → urlsafe-base64
- `relay_server.py` routes commands between Admin and User via per-agent queues (`cmd_q`, `resp_q`)

**Port map:**
| Port | Protocol | Purpose |
|------|----------|---------|
| 5555 | TCP | Relay server (commands, encrypted) |
| 5556 | UDP | LAN discovery broadcasts |
| 5001 | TCP | Direct file transfer (unencrypted) |

**File transfer (`file_transfer.py`):**
Uses plain TCP on port 5001 — NOT Fernet-encrypted. Header format: `filename<SEPARATOR>filesize` sent as raw bytes before the file data. Received files are saved to `%USERPROFILE%\Downloads\`.

**UDP Discovery (port 5556):**
- `discovery_utils.DiscoveryBroadcaster` — broadcasts role/IP every 3 seconds
- `discovery_utils.DiscoveryListener` — listens and builds discovered dict
- `relay_server.py` broadcasts as `role="relay"`, `agent_gui.py` broadcasts as `role="user"`
- Admin auto-discovers Users; User auto-populates relay IP field
- `discovery_store.py` persists discovered machines to `discovered_machines.json`

**Database:** SQLite (`users.db`) via `my_connector.py` — created automatically next to the script/exe. Tables: `users` (bcrypt-hashed passwords), `user_machines` (login history), `saved_targets` (bookmarked remote PCs).

**TCP protocol (port 5555):**
- Client sends init msg with `{"role": "user"|"admin", "name": ..., "os": ...}`
- Admin sends `{"action": "list"}` → gets agent list; `{"action": "cmd", "agent_id": X, "data": Y}` → gets response
- Commands prefixed with `CMD:` (e.g. `CMD:SCREENSHOT`, `CMD:SYSINFO`, `CMD:SHUTDOWN`)
- `script.py` remote shell also routes through relay using the same `CMD:<shell_command>` format

## Deployment Config

To deploy against a real relay server, change `RELAY_HOST` in two places:
- `main_menu.py:44` — Admin dashboard default relay IP
- `agent_gui.py:30` — User (agent) default relay IP

Both default to `"127.0.0.1"` for local development.
