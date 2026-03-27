import socket
import time

PAYLOAD = (
    "GET / HTTP/1.1\r\n"
    "Host: edu.ruangguru.com\r\n\r\n"
    "PATCH /ssh-ws HTTP/1.0\r\n"
    "Host: def.serverope.tech\r\n"
    "Upgrade: websocket\r\n"
    "Connection: Upgrade\r\n"
    "User-Agent: Mozilla/5.0 (Linux; Android 15; 23021 RAA2Y Build/ AP3A.240905.015.A2; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/ 145.0.7632.159 Mobile Safari/537.36\r\n\r\n"
)


def main():
    sock = socket.create_connection(("104.17.74.206", 80), timeout=10)
    sock.settimeout(0.8)
    data = PAYLOAD.encode("utf-8")
    sock.sendall(data)
    print(f"sent_bytes={len(data)}")

    buf = b""
    for _ in range(30):
        try:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
        except socket.timeout:
            pass
        time.sleep(0.1)

    print(f"recv_bytes={len(buf)}")
    print("=== STATUS LINES ===")
    for line in buf.split(b"\r\n"):
        if line.startswith(b"HTTP/") or line.startswith(b"SSH-"):
            print(line.decode("latin1", errors="replace"))

    print("=== FIRST 1200 BYTES RAW ===")
    print(buf[:1200].decode("latin1", errors="replace"))
    sock.close()


if __name__ == "__main__":
    main()
