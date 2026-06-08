"""
config.py — הגדרות גלובליות לפרויקט
קורא מ-.env אם קיים, אחרת משתמש בברירת מחדל.
"""
import os

# נסה לטעון .env אם python-dotenv מותקן
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv לא מותקן — משתמשים ב-environment variables רגילים

# ── MySQL ────────────────────────────────────────────────────────────────────
DB_HOST     = os.environ.get("DB_HOST",     "localhost")
DB_USER     = os.environ.get("DB_USER",     "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "Liamfort5")   # fallback לפיתוח בלבד
DB_NAME     = os.environ.get("DB_NAME",     "controlit_db")

# ── רשת ─────────────────────────────────────────────────────────────────────
CMD_PORT      = int(os.environ.get("CMD_PORT",      5555))  # TCP: פקודות
DISCOVERY_PORT = int(os.environ.get("DISCOVERY_PORT", 5556))  # UDP: גילוי agents
TRANSFER_PORT  = int(os.environ.get("TRANSFER_PORT",  5001))  # TCP: העברת קבצים

# ── אבטחה ────────────────────────────────────────────────────────────────────
AGENT_TIMEOUT_SEC = int(os.environ.get("AGENT_TIMEOUT_SEC", 10))  # שניות עד שagent נחשב offline
