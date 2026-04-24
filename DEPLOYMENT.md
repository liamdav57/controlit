# ControlIt - Deployment Guide

## ✅ Complete Implementation

### Architecture
- **LAN-Only Mode** with UDP auto-discovery on port 5556
- **No Relay Server Required** for same-network operation
- **No Invite Codes** needed
- **No Manual IP Entry** - auto-discovered

### Files Structure
```
PythonProject/
├── launcher.py              (Entry point - Admin/User mode selector)
├── main_menu.py            (Admin dashboard)
├── agent_gui.py            (User agent)
├── relay_server.py         (Optional relay for remote support)
├── script.py               (Remote command execution)
├── file_transfer.py        (File sharing)
├── login_page.py           (User authentication)
├── my_connector.py         (SQLite database)
├── net_utils.py            (Socket communication)
├── crypto.py               (Fernet encryption)
├── discovery_utils.py      (UDP broadcast/listen)
├── discovery_store.py      (Persistent machine memory)
└── discovered_machines.json (Auto-generated - machine list)
```

## How It Works

### 1. User Machine Startup
```
agent_gui.py starts
├─ Broadcasts: "I'm a User at 192.168.1.5"
├─ Listens for Relay servers
└─ Auto-fills relay IP if found
```

### 2. Admin Machine Startup
```
main_menu.py starts
├─ Listens for User machines
├─ Listens for Relay servers
└─ Shows discovered users in list
```

### 3. Relay Server (Optional)
```
relay_server.py starts
├─ Broadcasts: "I'm a Relay at 192.168.1.10"
├─ Routes commands between Admin and Users
└─ Persists for remote support later
```

## Quick Start

### For Users (Controlled Machines)
1. Run `agent_gui.py`
2. Wait for relay discovery (3-5 seconds)
3. Click "CONNECT" - relay IP auto-populated
4. Ready to receive commands

### For Admin (Control Machine)
1. Run `launcher.py`
2. Click "ADMIN"
3. Automatically sees all User machines on network
4. Select machine and send commands

## Deployment Steps

### Option A: Development Mode
```bash
python launcher.py              # Start control app
python agent_gui.py             # Start user app (on different machine)
```

### Option B: Production Mode (EXE)
```bash
pyinstaller --onefile launcher.py
# Creates: dist/launcher.exe
# Users run this on their machines
```

## Features

### Admin Dashboard Actions (6 Cards)
1. **📷 SCREENSHOT** - Capture remote screen
2. **⌨ REMOTE SHELL** - Execute commands
3. **📂 FILE TRANSFER** - Share files
4. **📊 SYSTEM INFO** - View CPU, RAM, Disk
5. **💬 MESSAGE** - Send alerts
6. **⏻ POWER** - Shutdown/Restart popup

### User Agent
- Runs in background, always listening
- Responds to admin commands
- Reports system status
- Auto-discovers relay/admin on LAN

## Database
- SQLite (created automatically in script directory)
- Tables: users, machines
- No external database needed
- Passwords hashed with bcrypt

## Security Notes
- Messages encrypted with Fernet
- Passwords never transmitted
- Works only on same local network by default
- Optional relay server for remote support (Phase 2)

## Troubleshooting

### Discovery Not Working
- Ensure both machines on same WiFi/Ethernet network
- Check Windows Firewall (allow UDP port 5556)
- Restart both applications

### Can't Connect to User
- Verify relay server IP in agent_gui.py
- Check network connectivity: ping relay IP
- Ensure relay_server.py is running

### File Transfer Issues
- Check file permissions
- Ensure source file exists
- Verify destination directory is writable

## Next Steps
1. Build EXE with PyInstaller
2. Test on 2-3 machines on same network
3. Package as installer (NSIS/MSI)
4. Deploy to client machines
