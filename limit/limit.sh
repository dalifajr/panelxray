#!/bin/bash
REPO="https://raw.githubusercontent.com/Arya-Blitar22/st-pusat/main/"
wget -q -O /etc/systemd/system/limitvmess.service "${REPO}media/limitvmess.service" && chmod +x limitvmess.service >/dev/null 2>&1
wget -q -O /etc/systemd/system/limitvless.service "${REPO}media/limitvless.service" && chmod +x limitvless.service >/dev/null 2>&1
wget -q -O /etc/systemd/system/limittrojan.service "${REPO}media/limittrojan.service" && chmod +x limittrojan.service >/dev/null 2>&1
wget -q -O /etc/systemd/system/limitshadowsocks.service "${REPO}media/limitshadowsocks.service" && chmod +x limitshadowsocks.service >/dev/null 2>&1
wget -q -O /etc/xray/limit.vmess "${REPO}media/vmess" >/dev/null 2>&1
wget -q -O /etc/xray/limit.vless "${REPO}media/vless" >/dev/null 2>&1
wget -q -O /etc/xray/limit.trojan "${REPO}media/trojan" >/dev/null 2>&1
wget -q -O /etc/xray/limit.shadowsocks "${REPO}media/shadowsocks" >/dev/null 2>&1
chmod +x /etc/xray/limit.vmess
chmod +x /etc/xray/limit.vless
chmod +x /etc/xray/limit.trojan
chmod +x /etc/xray/limit.shadowsocks
systemctl daemon-reload
systemctl enable --now limitvmess
systemctl enable --now limitvless
systemctl enable --now limittrojan
systemctl enable --now limitshadowsocks
