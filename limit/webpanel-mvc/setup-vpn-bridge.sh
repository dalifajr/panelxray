#!/bin/bash
#
# Setup script untuk VPN Bridge Service
# Jalankan sebagai root di VPS: sudo bash setup-vpn-bridge.sh
#

set -e

echo "=== Setup VPN Bridge Service ==="

# 1. Copy bridge server script
cp vpn-bridge.py /usr/local/bin/vpn-bridge.py
chmod +x /usr/local/bin/vpn-bridge.py
echo "[OK] Bridge script installed to /usr/local/bin/vpn-bridge.py"

# 2. Create systemd service
cat > /etc/systemd/system/vpn-bridge.service <<'EOF'
[Unit]
Description=VPN Bridge Server for Web Panel
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /usr/local/bin/vpn-bridge.py
Restart=always
RestartSec=3
User=root
Group=root

# NO ProtectSystem — this service needs full write access
ProtectSystem=false
ProtectHome=false

[Install]
WantedBy=multi-user.target
EOF
echo "[OK] Systemd service created"

# 3. Enable and start the service
systemctl daemon-reload
systemctl enable vpn-bridge.service
systemctl restart vpn-bridge.service
echo "[OK] VPN Bridge service started"

# 4. Verify
sleep 1
if systemctl is-active --quiet vpn-bridge.service; then
    echo "[OK] Service is running!"
    echo ""
    echo "=== TEST: Menulis ke /etc/xray ==="
    # Quick test via the socket
    python3 -c "
import socket, json, base64

sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.connect('/tmp/vpn-bridge.sock')

req = json.dumps({
    'cmd': base64.b64encode(b'touch /etc/xray/bridge_test && echo BRIDGE_WRITE_OK && rm /etc/xray/bridge_test').decode(),
    'mode': 'bash'
})
sock.sendall(req.encode())
sock.shutdown(socket.SHUT_WR)

chunks = []
while True:
    chunk = sock.recv(65536)
    if not chunk:
        break
    chunks.append(chunk)
sock.close()

resp = json.loads(b''.join(chunks).decode())
print(f\"  Return Code: {resp['rc']}\")
print(f\"  Output: {resp['stdout']}\")
if resp['stderr']:
    print(f\"  Stderr: {resp['stderr']}\")
"
    echo ""
    echo "=== Setup selesai! ==="
else
    echo "[GAGAL] Service tidak berjalan. Cek log: journalctl -u vpn-bridge -n 20"
fi
