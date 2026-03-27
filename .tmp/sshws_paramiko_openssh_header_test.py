import socket
import paramiko
import time

PAYLOAD = (
    "GET / HTTP/1.1\r\n"
    "Host: edu.ruangguru.com\r\n\r\n"
    "PATCH /ssh-ws HTTP/1.0\r\n"
    "Host: def.serverope.tech\r\n"
    "Upgrade: websocket\r\n"
    "Connection: Upgrade\r\n"
    "X-Real-Host: 127.0.0.1:22\r\n"
    "User-Agent: Mozilla/5.0 (Linux; Android 15; 23021 RAA2Y Build/ AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/ 145.0.7632.159 Mobile Safari/537.36\r\n\r\n"
)

class BufferedSocket:
    def __init__(self, sock, preload=b""):
        self.sock = sock
        self.preload = bytearray(preload)
    def recv(self, n):
        if self.preload:
            take = min(n, len(self.preload))
            out = bytes(self.preload[:take])
            del self.preload[:take]
            return out
        return self.sock.recv(n)
    def send(self, d):
        return self.sock.send(d)
    def sendall(self, d):
        return self.sock.sendall(d)
    def settimeout(self, t):
        return self.sock.settimeout(t)
    def gettimeout(self):
        return self.sock.gettimeout()
    def close(self):
        return self.sock.close()
    def fileno(self):
        return self.sock.fileno()
    def __getattr__(self, n):
        return getattr(self.sock, n)

raw = socket.create_connection(("104.17.74.206", 80), timeout=12)
raw.settimeout(2)
raw.sendall(PAYLOAD.encode())

buf = b""
idx = -1
end = -1
start = time.time()
while time.time() - start < 10:
    c = raw.recv(4096)
    if not c:
        break
    buf += c
    if idx == -1:
        idx = buf.find(b"HTTP/1.1 101")
    if idx != -1:
        end = buf.find(b"\r\n\r\n", idx)
        if end != -1:
            end += 4
            break

print("status lines:")
for line in buf.split(b"\r\n"):
    if line.startswith(b"HTTP/") or line.startswith(b"SSH-"):
        print(line.decode("latin1", errors="replace"))

pre = buf[end:] if end != -1 else b""
sock = BufferedSocket(raw, pre)
tr = paramiko.Transport(sock)
tr.banner_timeout = 15
tr.auth_timeout = 15

try:
    tr.start_client(timeout=15)
    print("hostkey:", tr.host_key_type)
    tr.auth_password("sshtest", "123")
    print("auth ok:", tr.is_authenticated())
except Exception as e:
    print("SSH failure:", type(e).__name__, str(e))
finally:
    tr.close()
    raw.close()
