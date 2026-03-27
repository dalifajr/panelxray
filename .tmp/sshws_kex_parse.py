import socket
import struct
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


def read_name_list(buf, off):
    n = struct.unpack_from(">I", buf, off)[0]
    off += 4
    val = buf[off:off+n].decode("ascii", errors="replace")
    off += n
    return val, off


s = socket.create_connection(("104.17.74.206", 80), timeout=12)
s.settimeout(1.0)
s.sendall(PAYLOAD.encode())

buf = b""
start = time.time()
seen_101 = False
while time.time() - start < 12:
    try:
        d = s.recv(4096)
        if not d:
            break
        buf += d
        if b"HTTP/1.1 101 LunaticTunneling" in buf and b"SSH-2.0-dropbear" in buf:
            seen_101 = True
            if len(buf) > 1200:
                break
    except socket.timeout:
        pass

s.close()

idx = buf.find(b"HTTP/1.1 101 LunaticTunneling")
hend = buf.find(b"\r\n\r\n", idx)
post = buf[hend+4:]

# post starts with banner line
bend = post.find(b"\r\n")
banner = post[:bend].decode("latin1", errors="replace")
rest = post[bend+2:]

print("banner:", banner)

if len(rest) < 6:
    print("not enough bytes for ssh packet")
    raise SystemExit

pkt_len = struct.unpack_from(">I", rest, 0)[0]
pad_len = rest[4]
need = 4 + pkt_len
pkt = rest[5:need-pad_len]
msg = pkt[0]
print("msg_code:", msg)
if msg != 20:
    print("not KEXINIT")
    raise SystemExit

off = 1 + 16
labels = [
    "kex_algorithms",
    "server_host_key_algorithms",
    "enc_c2s",
    "enc_s2c",
    "mac_c2s",
    "mac_s2c",
    "comp_c2s",
    "comp_s2c",
    "lang_c2s",
    "lang_s2c",
]
for lb in labels:
    val, off = read_name_list(pkt, off)
    print(lb + ":", val)
