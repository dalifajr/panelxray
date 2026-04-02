#!/bin/bash
set -euo pipefail

REPO_URL="https://github.com/dalifajr/panelxray.git"
REPO_API="https://api.github.com/repos/dalifajr/panelxray"
TARGET_SBIN="/usr/local/sbin"
STATE_FILE="/etc/kyt/panelxray-revision"
TMP_DIR="/tmp/panelxray-update.$$"
BRANCH="${PANELXRAY_BRANCH:-}"
MECLI_ASSET_DIR="/usr/local/share/vpnxray/me-cli-sunset-main"
MECLI_INSTALL_DIR="/opt/vpnxray-me-cli-sunset"
MECLI_UPSTREAM_REPO_URL="https://github.com/dalifajr/xl-cli.git"
KYT_ASSETS_CHANGED=0
KYT_REQUIREMENTS_CHANGED=0
MECLI_ASSETS_CHANGED=0
KYT_RESTARTED=0
MECLI_BOT_RESTARTED=0
MECLI_CLI_RESTARTED=0

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

if [[ -z "$BRANCH" ]]; then
    BRANCH="$(curl -fsSL "$REPO_API" 2>/dev/null | awk -F '"' '/"default_branch"/ {print $4; exit}')"
    [[ -n "$BRANCH" ]] || BRANCH="main"
fi

safe_clear() {
    if [[ -t 1 && -n "${TERM:-}" ]]; then
        clear || true
    fi
}

safe_clear
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

ensure_dropbear_legacy_runtime() {
    local target_ver cur_ver src_root src_pkg tarball src_dir url
    target_ver="2019.78"
    cur_ver=""
    src_root="/usr/local/src"
    src_pkg="dropbear-${target_ver}"
    tarball="${src_root}/${src_pkg}.tar.bz2"
    src_dir="${src_root}/${src_pkg}"
    url="https://matt.ucc.asn.au/dropbear/releases/${src_pkg}.tar.bz2"

    if command -v /usr/sbin/dropbear >/dev/null 2>&1; then
        cur_ver="$(/usr/sbin/dropbear -V 2>&1 | sed -n 's/^Dropbear v\([0-9.]*\).*/\1/p' | head -n 1)"
    fi

    if [[ "$cur_ver" != "$target_ver" ]]; then
        apt-get install -y build-essential zlib1g-dev >/dev/null 2>&1 || apt install -y build-essential zlib1g-dev >/dev/null 2>&1 || true
        mkdir -p "$src_root"
        rm -rf "$src_dir"

        if command -v curl >/dev/null 2>&1; then
            curl -fsSL "$url" -o "$tarball" >/dev/null 2>&1 || true
        else
            wget -qO "$tarball" "$url" >/dev/null 2>&1 || true
        fi

        if [[ -s "$tarball" ]]; then
            tar -xjf "$tarball" -C "$src_root" >/dev/null 2>&1 || true
            if [[ -d "$src_dir" ]]; then
                (
                    cd "$src_dir" || exit 0
                    ./configure --prefix=/usr --sysconfdir=/etc/dropbear >/dev/null 2>&1 || exit 0
                    make PROGRAMS="dropbear dbclient dropbearkey dropbearconvert scp" >/dev/null 2>&1 || exit 0
                    install -m 0755 dropbear /usr/sbin/dropbear >/dev/null 2>&1 || true
                    install -m 0755 dropbearkey /usr/bin/dropbearkey >/dev/null 2>&1 || true
                    install -m 0755 dbclient /usr/bin/dbclient >/dev/null 2>&1 || true
                    install -m 0755 scp /usr/bin/scp >/dev/null 2>&1 || true
                )
            fi
        fi
    fi

    mkdir -p /etc/dropbear
    if [[ ! -s /etc/dropbear/dropbear_rsa_host_key ]]; then
        if command -v /usr/bin/dropbearkey >/dev/null 2>&1; then
            /usr/bin/dropbearkey -t rsa -f /etc/dropbear/dropbear_rsa_host_key >/dev/null 2>&1 || true
        fi
        chmod 600 /etc/dropbear/dropbear_rsa_host_key >/dev/null 2>&1 || true
    fi
}

disable_legacy_daily_reboot() {
    local cron_file backup_file
    cron_file="/etc/cron.d/daily_reboot"

    if [[ -f "$cron_file" ]] && grep -q '/sbin/reboot' "$cron_file" 2>/dev/null; then
        backup_file="${cron_file}.disabled.$(date +%Y%m%d%H%M%S)"
        cp -f "$cron_file" "$backup_file" 2>/dev/null || true
        rm -f "$cron_file"
        echo -e "\033[1;33mLegacy auto reboot dimatikan untuk mencegah lockout SSH. Backup: $backup_file\033[0m"
    fi

    if [[ -f /etc/cron.d/reboot_otomatis ]]; then
        backup_file="/etc/cron.d/reboot_otomatis.disabled.$(date +%Y%m%d%H%M%S)"
        cp -f /etc/cron.d/reboot_otomatis "$backup_file" 2>/dev/null || true
        rm -f /etc/cron.d/reboot_otomatis
        echo -e "\033[1;33mLegacy reboot_otomatis dimatikan untuk mencegah reboot tak terduga. Backup: $backup_file\033[0m"
    fi

    mkdir -p /home
    echo "0" >/home/daily_reboot 2>/dev/null || true
}

ensure_ssh_ports_in_iptables_rules() {
    local rules_file changed port rule
    rules_file="/etc/iptables/rules.v4"
    changed=0

    if [[ ! -f "$rules_file" ]] && command -v iptables-save >/dev/null 2>&1; then
        mkdir -p /etc/iptables
        iptables-save >"$rules_file" 2>/dev/null || true
    fi

    for port in 22 2222 2223 143 109; do
        if command -v iptables >/dev/null 2>&1; then
            iptables -C INPUT -p tcp -m tcp --dport "$port" -j ACCEPT >/dev/null 2>&1 || \
                iptables -I INPUT -p tcp -m tcp --dport "$port" -j ACCEPT >/dev/null 2>&1 || true
        fi

        [[ -f "$rules_file" ]] || continue
        rule="-A INPUT -p tcp -m tcp --dport ${port} -j ACCEPT"
        if ! grep -qF -- "$rule" "$rules_file" 2>/dev/null; then
            if grep -q '^:OUTPUT ' "$rules_file" 2>/dev/null; then
                sed -i "/^:OUTPUT /i ${rule}" "$rules_file" 2>/dev/null || true
            elif grep -q '^COMMIT$' "$rules_file" 2>/dev/null; then
                sed -i "/^COMMIT$/i ${rule}" "$rules_file" 2>/dev/null || true
            else
                printf '%s\n' "$rule" >>"$rules_file"
            fi
            changed=1
        fi
    done

    if [[ "$changed" -eq 1 ]]; then
        echo -e "\033[1;33mMenambahkan rule ACCEPT untuk port SSH management di $rules_file\033[0m"
    fi

    if command -v netfilter-persistent >/dev/null 2>&1; then
        netfilter-persistent save >/dev/null 2>&1 || true
        netfilter-persistent reload >/dev/null 2>&1 || true
    elif [[ -f "$rules_file" ]] && command -v iptables-restore >/dev/null 2>&1; then
        iptables-restore <"$rules_file" >/dev/null 2>&1 || true
    fi
}

install_boot_recovery_guard() {
    mkdir -p /usr/local/sbin /etc/systemd/system

    cat >/usr/local/sbin/panelxray-boot-guard <<'EOF'
#!/bin/bash
set -u

for cron_file in /etc/cron.d/daily_reboot /etc/cron.d/reboot_otomatis; do
  [ -f "$cron_file" ] && rm -f "$cron_file" >/dev/null 2>&1 || true
done

for port in 22 2222 2223 143 109; do
  if command -v iptables >/dev/null 2>&1; then
    iptables -C INPUT -p tcp -m tcp --dport "$port" -j ACCEPT >/dev/null 2>&1 || \
      iptables -I INPUT -p tcp -m tcp --dport "$port" -j ACCEPT >/dev/null 2>&1 || true
  fi
done

if command -v netfilter-persistent >/dev/null 2>&1; then
  netfilter-persistent save >/dev/null 2>&1 || true
  netfilter-persistent reload >/dev/null 2>&1 || true
fi

systemctl restart ssh >/dev/null 2>&1 || systemctl restart sshd >/dev/null 2>&1 || true
systemctl restart dropbear >/dev/null 2>&1 || true
systemctl restart xray >/dev/null 2>&1 || true
systemctl restart ws >/dev/null 2>&1 || true
systemctl restart nginx >/dev/null 2>&1 || true
systemctl restart haproxy >/dev/null 2>&1 || true

if systemctl list-unit-files 2>/dev/null | grep -q '^kyt\.service'; then
  systemctl restart kyt >/dev/null 2>&1 || true
fi

exit 0
EOF
    chmod 755 /usr/local/sbin/panelxray-boot-guard

    cat >/etc/systemd/system/panelxray-boot-guard.service <<'EOF'
[Unit]
Description=PanelXray boot access guard
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/panelxray-boot-guard
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload >/dev/null 2>&1 || true
    systemctl enable --now panelxray-boot-guard.service >/dev/null 2>&1 || true
}

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
        mkdir -p /etc/whoiamluna
        cp -f "$TMP_DIR/limit/ws.py" /etc/whoiamluna/ws.py 2>/dev/null || true
        chmod 755 /etc/whoiamluna/ws.py 2>/dev/null || true
        rm -f /usr/bin/ws.py 2>/dev/null || true
    fi

    if [[ -f "$TMP_DIR/limit/ws" ]]; then
        cp -f "$TMP_DIR/limit/ws" /usr/bin/ws
        chmod 755 /usr/bin/ws 2>/dev/null || true
    fi

    if [[ -f "$TMP_DIR/limit/ws.service" ]]; then
        cp -f "$TMP_DIR/limit/ws.service" /etc/systemd/system/ws.service
        chmod 644 /etc/systemd/system/ws.service 2>/dev/null || true
    fi

    ensure_dropbear_legacy_runtime
    disable_legacy_daily_reboot
    ensure_ssh_ports_in_iptables_rules
    install_boot_recovery_guard

    mkdir -p /etc/systemd/system/dropbear.service.d
    cat >/etc/systemd/system/dropbear.service.d/override.conf <<'EOF'
[Service]
Environment=DROPBEAR_PORT=143
Environment=DROPBEAR_EXTRA_ARGS=-p 109 -r /etc/dropbear/dropbear_rsa_host_key
ExecStart=
ExecStart=/usr/sbin/dropbear -E -F -r /etc/dropbear/dropbear_rsa_host_key -p 143 -p 109
EOF

    if [[ -f /etc/default/dropbear ]]; then
        sed -i 's/^DROPBEAR_PORT=.*/DROPBEAR_PORT=143/' /etc/default/dropbear 2>/dev/null || true
        sed -i 's|^DROPBEAR_EXTRA_ARGS=.*|DROPBEAR_EXTRA_ARGS="-p 109 -r /etc/dropbear/dropbear_rsa_host_key"|' /etc/default/dropbear 2>/dev/null || true
        grep -q '^DROPBEAR_EXTRA_ARGS=' /etc/default/dropbear || echo 'DROPBEAR_EXTRA_ARGS="-p 109 -r /etc/dropbear/dropbear_rsa_host_key"' >> /etc/default/dropbear
    fi

    if [[ -f /etc/ssh/sshd_config ]]; then
        sed -i '/^Port 143$/d' /etc/ssh/sshd_config 2>/dev/null || true
        grep -q '^Port 22$' /etc/ssh/sshd_config || echo 'Port 22' >> /etc/ssh/sshd_config
        sed -i '/^[#[:space:]]*GSSAPIKexAlgorithms[[:space:]]/d' /etc/ssh/sshd_config 2>/dev/null || true
        sed -i '/^[#[:space:]]*Ciphers[[:space:]]/d' /etc/ssh/sshd_config 2>/dev/null || true
        sed -i '/^[#[:space:]]*MACs[[:space:]]/d' /etc/ssh/sshd_config 2>/dev/null || true
        sed -i '/^[#[:space:]]*HostKeyAgent[[:space:]]/d' /etc/ssh/sshd_config 2>/dev/null || true
        sed -i '/^[#[:space:]]*KexAlgorithms[[:space:]]/d' /etc/ssh/sshd_config 2>/dev/null || true
        sed -i '/^[#[:space:]]*HostKeyAlgorithms[[:space:]]/d' /etc/ssh/sshd_config 2>/dev/null || true
        sed -i '/^[#[:space:]]*HostKey[[:space:]]\+\/etc\/ssh\/ssh_host_\(rsa\|ecdsa\|ed25519\)_key[[:space:]]*$/d' /etc/ssh/sshd_config 2>/dev/null || true
        cat >>/etc/ssh/sshd_config <<'EOF'
GSSAPIKexAlgorithms gss-gex-sha1-,gss-group14-sha1-
Ciphers chacha20-poly1305@openssh.com,aes128-ctr,aes192-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com
MACs umac-64-etm@openssh.com,umac-128-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512-etm@openssh.com,hmac-sha1-etm@openssh.com,umac-64@openssh.com,umac-128@openssh.com,hmac-sha2-256,hmac-sha2-512,hmac-sha1
HostKeyAgent none
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group-exchange-sha256,diffie-hellman-group16-sha512,diffie-hellman-group18-sha512,diffie-hellman-group14-sha256
HostKeyAlgorithms ecdsa-sha2-nistp256-cert-v01@openssh.com,ecdsa-sha2-nistp384-cert-v01@openssh.com,ecdsa-sha2-nistp521-cert-v01@openssh.com,sk-ecdsa-sha2-nistp256-cert-v01@openssh.com,ssh-ed25519-cert-v01@openssh.com,sk-ssh-ed25519-cert-v01@openssh.com,rsa-sha2-512-cert-v01@openssh.com,rsa-sha2-256-cert-v01@openssh.com,ssh-rsa-cert-v01@openssh.com,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,sk-ecdsa-sha2-nistp256@openssh.com,ssh-ed25519,sk-ssh-ed25519@openssh.com,rsa-sha2-512,rsa-sha2-256,ssh-rsa
HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key
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
    if systemctl list-unit-files 2>/dev/null | grep -q '^ssh\.service'; then
        systemctl enable ssh >/dev/null 2>&1 || true
    fi
    if systemctl list-unit-files 2>/dev/null | grep -q '^sshd\.service'; then
        systemctl enable sshd >/dev/null 2>&1 || true
    fi
    if systemctl list-unit-files 2>/dev/null | grep -q '^dropbear\.service'; then
        systemctl enable dropbear >/dev/null 2>&1 || true
    fi
    if systemctl list-unit-files 2>/dev/null | grep -q '^ws\.service'; then
        systemctl enable ws >/dev/null 2>&1 || true
    fi
    if systemctl list-unit-files 2>/dev/null | grep -q '^xray\.service'; then
        systemctl enable xray >/dev/null 2>&1 || true
    fi
    if systemctl list-unit-files 2>/dev/null | grep -q '^kyt\.service'; then
        systemctl enable kyt >/dev/null 2>&1 || true
    fi
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

sync_kyt_bot_assets() {
    local kyt_dir venv_pip

    if [[ "${KYT_ASSETS_CHANGED:-0}" != "1" ]]; then
        return 0
    fi

    kyt_dir="/usr/bin/kyt"
    venv_pip="${kyt_dir}/.venv/bin/pip"

    if [[ -d "$TMP_DIR/limit/bot" ]]; then
        cp -rf "$TMP_DIR/limit/bot/." /usr/bin/ 2>/dev/null || true
        chmod +x /usr/bin/bot-* 2>/dev/null || true
    fi

    if [[ -d "$TMP_DIR/limit/kyt" ]]; then
        mkdir -p "$kyt_dir"
        cp -rf "$TMP_DIR/limit/kyt/." "$kyt_dir/"
    fi

    if [[ "${KYT_REQUIREMENTS_CHANGED:-0}" == "1" && -x "$venv_pip" && -f "${kyt_dir}/requirements.txt" ]]; then
        "$venv_pip" install -r "${kyt_dir}/requirements.txt" >/dev/null 2>&1 || true
    fi

    if systemctl list-unit-files 2>/dev/null | grep -q '^kyt\.service'; then
        systemctl daemon-reload >/dev/null 2>&1 || true
        systemctl enable --now kyt >/dev/null 2>&1 || systemctl restart kyt >/dev/null 2>&1 || true
        KYT_RESTARTED=1
    fi
}

is_valid_me_cli_source() {
    local dir="$1"
    [[ -d "$dir" ]] || return 1
    [[ -f "$dir/requirements.txt" ]] || return 1
    [[ -f "$dir/main.py" ]] || return 1
    [[ -f "$dir/panel.sh" ]] || return 1
    [[ -f "$dir/telegram_main.py" ]] || return 1
    [[ -d "$dir/app" ]] || return 1
    [[ -d "$dir/app/client" ]] || return 1
    [[ -d "$dir/app/menus" ]] || return 1
    [[ -d "$dir/app/service" ]] || return 1
    [[ -d "$dir/app/bot_handlers" ]] || return 1
    [[ -f "$dir/app/service/auth.py" ]] || return 1
    [[ -f "$dir/app/service/decoy.py" ]] || return 1
    [[ -d "$dir/hot_data" ]] || return 1
    [[ -f "$dir/hot_data/hot.json" ]] || return 1
    [[ -f "$dir/hot_data/hot2.json" ]] || return 1
    [[ -d "$dir/decoy_data" ]] || return 1
    [[ -f "$dir/decoy_data/decoy-default-balance.json" ]] || return 1
    [[ -f "$dir/decoy_data/decoy-default-qris.json" ]] || return 1
    return 0
}

resolve_me_cli_source_dir() {
    local root="$1"
    local candidate
    local candidates=(
        "$root"
        "$root/limit/me-cli-sunset-main"
        "$root/me-cli-sunset-main"
        "$root/me-cli-sunset"
    )

    for candidate in "${candidates[@]}"; do
        if is_valid_me_cli_source "$candidate"; then
            printf '%s' "$candidate"
            return 0
        fi
    done

    while IFS= read -r candidate; do
        candidate="$(dirname "$candidate")"
        if is_valid_me_cli_source "$candidate"; then
            printf '%s' "$candidate"
            return 0
        fi
    done < <(find "$root" -maxdepth 5 -type f -name "requirements.txt" 2>/dev/null)

    return 1
}

sync_me_cli_assets() {
    local src_dir resolved_src upstream_dir

    if [[ "${MECLI_ASSETS_CHANGED:-0}" != "1" ]]; then
        return 0
    fi

    src_dir="$TMP_DIR/limit/me-cli-sunset-main"
    resolved_src="$(resolve_me_cli_source_dir "$src_dir" || true)"

    if [[ -z "$resolved_src" ]]; then
        upstream_dir="$TMP_DIR/mecli-upstream"
        rm -rf "$upstream_dir"
        if git clone --depth 1 "$MECLI_UPSTREAM_REPO_URL" "$upstream_dir" >/dev/null 2>&1; then
            resolved_src="$(resolve_me_cli_source_dir "$upstream_dir" || true)"
        fi
    fi

    if [[ -z "$resolved_src" ]]; then
        echo -e "\033[1;31mAsset me-cli valid tidak ditemukan (source update/upstream), sinkronisasi dilewati.\033[0m"
        return 0
    fi

    mkdir -p "$MECLI_ASSET_DIR"
    find "$MECLI_ASSET_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
    cp -a "$resolved_src"/. "$MECLI_ASSET_DIR"/

    rm -rf "$MECLI_ASSET_DIR/.git" "$MECLI_ASSET_DIR/.venv" "$MECLI_ASSET_DIR/logs" "$MECLI_ASSET_DIR/run" "$MECLI_ASSET_DIR/__pycache__"
    find "$MECLI_ASSET_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
    find "$MECLI_ASSET_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    rm -f "$MECLI_ASSET_DIR/.env"
}

auto_refresh_me_cli_runtime() {
    local installer sync_log

    if [[ "${MECLI_ASSETS_CHANGED:-0}" != "1" ]]; then
        return 0
    fi

    installer="${TARGET_SBIN}/install-me-cli"
    sync_log="/tmp/panelxray-me-cli-sync.log"

    if [[ ! -d "$MECLI_INSTALL_DIR" ]]; then
        return 0
    fi

    if [[ ! -x "$installer" ]]; then
        echo -e "\033[1;31mSinkronisasi runtime me-cli dilewati: installer $installer tidak ditemukan.\033[0m"
        return 0
    fi

    echo -e "\033[1;33mme-cli terpasang, menjalankan sinkronisasi runtime...\033[0m"
    if "$installer" --sync-only --non-interactive >"$sync_log" 2>&1; then
        echo -e "\033[0;32mSinkronisasi runtime me-cli berhasil.\033[0m"
    else
        echo -e "\033[1;31mSinkronisasi runtime me-cli gagal. Lihat log: $sync_log\033[0m"
    fi
}

restart_me_cli_runtime_if_running() {
    local app_dir venv_py bot_pid_file cli_pid_file pid

    if [[ "${MECLI_ASSETS_CHANGED:-0}" != "1" ]]; then
        return 0
    fi

    app_dir="$MECLI_INSTALL_DIR"
    venv_py="${app_dir}/.venv/bin/python"
    bot_pid_file="${app_dir}/run/telegram_bot.pid"
    cli_pid_file="${app_dir}/run/cli.pid"

    if [[ ! -d "$app_dir" || ! -x "$venv_py" ]]; then
        return 0
    fi

    mkdir -p "${app_dir}/run" "${app_dir}/logs"

    if [[ -f "$bot_pid_file" ]]; then
        pid="$(cat "$bot_pid_file" 2>/dev/null || true)"
        if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
            kill "$pid" >/dev/null 2>&1 || true
            sleep 1
            if kill -0 "$pid" >/dev/null 2>&1; then
                kill -9 "$pid" >/dev/null 2>&1 || true
            fi
            (cd "$app_dir" && nohup "$venv_py" telegram_main.py >> "${app_dir}/logs/telegram_bot.log" 2>&1 & echo $! > "$bot_pid_file")
            MECLI_BOT_RESTARTED=1
        fi
    fi

    if [[ -f "$cli_pid_file" ]]; then
        pid="$(cat "$cli_pid_file" 2>/dev/null || true)"
        if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
            kill "$pid" >/dev/null 2>&1 || true
            sleep 1
            if kill -0 "$pid" >/dev/null 2>&1; then
                kill -9 "$pid" >/dev/null 2>&1 || true
            fi
            (cd "$app_dir" && nohup "$venv_py" main.py >> "${app_dir}/logs/cli.log" 2>&1 & echo $! > "$cli_pid_file")
            MECLI_CLI_RESTARTED=1
        fi
    fi
}

detect_bot_asset_changes() {
    local changed

    KYT_ASSETS_CHANGED=0
    KYT_REQUIREMENTS_CHANGED=0
    MECLI_ASSETS_CHANGED=0

    if [[ "$old_sha" == "unknown" ]] || ! git -C "$TMP_DIR" rev-parse --verify --quiet "$old_sha" >/dev/null 2>&1; then
        if [[ -d "$TMP_DIR/limit/kyt" || -d "$TMP_DIR/limit/bot" ]]; then
            KYT_ASSETS_CHANGED=1
        fi
        if [[ -d "$TMP_DIR/limit/me-cli-sunset-main" ]]; then
            MECLI_ASSETS_CHANGED=1
        fi
        return 0
    fi

    changed="$(git -C "$TMP_DIR" diff --name-only "$old_sha" "$new_sha" 2>/dev/null || true)"
    if [[ -z "$changed" ]]; then
        return 0
    fi

    if printf '%s\n' "$changed" | grep -qE '^limit/(kyt|bot)/'; then
        KYT_ASSETS_CHANGED=1
    fi
    if printf '%s\n' "$changed" | grep -qE '^limit/kyt/requirements\.txt$'; then
        KYT_REQUIREMENTS_CHANGED=1
    fi
    if printf '%s\n' "$changed" | grep -qE '^limit/me-cli-sunset-main/'; then
        MECLI_ASSETS_CHANGED=1
    fi
}

is_webpanel_present() {
    if systemctl list-unit-files 2>/dev/null | grep -q '^vpnxray-webpanel\.service'; then
        return 0
    fi

    if [[ -d /opt/vpnxray-webpanel || -f /etc/kyt/webpanel.env ]]; then
        return 0
    fi

    if [[ -f /etc/nginx/conf.d/xray.conf ]] && grep -q "BEGIN VPNXRAY WEB PANEL" /etc/nginx/conf.d/xray.conf 2>/dev/null; then
        return 0
    fi

    return 1
}

run_webpanel_regression_gate() {
    local gate_runner gate_log source_dir
    gate_runner="${TARGET_SBIN}/panel-mvc-regression-gate"
    gate_log="/tmp/panelxray-webpanel-regression.log"
    source_dir="${TMP_DIR}/limit/menu/webpanel-mvc"

    if [[ "${PANEL_REGRESSION_GATE:-1}" == "0" ]]; then
        echo -e "\033[1;33mRegression gate panel dilewati (PANEL_REGRESSION_GATE=0).\033[0m"
        return 0
    fi

    if ! is_webpanel_present; then
        return 0
    fi

    if [[ ! -x "$gate_runner" ]]; then
        echo -e "\033[1;31mRegression gate dilewati: $gate_runner tidak ditemukan.\033[0m"
        return 0
    fi

    if [[ ! -d "$source_dir" ]]; then
        echo -e "\033[1;31mRegression gate dilewati: source webpanel tidak ditemukan di $source_dir.\033[0m"
        return 0
    fi

    echo -e "\033[1;33mMenjalankan regression gate web panel sebelum deploy produksi...\033[0m"
    if "$gate_runner" --source "$source_dir" --skip-mirror-check >"$gate_log" 2>&1; then
        echo -e "\033[0;32mRegression gate web panel lulus.\033[0m"
        return 0
    fi

    echo -e "\033[1;31mRegression gate web panel gagal. Lihat log: $gate_log\033[0m"
    tail -n 20 "$gate_log" 2>/dev/null || true
    echo -e "\033[1;31mUpdate dihentikan untuk mencegah deploy panel yang regresif.\033[0m"
    echo -e "\033[1;33mJika darurat, jalankan ulang dengan PANEL_REGRESSION_GATE=0.\033[0m"
    exit 1
}

auto_fix_webpanel_route() {
    local installer fix_log
    installer="${TARGET_SBIN}/install-panel-mvc"
    fix_log="/tmp/panelxray-webpanel-fix.log"

    if ! is_webpanel_present; then
        return 0
    fi

    if [[ ! -x "$installer" ]]; then
        echo -e "\033[1;31mAuto-fix /panel dilewati: installer $installer tidak ditemukan.\033[0m"
        return 0
    fi

    echo -e "\033[1;33mWeb panel MVC terdeteksi, menjalankan sinkronisasi panel (assets + route)...\033[0m"
    if "$installer" --non-interactive >"$fix_log" 2>&1; then
        echo -e "\033[0;32mSinkronisasi web panel berhasil.\033[0m"
    else
        echo -e "\033[1;31mSinkronisasi web panel gagal, mencoba fallback auto-fix route /panel...\033[0m"
        if "$installer" --repair-nginx >>"$fix_log" 2>&1; then
            echo -e "\033[0;32mFallback auto-fix /panel berhasil.\033[0m"
        else
            echo -e "\033[1;31mFallback auto-fix /panel gagal. Lihat log: $fix_log\033[0m"
        fi
    fi
}

old_sha="unknown"
[[ -f "$STATE_FILE" ]] && old_sha="$(cat "$STATE_FILE" 2>/dev/null || echo unknown)"
new_sha="$(git -C "$TMP_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
detect_bot_asset_changes

mkdir -p "$TARGET_SBIN" /etc/kyt
cp -rf "$TMP_DIR/limit/menu/." "$TARGET_SBIN/"
chmod +x "$TARGET_SBIN"/* 2>/dev/null || true
run_webpanel_regression_gate
sync_runtime_configs
sync_kyt_bot_assets
sync_me_cli_assets
auto_refresh_me_cli_runtime
restart_me_cli_runtime_if_running
auto_fix_webpanel_route
echo "$new_sha" > "$STATE_FILE"

echo -e "\033[0;32mUpdate selesai.\033[0m"
echo -e "Old revision : $old_sha"
echo -e "New revision : $new_sha"
echo -e "Target path  : $TARGET_SBIN"
echo -e "Regression   : panel gate dijalankan otomatis (set PANEL_REGRESSION_GATE=0 untuk bypass darurat)"
echo -e "Runtime cfg  : nginx/haproxy/ws synced"
if [[ "$KYT_ASSETS_CHANGED" == "1" ]]; then
    echo -e "KYT sync     : /usr/bin/kyt + bot scripts disinkronkan"
    if [[ "$KYT_RESTARTED" == "1" ]]; then
        echo -e "KYT restart  : kyt.service di-restart"
    fi
fi
if [[ "$MECLI_ASSETS_CHANGED" == "1" ]]; then
    echo -e "ME-CLI sync  : asset me-cli disinkronkan"
    if [[ "$MECLI_BOT_RESTARTED" == "1" || "$MECLI_CLI_RESTARTED" == "1" ]]; then
        echo -e "ME-CLI restart: proses aktif me-cli di-restart"
    fi
fi
echo -e "Web panel    : sinkronisasi panel + auto-fix /panel dijalankan jika panel terdeteksi"
