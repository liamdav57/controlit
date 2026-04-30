import hashlib
import base64

_SECRET_PASSWORD = b"ControlIt-SecretKey-2024"
_raw_key = hashlib.sha256(_SECRET_PASSWORD).digest()

def encrypt(text: str) -> str:
    data = text.encode('utf-8')
    key = _raw_key
    result = bytearray()

    for i, byte in enumerate(data):
        result.append(byte ^ key[i % len(key)])

    return base64.b64encode(bytes(result)).decode('utf-8')

def decrypt(text: str) -> str:
    data = base64.b64decode(text.encode('utf-8'))
    key = _raw_key
    result = bytearray()

    for i, byte in enumerate(data):
        result.append(byte ^ key[i % len(key)])

    return bytes(result).decode('utf-8')
