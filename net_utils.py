from crypto import encrypt, decrypt

def send_msg(conn, data):
    if isinstance(data, list):
        data = '|'.join(str(x) for x in data)
    elif isinstance(data, dict):
        parts = []
        for key, value in data.items():
            parts.append(str(value))
        data = '|'.join(parts)
    elif not isinstance(data, str):
        data = str(data)

    encrypted = encrypt(data)
    conn.sendall((encrypted + "\n").encode("utf-8"))

def recv_msg(conn):
    buf = bytearray()
    while True:
        chunk = conn.recv(4096)
        if not chunk:
            return None
        buf.extend(chunk)
        if b"\n" in buf:
            line, _ = buf.split(b"\n", 1)
            text = bytes(line).decode("utf-8").strip()
            if not text:
                return None
            try:
                decrypted = decrypt(text)
                parts = decrypted.split('|')
                return parts
            except Exception as e:
                print("Decrypt error:", e)
                return None
