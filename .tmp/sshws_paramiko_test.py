import socket
import time
import paramiko

PAYLOAD = (
    "GET / HTTP/1.1\r\n"
    "Host: edu.ruangguru.com\r\n\r\n"
    "PATCH /ssh-ws HTTP/1.0\r\n"
    "Host: def.serverope.tech\r\n"
    "Upgrade: websocket\r\n"
    "Connection: Upgrade\r\n"
    "User-Agent: Mozilla/5.0 (Linux; Android 15; 23021 RAA2Y Build/ AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/ 145.0.7632.159 Mobile Safari/537.36\r\n\r\n"
)


class BufferedSocket:
    def __init__(self, sock, preload=b""):
        self.sock = sock
        self.preload = bytearray(preload)

    def recv(self, n):
        if self.preload:
            take = min(n, len(self.preload))
            data = bytes(self.preload[:take])
            del self.preload[:take]
            return data
        return self.sock.recv(n)

    def send(self, data):
        return self.sock.send(data)

    def sendall(self, data):
        return self.sock.sendall(data)

    def settimeout(self, v):
        return self.sock.settimeout(v)

    def gettimeout(self):
        return self.sock.gettimeout()

    def close(self):
        return self.sock.close()

    def fileno(self):
        return self.sock.fileno()

    def __getattr__(self, name):
        return getattr(self.sock, name)


def main():
    raw = socket.create_connection(("104.17.74.206", 80), timeout=12)
    raw.settimeout(2.0)
    raw.sendall(PAYLOAD.encode("utf-8"))

    buf = b""
    header_start = -1
    header_end = -1

    deadline = time.time() + 10
    while time.time() < deadline:
        chunk = raw.recv(4096)
        if not chunk:
            break
        buf += chunk
        if header_start == -1:
            header_start = buf.find(b"HTTP/1.1 101 LunaticTunneling")
        if header_start != -1:
            header_end = buf.find(b"\r\n\r\n", header_start)
            if header_end != -1:
                header_end += 4
                break

    if header_start == -1 or header_end == -1:
        print("FAILED: no 101 header found")
        print(buf.decode("latin1", errors="replace"))
        return

    print("101 header located")
    print(buf[:header_end].decode("latin1", errors="replace"))

    preload = buf[header_end:]
    print("preload bytes after 101:", len(preload))
    if preload:
        print("preload first line:", preload.split(b"\r\n")[0].decode("latin1", errors="replace"))

    b_sock = BufferedSocket(raw, preload)

    transport = paramiko.Transport(b_sock)
    transport.banner_timeout = 15
    transport.auth_timeout = 15

    try:
        transport.start_client(timeout=15)
        sec = transport.get_security_options()
        print("kex in use:", transport.kex_engine.__class__.__name__ if transport.kex_engine else "unknown")
        print("server key type:", transport.host_key_type)
        transport.auth_password("sshtest", "123")
        print("auth ok:", transport.is_authenticated())

        chan = transport.open_session(timeout=10)
        chan.exec_command("whoami")
        out = chan.recv(1024)
        err = chan.recv_stderr(1024)
        print("cmd out:", out.decode("latin1", errors="replace"))
        print("cmd err:", err.decode("latin1", errors="replace"))
        chan.close()

    except Exception as exc:
        print("SSH FAILURE:", type(exc).__name__, str(exc))
    finally:
        try:
            transport.close()
        except Exception:
            pass
        try:
            raw.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
