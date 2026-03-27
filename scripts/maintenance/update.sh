#!/bin/bash
set -euo pipefail

REPO_URL="https://github.com/dalifajr/panelxray.git"
REPO_API="https://api.github.com/repos/dalifajr/panelxray"
TARGET_SBIN="/usr/local/sbin"
STATE_FILE="/etc/kyt/panelxray-revision"
TMP_DIR="/tmp/panelxray-update.$$"
BRANCH="${PANELXRAY_BRANCH:-}"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

if [[ -z "$BRANCH" ]]; then
    BRANCH="$(curl -fsSL "$REPO_API" 2>/dev/null | awk -F '"' '/"default_branch"/ {print $4; exit}')"
    [[ -n "$BRANCH" ]] || BRANCH="main"
fi

clear
echo -e "\033[1;36m==========================================================\033[0m"
echo -e "\033[1;33m                 UPDATE PROGRAM (GITHUB)                  \033[0m"
echo -e "\033[1;36m==========================================================\033[0m"
echo -e "Branch target : $BRANCH"

if ! command -v git >/dev/null 2>&1; then
    echo -e "\033[1;31mGit tidak ditemukan. Install git terlebih dahulu.\033[0m"
    exit 1
fi

mkdir -p "$TMP_DIR"
if ! git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP_DIR" >/dev/null 2>&1; then
    echo -e "\033[1;31mGagal clone branch $BRANCH dari repository.\033[0m"
    exit 1
fi

if [[ ! -d "$TMP_DIR/limit/menu" ]]; then
    echo -e "\033[1;31mStruktur repository tidak valid: limit/menu tidak ditemukan.\033[0m"
    exit 1
fi

sync_runtime_configs() {
    local domain
    domain="$(cat /etc/xray/domain 2>/dev/null || hostname -f 2>/dev/null || hostname 2>/dev/null || echo localhost)"

    mkdir -p /etc/nginx/conf.d /etc/haproxy /etc/systemd/system /usr/bin

    if [[ -f "$TMP_DIR/limit/xray.conf" ]]; then
        cp -f "$TMP_DIR/limit/xray.conf" /etc/nginx/conf.d/xray.conf
        sed -i "s/xxx/${domain}/g" /etc/nginx/conf.d/xray.conf 2>/dev/null || true
    fi

    if [[ -f "$TMP_DIR/limit/haproxy.cfg" ]]; then
        cp -f "$TMP_DIR/limit/haproxy.cfg" /etc/haproxy/haproxy.cfg
        sed -i "s/xxx/${domain}/g" /etc/haproxy/haproxy.cfg 2>/dev/null || true
        sed -i -E '/^[[:space:]]*bind-process[[:space:]]+/d' /etc/haproxy/haproxy.cfg 2>/dev/null || true
        sed -i -E 's/[[:space:]]+tfo([[:space:]]|$)/ /g' /etc/haproxy/haproxy.cfg 2>/dev/null || true
        sed -i -E '/^[[:space:]]*bind[[:space:]]+\*:109([[:space:]]|$)/d' /etc/haproxy/haproxy.cfg 2>/dev/null || true
        sed -i -E '/^[[:space:]]*bind[[:space:]]+\*:143([[:space:]]|$)/d' /etc/haproxy/haproxy.cfg 2>/dev/null || true
    fi

    if [[ -f "$TMP_DIR/limit/tun.conf" ]]; then
        cp -f "$TMP_DIR/limit/tun.conf" /usr/bin/tun.conf
        chmod 644 /usr/bin/tun.conf 2>/dev/null || true
    fi

    if [[ -f "$TMP_DIR/limit/ws.py" ]]; then
        cp -f "$TMP_DIR/limit/ws.py" /usr/bin/ws.py
        chmod 755 /usr/bin/ws.py 2>/dev/null || true
    fi

    if [[ -f "$TMP_DIR/limit/ws" ]]; then
        cp -f "$TMP_DIR/limit/ws" /usr/bin/ws
        chmod 755 /usr/bin/ws 2>/dev/null || true
    fi

    if [[ -f "$TMP_DIR/limit/ws.service" ]]; then
        cp -f "$TMP_DIR/limit/ws.service" /etc/systemd/system/ws.service
        chmod 644 /etc/systemd/system/ws.service 2>/dev/null || true
    fi

    mkdir -p /etc/systemd/system/dropbear.service.d
    cat >/etc/systemd/system/dropbear.service.d/override.conf <<'EOF'
[Service]
Environment=DROPBEAR_PORT=143
Environment=DROPBEAR_EXTRA_ARGS=-p 109
ExecStart=
ExecStart=/usr/sbin/dropbear -E -F -p 143 -p 109
EOF

    if [[ -f /etc/default/dropbear ]]; then
        sed -i 's/^DROPBEAR_PORT=.*/DROPBEAR_PORT=143/' /etc/default/dropbear 2>/dev/null || true
        sed -i 's/^DROPBEAR_EXTRA_ARGS=.*/DROPBEAR_EXTRA_ARGS="-p 109"/' /etc/default/dropbear 2>/dev/null || true
        grep -q '^DROPBEAR_EXTRA_ARGS=' /etc/default/dropbear || echo 'DROPBEAR_EXTRA_ARGS="-p 109"' >> /etc/default/dropbear
    fi

    # Keep legacy nodes aligned with SSH-WS tunnel route 109 from reference.
    if [[ -f /etc/nginx/conf.d/xray.conf ]]; then
        sed -i 's/X-Real-Host "127.0.0.1:143"/X-Real-Host "127.0.0.1:109"/g' /etc/nginx/conf.d/xray.conf 2>/dev/null || true
        sed -i 's/X-Real-Host "127.0.0.1:22"/X-Real-Host "127.0.0.1:109"/g' /etc/nginx/conf.d/xray.conf 2>/dev/null || true
        sed -i 's/listen 81 ssl reuseport;/listen 81 ssl http2 reuseport;/g' /etc/nginx/conf.d/xray.conf 2>/dev/null || true
        sed -i 's/listen 1013 proxy_protocol so_keepalive=on reuseport;/listen 1013 http2 proxy_protocol so_keepalive=on reuseport;/g' /etc/nginx/conf.d/xray.conf 2>/dev/null || true
        sed -i '/^\s*http2 on;\s*$/d' /etc/nginx/conf.d/xray.conf 2>/dev/null || true
    fi

    if [[ -f /usr/bin/tun.conf ]]; then
        sed -i 's/target_port: 143/target_port: 109/g' /usr/bin/tun.conf 2>/dev/null || true
        sed -i 's/target_port: 22/target_port: 109/g' /usr/bin/tun.conf 2>/dev/null || true
    fi

    systemctl daemon-reload >/dev/null 2>&1 || true
    if nginx -t >/dev/null 2>&1; then
        systemctl restart nginx >/dev/null 2>&1 || true
    fi
    if haproxy -c -f /etc/haproxy/haproxy.cfg >/dev/null 2>&1; then
        systemctl restart haproxy >/dev/null 2>&1 || true
    fi
    systemctl restart dropbear >/dev/null 2>&1 || true
    systemctl restart ws >/dev/null 2>&1 || true
}

old_sha="unknown"
[[ -f "$STATE_FILE" ]] && old_sha="$(cat "$STATE_FILE" 2>/dev/null || echo unknown)"
new_sha="$(git -C "$TMP_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"

mkdir -p "$TARGET_SBIN" /etc/kyt
cp -rf "$TMP_DIR/limit/menu/." "$TARGET_SBIN/"
chmod +x "$TARGET_SBIN"/* 2>/dev/null || true
sync_runtime_configs
echo "$new_sha" > "$STATE_FILE"

echo -e "\033[0;32mUpdate selesai.\033[0m"
echo -e "Old revision : $old_sha"
echo -e "New revision : $new_sha"
echo -e "Target path  : $TARGET_SBIN"
echo -e "Runtime cfg  : nginx/haproxy/ws synced"
