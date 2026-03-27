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

fetch_repo() {
    if git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP_DIR" >/dev/null 2>&1; then
        return 0
    fi

    rm -rf "$TMP_DIR"
    if git clone --branch "$BRANCH" "$REPO_URL" "$TMP_DIR" >/dev/null 2>&1; then
        return 0
    fi

    rm -rf "$TMP_DIR"
    mkdir -p "$TMP_DIR/src"
    if command -v curl >/dev/null 2>&1 && command -v tar >/dev/null 2>&1; then
        local archive_url extracted_dir
        archive_url="https://codeload.github.com/dalifajr/panelxray/tar.gz/refs/heads/$BRANCH"
        if curl -fsSL "$archive_url" -o "$TMP_DIR/repo.tgz" >/dev/null 2>&1 && \
           tar -xzf "$TMP_DIR/repo.tgz" -C "$TMP_DIR/src" >/dev/null 2>&1; then
            extracted_dir="$(find "$TMP_DIR/src" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
            if [[ -n "$extracted_dir" ]]; then
                cp -a "$extracted_dir"/. "$TMP_DIR"/
                rm -rf "$TMP_DIR/src" "$TMP_DIR/repo.tgz"
                return 0
            fi
        fi
    fi

    return 1
}

if ! fetch_repo; then
    echo -e "\033[1;31mGagal clone/download branch $BRANCH dari repository.\033[0m"
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
        mkdir -p /etc/whoiamluna
        cp -f /usr/bin/ws.py /etc/whoiamluna/ws.py 2>/dev/null || true
        chmod 755 /etc/whoiamluna/ws.py 2>/dev/null || true
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

    if [[ -f /etc/ssh/sshd_config ]]; then
        sed -i '/^Port 143$/d' /etc/ssh/sshd_config 2>/dev/null || true
        grep -q '^Port 22$' /etc/ssh/sshd_config || echo 'Port 22' >> /etc/ssh/sshd_config
        sed -i '/^[#[:space:]]*KexAlgorithms[[:space:]]/d' /etc/ssh/sshd_config 2>/dev/null || true
        sed -i '/^[#[:space:]]*HostKeyAlgorithms[[:space:]]/d' /etc/ssh/sshd_config 2>/dev/null || true
        cat >>/etc/ssh/sshd_config <<'EOF'
KexAlgorithms +diffie-hellman-group-exchange-sha256,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512,diffie-hellman-group14-sha256
HostKeyAlgorithms +ssh-rsa,ssh-rsa-cert-v01@openssh.com
EOF
    fi
    if systemctl list-unit-files 2>/dev/null | grep -q '^ssh\.socket'; then
        mkdir -p /etc/systemd/system/ssh.socket.d
        cat >/etc/systemd/system/ssh.socket.d/override.conf <<'EOF'
[Socket]
ListenStream=
ListenStream=0.0.0.0:22
ListenStream=[::]:22
EOF
        systemctl restart ssh.socket >/dev/null 2>&1 || true
    fi

    # Keep SSH-WS route aligned to dropbear main port to avoid drift.
    if [[ -f /etc/nginx/conf.d/xray.conf ]]; then
        sed -i 's/X-Real-Host "127.0.0.1:109"/X-Real-Host "127.0.0.1:143"/g' /etc/nginx/conf.d/xray.conf 2>/dev/null || true
        sed -i 's/X-Real-Host "127.0.0.1:22"/X-Real-Host "127.0.0.1:143"/g' /etc/nginx/conf.d/xray.conf 2>/dev/null || true
        sed -i 's/listen 81 ssl reuseport;/listen 81 ssl http2 reuseport;/g' /etc/nginx/conf.d/xray.conf 2>/dev/null || true
        sed -i 's/listen 1013 proxy_protocol so_keepalive=on reuseport;/listen 1013 http2 proxy_protocol so_keepalive=on reuseport;/g' /etc/nginx/conf.d/xray.conf 2>/dev/null || true
        sed -i '/^\s*http2 on;\s*$/d' /etc/nginx/conf.d/xray.conf 2>/dev/null || true
    fi

    if [[ -f /usr/bin/tun.conf ]]; then
        sed -i 's/target_port: 109/target_port: 143/g' /usr/bin/tun.conf 2>/dev/null || true
        sed -i 's/target_port: 22/target_port: 143/g' /usr/bin/tun.conf 2>/dev/null || true
    fi

    # Normalize xray routing tags to avoid outboundTag mismatch runtime drops.
    if [[ -f /etc/xray/config.json ]]; then
        sed -i '0,/"protocol"\s*:\s*"freedom"\s*,/s//"protocol": "freedom",\n      "tag": "direct",/' /etc/xray/config.json 2>/dev/null || true
        sed -i 's/"outboundTag"\s*:\s*"dnsOut"/"outboundTag": "direct"/g' /etc/xray/config.json 2>/dev/null || true
        sed -i 's/"outboundTag"\s*:\s*"api"/"outboundTag": "direct"/g' /etc/xray/config.json 2>/dev/null || true
        sed -i 's/"outboundTag"\s*:\s*"proxy"/"outboundTag": "direct"/g' /etc/xray/config.json 2>/dev/null || true
        sed -i 's/"outboundTag"\s*:\s*"reject"/"outboundTag": "blocked"/g' /etc/xray/config.json 2>/dev/null || true
        sed -i 's/"outboundTag"\s*:\s*"block"/"outboundTag": "blocked"/g' /etc/xray/config.json 2>/dev/null || true
    fi

    systemctl daemon-reload >/dev/null 2>&1 || true
    if nginx -t >/dev/null 2>&1; then
        systemctl restart nginx >/dev/null 2>&1 || true
    fi
    if haproxy -c -f /etc/haproxy/haproxy.cfg >/dev/null 2>&1; then
        systemctl restart haproxy >/dev/null 2>&1 || true
    fi
    systemctl restart ssh >/dev/null 2>&1 || systemctl restart sshd >/dev/null 2>&1 || true
    systemctl restart dropbear >/dev/null 2>&1 || true
    systemctl restart ws >/dev/null 2>&1 || true
    systemctl restart xray >/dev/null 2>&1 || true
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
