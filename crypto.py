# ============================================================
#  crypto.py - מודול הצפנה משותף לכל חלקי המערכת
#  משתמש בהצפנה סימטרית Fernet (AES-128-CBC + HMAC-SHA256)
#  המפתח נגזר מסיסמא קבועה — זהה בשרת ובכל הלקוחות
# ============================================================

import hashlib
import base64
from cryptography.fernet import Fernet

# ──────────────────────────────────────────
#  יצירת מפתח הצפנה מסיסמא קבועה
#  SHA-256 של הסיסמא נותן בדיוק 32 בייט —
#  גודל המפתח שFernet מצפה לו
# ──────────────────────────────────────────
_SECRET_PASSWORD = b"ControlIt-SecretKey-2024"
_raw_key         = hashlib.sha256(_SECRET_PASSWORD).digest()
SHARED_KEY       = base64.urlsafe_b64encode(_raw_key)

_fernet = Fernet(SHARED_KEY)


def encrypt(text: str) -> str:
    """מצפין טקסט רגיל ומחזיר מחרוזת base64 מוצפנת"""
    return _fernet.encrypt(text.encode("utf-8")).decode("utf-8")


def decrypt(text: str) -> str:
    """מפענח מחרוזת base64 מוצפנת ומחזיר טקסט רגיל"""
    return _fernet.decrypt(text.encode("utf-8")).decode("utf-8")
