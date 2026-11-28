#!/bin/bash
# Local IP-limiter service activation (replaces legacy third-party /etc/xray/limit.* scripts)
set -e

for legacy in limitvmess limitvless limittrojan limitshadowsocks; do
  if systemctl list-unit-files 2>/dev/null | grep -q "^${legacy}\.service"; then
    systemctl disable --now "$legacy" >/dev/null 2>&1 || true
  fi
done

if [[ ! -x /usr/bin/limit-ip ]]; then
  echo "ERROR: /usr/bin/limit-ip tidak ditemukan atau tidak executable." >&2
  exit 1
fi

for pair in "vmip:VMESS" "vlip:VLESS" "trip:TROJAN" "ssip:SHADOWSOCKS" "sship:SSH"; do
  svc="${pair%%:*}"
  desc="${pair#*:}"
  cat > "/etc/systemd/system/${svc}.service" <<EOF
[Unit]
Description=VPN IP Limit Monitor (${desc})
After=network-online.target xray.service

[Service]
Type=simple
User=root
Nice=15
IOSchedulingClass=idle
ExecStart=/usr/bin/limit-ip ${svc}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
done

systemctl daemon-reload
for svc in vmip vlip trip ssip sship; do
  systemctl enable --now "$svc" >/dev/null 2>&1 || systemctl restart "$svc" >/dev/null 2>&1 || true
done
