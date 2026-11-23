#!/bin/bash
set -Eeuo pipefail

REPO_URL="https://github.com/dalifajr/panelxray.git"
REPO_API="https://api.github.com/repos/dalifajr/panelxray"
TARGET_SBIN="/usr/local/sbin"
STATE_FILE="/etc/kyt/panelxray-revision"
TMP_DIR="/tmp/panelxray-update.$$"
WEBPANEL_PRESERVE_DIR="/tmp/panelxray-webpanel-preserve.$$"
BRANCH="${PANELXRAY_BRANCH:-}"
MECLI_ASSET_DIR="/usr/local/share/vpnxray/me-cli-sunset-main"
MECLI_INSTALL_DIR="/opt/vpnxray-me-cli-sunset"
MECLI_UPSTREAM_REPO_URL="https://github.com/dalifajr/xl-cli.git"
UPDATE_LOG="/var/log/panelxray-update.log"
START_TS="$(date +%s)"

KYT_ASSETS_CHANGED=0
KYT_REQUIREMENTS_CHANGED=0
MECLI_ASSETS_CHANGED=0
KYT_RESTARTED=0
MECLI_BOT_RESTARTED=0
MECLI_CLI_RESTARTED=0
WEBPANEL_UPDATED=0
COMPOSER_STATUS="skipped"
MIGRATE_STATUS="skipped"

if ! touch "$UPDATE_LOG" 2>/dev/null; then
    UPDATE_LOG="/tmp/panelxray-update.log"
    touch "$UPDATE_LOG" 2>/dev/null || true
fi
if [[ -f "$UPDATE_LOG" ]]; then
    log_size="$(wc -c < "$UPDATE_LOG" 2>/dev/null || echo 0)"
    if [[ "$log_size" -gt 5242880 ]]; then
        mv -f "$UPDATE_LOG" "${UPDATE_LOG}.old" 2>/dev/null || true
        : > "$UPDATE_LOG" 2>/dev/null || true
    fi
fi

ts_now() { date '+%H:%M:%S'; }
log_raw() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >> "$UPDATE_LOG" 2>/dev/null || true; }
log_step() { local ts; ts="$(ts_now)"; echo -e "\033[1;36m[update][${ts}]\033[0m $*"; log_raw "[STEP] $*"; }
log_info() { local ts; ts="$(ts_now)"; echo -e "\033[0;90m[update][${ts}]\033[0m $*"; log_raw "[INFO] $*"; }
log_ok()   { local ts; ts="$(ts_now)"; echo -e "\033[0;32m[update][${ts}][OK]\033[0m $*"; log_raw "[OK] $*"; }
log_warn() { local ts; ts="$(ts_now)"; echo -e "\033[1;33m[update][${ts}][WARN]\033[0m $*"; log_raw "[WARN] $*"; }
log_err()  { local ts; ts="$(ts_now)"; echo -e "\033[1;31m[update][${ts}][ERROR]\033[0m $*" >&2; log_raw "[ERROR] $*"; }

run_logged() {
    local desc="$1"
    shift
    local rc=0
    log_info "Menjalankan: ${desc}"
    log_raw "CMD: $*"
    set +e
    "$@" 2>&1 | while IFS= read -r line; do
        printf '  %s\n' "$line"
        printf '  %s\n' "$line" >> "$UPDATE_LOG" 2>/dev/null || true
    done
    rc=${PIPESTATUS[0]}
    set -e
    return "$rc"
}

cleanup() {
    rm -rf "$TMP_DIR" "$WEBPANEL_PRESERVE_DIR" 2>/dev/null || true
}

on_error() {
    local exit_code="$?"
    local line_no="${BASH_LINENO[0]:-unknown}"
    local cmd="${BASH_COMMAND:-unknown}"
    log_err "Update gagal pada baris ${line_no} (exit=${exit_code}): ${cmd}"
    log_warn "Lihat log lengkap di: ${UPDATE_LOG}"
    exit "${exit_code}"
}

trap cleanup EXIT
trap on_error ERR

safe_clear() {
    if [[ -t 1 && -n "${TERM:-}" ]]; then
        clear || true
    fi
}

safe_clear
log_raw "==================== START UPDATE (maintenance/update.sh) ===================="
echo -e "\033[1;36m==========================================================\033[0m"
echo -e "\033[1;33m                 UPDATE PROGRAM (GITHUB)                  \033[0m"
echo -e "\033[1;36m==========================================================\033[0m"

log_step "[1/10] Memeriksa prasyarat sistem, branch target, dan ruang disk..."

if ! command -v git >/dev/null 2>&1; then
    log_err "Git tidak ditemukan. Install git terlebih dahulu."
    exit 1
fi

if [[ -z "$BRANCH" ]]; then
    BRANCH="$(curl -fsSL --max-time 10 "$REPO_API" 2>/dev/null | awk -F '"' '/"default_branch"/ {print $4; exit}' || true)"
    [[ -n "$BRANCH" ]] || BRANCH="main"
fi

free_root_mb="$(df -Pm / 2>/dev/null | awk 'NR==2 {print $4}' || echo "?")"
log_info "Branch target : ${BRANCH}"
log_info "Log file      : ${UPDATE_LOG}"
log_info "Sisa disk (/) : ${free_root_mb} MB"

mkdir -p "$TMP_DIR"

fetch_repo() {
    log_info "Mencoba git clone shallow (--depth 1) branch '${BRANCH}'..."
    if run_logged "git clone --depth 1" git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP_DIR"; then
        log_ok "Clone repository berhasil (shallow)."
        return 0
    fi

    rm -rf "$TMP_DIR"
    log_warn "Shallow clone gagal, mencoba full clone..."
    if run_logged "git clone full" git clone --branch "$BRANCH" "$REPO_URL" "$TMP_DIR"; then
        log_ok "Clone repository berhasil (full)."
        return 0
    fi

    rm -rf "$TMP_DIR"
    mkdir -p "$TMP_DIR/src"
    if command -v curl >/dev/null 2>&1 && command -v tar >/dev/null 2>&1; then
        local archive_url extracted_dir
        archive_url="https://codeload.github.com/dalifajr/panelxray/tar.gz/refs/heads/$BRANCH"
        log_warn "Git clone gagal, mencoba fallback download tarball GitHub..."
        if curl -fsSL --max-time 60 "$archive_url" -o "$TMP_DIR/repo.tgz" 2>>"$UPDATE_LOG" && \
           tar -xzf "$TMP_DIR/repo.tgz" -C "$TMP_DIR/src" 2>>"$UPDATE_LOG"; then
            extracted_dir="$(find "$TMP_DIR/src" -mindepth 1 -maxdepth 1 -type d | head -n 1)"
            if [[ -n "$extracted_dir" ]]; then
                cp -a "$extracted_dir"/. "$TMP_DIR"/
                rm -rf "$TMP_DIR/src" "$TMP_DIR/repo.tgz"
                log_ok "Download tarball repository berhasil."
                return 0
            fi
        fi
    fi

    return 1
}

log_step "[2/10] Mengunduh pembaruan terbaru dari GitHub (${REPO_URL})..."
if ! fetch_repo; then
    log_err "Gagal clone/download branch $BRANCH dari repository."
    exit 1
fi

if [[ ! -d "$TMP_DIR/limit/menu" ]]; then
    log_err "Struktur repository tidak valid: limit/menu tidak ditemukan."
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
        cur_ver="$(/usr/sbin/dropbear -V 2>&1 | sed -n 's/^Dropbear v\([0-9.]*\).*/\1/p' | head -n 1 || true)"
    fi

    if [[ "$cur_ver" != "$target_ver" ]]; then
        log_info "Dropbear versi '${cur_ver:-none}' != '${target_ver}', membangun Dropbear ${target_ver}..."
        apt-get install -y build-essential zlib1g-dev >>"$UPDATE_LOG" 2>&1 || apt install -y build-essential zlib1g-dev >>"$UPDATE_LOG" 2>&1 || true
        mkdir -p "$src_root"
        rm -rf "$src_dir"

        if command -v curl >/dev/null 2>&1; then
            curl -fsSL --max-time 60 "$url" -o "$tarball" >>"$UPDATE_LOG" 2>&1 || true
        else
            wget -qO "$tarball" "$url" >>"$UPDATE_LOG" 2>&1 || true
        fi

        if [[ -s "$tarball" ]]; then
            tar -xjf "$tarball" -C "$src_root" >>"$UPDATE_LOG" 2>&1 || true
            if [[ -d "$src_dir" ]]; then
                (
                    cd "$src_dir" || exit 0
                    ./configure --prefix=/usr --sysconfdir=/etc/dropbear >>"$UPDATE_LOG" 2>&1 || exit 0
                    make PROGRAMS="dropbear dbclient dropbearkey dropbearconvert scp" >>"$UPDATE_LOG" 2>&1 || exit 0
                    install -m 0755 dropbear /usr/sbin/dropbear >>"$UPDATE_LOG" 2>&1 || true
                    install -m 0755 dropbearkey /usr/bin/dropbearkey >>"$UPDATE_LOG" 2>&1 || true
                    install -m 0755 dbclient /usr/bin/dbclient >>"$UPDATE_LOG" 2>&1 || true
                    install -m 0755 scp /usr/bin/scp >>"$UPDATE_LOG" 2>&1 || true
                )
            fi
        fi
    fi

    mkdir -p /etc/dropbear
    if [[ ! -s /etc/dropbear/dropbear_rsa_host_key ]]; then
        if command -v /usr/bin/dropbearkey >/dev/null 2>&1; then
            /usr/bin/dropbearkey -t rsa -f /etc/dropbear/dropbear_rsa_host_key >>"$UPDATE_LOG" 2>&1 || true
        fi
        chmod 600 /etc/dropbear/dropbear_rsa_host_key 2>/dev/null || true
    fi
}

disable_legacy_daily_reboot() {
    local cron_file backup_file
    cron_file="/etc/cron.d/daily_reboot"

    if [[ -f "$cron_file" ]] && grep -q '/sbin/reboot' "$cron_file" 2>/dev/null; then
        backup_file="${cron_file}.disabled.$(date +%Y%m%d%H%M%S)"
        cp -f "$cron_file" "$backup_file" 2>/dev/null || true
        rm -f "$cron_file"
        log_warn "Legacy auto reboot dimatikan untuk mencegah lockout SSH. Backup: $backup_file"
    fi

    if [[ -f /etc/cron.d/reboot_otomatis ]]; then
        backup_file="/etc/cron.d/reboot_otomatis.disabled.$(date +%Y%m%d%H%M%S)"
        cp -f /etc/cron.d/reboot_otomatis "$backup_file" 2>/dev/null || true
        rm -f /etc/cron.d/reboot_otomatis
        log_warn "Legacy reboot_otomatis dimatikan untuk mencegah reboot tak terduga. Backup: $backup_file"
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
        log_info "Menambahkan rule ACCEPT untuk port SSH management di $rules_file"
    fi

    if command -v netfilter-persistent >/dev/null 2>&1; then
        netfilter-persistent save >>"$UPDATE_LOG" 2>&1 || true
        netfilter-persistent reload >>"$UPDATE_LOG" 2>&1 || true
    elif [[ -f "$rules_file" ]] && command -v iptables-restore >/dev/null 2>&1; then
        iptables-restore <"$rules_file" >>"$UPDATE_LOG" 2>&1 || true
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
elif command -v iptables-save >/dev/null 2>&1; then
    mkdir -p /etc/iptables
    iptables-save >/etc/iptables/rules.v4 2>/dev/null || true
fi

if systemctl list-unit-files 2>/dev/null | grep -q '^ssh\.socket'; then
    systemctl enable ssh.socket >/dev/null 2>&1 || true
    systemctl restart ssh.socket >/dev/null 2>&1 || true
fi

for unit in ssh sshd dropbear ws xray cron kyt; do
    if systemctl list-unit-files 2>/dev/null | grep -q "^${unit}\.service"; then
        systemctl reset-failed "$unit" >/dev/null 2>&1 || true
        systemctl enable "$unit" >/dev/null 2>&1 || true
        systemctl restart "$unit" >/dev/null 2>&1 || true
    fi
done

systemctl restart nginx >/dev/null 2>&1 || true
systemctl restart haproxy >/dev/null 2>&1 || true

rm -f /etc/cron.d/daily_reboot /etc/cron.d/reboot_otomatis 2>/dev/null || true

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

    systemctl daemon-reload >>"$UPDATE_LOG" 2>&1 || true
    systemctl enable --now panelxray-boot-guard.service >>"$UPDATE_LOG" 2>&1 || true
}

ensure_ws_epro_service() {
    local ws_unit ws_runner ws_script
    ws_unit="/etc/systemd/system/ws.service"
    ws_runner="/usr/bin/ws"
    ws_script="/etc/whoiamluna/ws.py"

    mkdir -p /etc/whoiamluna

    if [[ -f "$TMP_DIR/limit/ws.py" ]]; then
        cp -f "$TMP_DIR/limit/ws.py" "$ws_script" 2>/dev/null || true
        chmod 755 "$ws_script" 2>/dev/null || true
    fi

    if [[ -f "$TMP_DIR/limit/ws" ]]; then
        cp -f "$TMP_DIR/limit/ws" "$ws_runner" 2>/dev/null || true
        chmod 755 "$ws_runner" 2>/dev/null || true
    fi

    if [[ -f "$TMP_DIR/limit/ws.service" ]]; then
        cp -f "$TMP_DIR/limit/ws.service" "$ws_unit" 2>/dev/null || true
        chmod 644 "$ws_unit" 2>/dev/null || true
    fi

    if ! command -v /usr/bin/python3 >/dev/null 2>&1; then
        apt-get install -y python3 >>"$UPDATE_LOG" 2>&1 || apt install -y python3 >>"$UPDATE_LOG" 2>&1 || true
    fi

    if ! systemctl list-unit-files 2>/dev/null | grep -q '^ws\.service'; then
        return 0
    fi

    systemctl daemon-reload >>"$UPDATE_LOG" 2>&1 || true
    systemctl unmask ws >>"$UPDATE_LOG" 2>&1 || true
    systemctl reset-failed ws >>"$UPDATE_LOG" 2>&1 || true
    systemctl enable ws >>"$UPDATE_LOG" 2>&1 || true
    systemctl restart ws >>"$UPDATE_LOG" 2>&1 || systemctl start ws >>"$UPDATE_LOG" 2>&1 || true

    if ! systemctl is-active --quiet ws; then
        if command -v pkill >/dev/null 2>&1; then
            pkill -f '/etc/whoiamluna/ws.py' >/dev/null 2>&1 || true
        fi
        sleep 1
        systemctl reset-failed ws >>"$UPDATE_LOG" 2>&1 || true
        systemctl start ws >>"$UPDATE_LOG" 2>&1 || true
    fi

    if ! systemctl is-active --quiet ws; then
        log_warn "Service ws belum aktif setelah update. Jalankan: journalctl -u ws -n 40 --no-pager"
    fi
}

report_service_status() {
    local svc="$1"
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        log_ok "Service ${svc}: active"
    elif systemctl list-unit-files 2>/dev/null | grep -q "^${svc}\.service"; then
        log_warn "Service ${svc}: tidak aktif ($(systemctl is-active "$svc" 2>/dev/null || echo inactive))"
    fi
}

sync_runtime_configs() {
    local domain
    domain="$(cat /etc/xray/domain 2>/dev/null || hostname -f 2>/dev/null || hostname 2>/dev/null || echo localhost)"
    log_info "Domain runtime terdeteksi: ${domain}"

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
        systemctl restart ssh.socket >>"$UPDATE_LOG" 2>&1 || true
    fi

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

    if [[ -f /etc/xray/config.json ]]; then
        sed -i '0,/"protocol"\s*:\s*"freedom"\s*,/s//"protocol": "freedom",\n      "tag": "direct",/' /etc/xray/config.json 2>/dev/null || true
        sed -i 's/"outboundTag"\s*:\s*"dnsOut"/"outboundTag": "direct"/g' /etc/xray/config.json 2>/dev/null || true
        sed -i 's/"outboundTag"\s*:\s*"api"/"outboundTag": "direct"/g' /etc/xray/config.json 2>/dev/null || true
        sed -i 's/"outboundTag"\s*:\s*"proxy"/"outboundTag": "direct"/g' /etc/xray/config.json 2>/dev/null || true
        sed -i 's/"outboundTag"\s*:\s*"reject"/"outboundTag": "blocked"/g' /etc/xray/config.json 2>/dev/null || true
        sed -i 's/"outboundTag"\s*:\s*"block"/"outboundTag": "blocked"/g' /etc/xray/config.json 2>/dev/null || true
    fi

    systemctl daemon-reload >>"$UPDATE_LOG" 2>&1 || true
    for unit in ssh.socket ssh sshd dropbear ws xray kyt; do
        if systemctl list-unit-files 2>/dev/null | grep -q "^${unit}"; then
            systemctl enable "$unit" >>"$UPDATE_LOG" 2>&1 || true
        fi
    done

    if command -v nginx >/dev/null 2>&1; then
        if nginx -t >>"$UPDATE_LOG" 2>&1; then
            systemctl restart nginx >>"$UPDATE_LOG" 2>&1 || true
            report_service_status nginx
        else
            log_warn "Validasi nginx -t gagal! Cek detail di ${UPDATE_LOG}."
        fi
    fi

    if command -v haproxy >/dev/null 2>&1; then
        if haproxy -c -f /etc/haproxy/haproxy.cfg >>"$UPDATE_LOG" 2>&1; then
            systemctl restart haproxy >>"$UPDATE_LOG" 2>&1 || true
            report_service_status haproxy
        else
            log_warn "Validasi haproxy.cfg gagal! Cek detail di ${UPDATE_LOG}."
        fi
    fi

    systemctl restart ssh >>"$UPDATE_LOG" 2>&1 || systemctl restart sshd >>"$UPDATE_LOG" 2>&1 || true
    systemctl restart dropbear >>"$UPDATE_LOG" 2>&1 || true
    ensure_ws_epro_service
    systemctl restart xray >>"$UPDATE_LOG" 2>&1 || true

    report_service_status dropbear
    report_service_status ws
    report_service_status xray
}

sync_kyt_bot_assets() {
    local kyt_dir venv_pip

    if [[ "${KYT_ASSETS_CHANGED:-0}" != "1" ]]; then
        log_info "Aset bot KYT tidak berubah (dilewati)."
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
        run_logged "pip install requirements KYT" timeout 180 "$venv_pip" install --no-input -r "${kyt_dir}/requirements.txt" || true
    fi

    if systemctl list-unit-files 2>/dev/null | grep -q '^kyt\.service'; then
        systemctl daemon-reload >>"$UPDATE_LOG" 2>&1 || true
        systemctl enable --now kyt >>"$UPDATE_LOG" 2>&1 || systemctl restart kyt >>"$UPDATE_LOG" 2>&1 || true
        KYT_RESTARTED=1
        report_service_status kyt
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
        log_info "Aset me-cli tidak berubah (dilewati)."
        return 0
    fi

    src_dir="$TMP_DIR/limit/me-cli-sunset-main"
    resolved_src="$(resolve_me_cli_source_dir "$src_dir" || true)"

    if [[ -z "$resolved_src" ]]; then
        upstream_dir="$TMP_DIR/mecli-upstream"
        rm -rf "$upstream_dir"
        if git clone --depth 1 "$MECLI_UPSTREAM_REPO_URL" "$upstream_dir" >>"$UPDATE_LOG" 2>&1; then
            resolved_src="$(resolve_me_cli_source_dir "$upstream_dir" || true)"
        fi
    fi

    if [[ -z "$resolved_src" ]]; then
        log_warn "Asset me-cli valid tidak ditemukan (source update/upstream), sinkronisasi dilewati."
        return 0
    fi

    mkdir -p "$MECLI_ASSET_DIR"
    find "$MECLI_ASSET_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf {} + 2>/dev/null || true
    cp -a "$resolved_src"/. "$MECLI_ASSET_DIR"/

    rm -rf "$MECLI_ASSET_DIR/.git" "$MECLI_ASSET_DIR/.venv" "$MECLI_ASSET_DIR/logs" "$MECLI_ASSET_DIR/run" "$MECLI_ASSET_DIR/__pycache__"
    find "$MECLI_ASSET_DIR" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
    find "$MECLI_ASSET_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    rm -f "$MECLI_ASSET_DIR/.env"
    log_ok "Asset me-cli disinkronkan ke ${MECLI_ASSET_DIR}."
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
        log_warn "Sinkronisasi runtime me-cli dilewati: installer $installer tidak ditemukan."
        return 0
    fi

    log_info "me-cli terpasang, menjalankan sinkronisasi runtime..."
    if timeout 180 "$installer" --sync-only --non-interactive >"$sync_log" 2>&1 </dev/null; then
        log_ok "Sinkronisasi runtime me-cli berhasil."
    else
        log_warn "Sinkronisasi runtime me-cli gagal. Lihat log: $sync_log"
        tail -n 10 "$sync_log" 2>/dev/null | sed 's/^/  /' || true
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
            (cd "$app_dir" && nohup "$venv_py" telegram_main.py >> "${app_dir}/logs/telegram_bot.log" 2>&1 </dev/null & echo $! > "$bot_pid_file")
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
            (cd "$app_dir" && nohup "$venv_py" main.py >> "${app_dir}/logs/cli.log" 2>&1 </dev/null & echo $! > "$cli_pid_file")
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

sync_laravel_webpanel() {
    local web_dir="/var/www/webpanel-mvc"
    local src_web="$TMP_DIR/limit/webpanel-mvc"
    local old_lock_hash="" new_lock_hash="" has_vendor_cache=0

    cd /tmp || true

    if [[ ! -d "$src_web" ]]; then
        log_info "Folder limit/webpanel-mvc tidak ditemukan di repository, dilewati."
        return 0
    fi

    log_step "[7/10] Sinkronisasi kode Laravel Web Panel (${web_dir})..."
    mkdir -p /var/www "$WEBPANEL_PRESERVE_DIR"

    [[ -f "$web_dir/.env" ]] && cp -a "$web_dir/.env" "$WEBPANEL_PRESERVE_DIR/.env"
    [[ -f "$web_dir/database/database.sqlite" ]] && cp -a "$web_dir/database/database.sqlite" "$WEBPANEL_PRESERVE_DIR/database.sqlite"
    [[ -d "$web_dir/storage/app" ]] && cp -a "$web_dir/storage/app" "$WEBPANEL_PRESERVE_DIR/storage_app" 2>/dev/null || true
    [[ -f "$web_dir/composer.lock" ]] && old_lock_hash="$(sha256sum "$web_dir/composer.lock" 2>/dev/null | awk '{print $1}' || true)"

    if [[ -d "$web_dir/vendor" && -f "$web_dir/vendor/autoload.php" ]]; then
        mv "$web_dir/vendor" "$WEBPANEL_PRESERVE_DIR/vendor"
        has_vendor_cache=1
    fi

    rm -rf "$web_dir"
    cp -a "$src_web" "$web_dir"

    [[ -f "$WEBPANEL_PRESERVE_DIR/.env" ]] && cp -a "$WEBPANEL_PRESERVE_DIR/.env" "$web_dir/.env"
    mkdir -p "$web_dir/database"
    if [[ -f "$WEBPANEL_PRESERVE_DIR/database.sqlite" ]]; then
        cp -a "$WEBPANEL_PRESERVE_DIR/database.sqlite" "$web_dir/database/database.sqlite"
    else
        touch "$web_dir/database/database.sqlite"
    fi
    if [[ -d "$WEBPANEL_PRESERVE_DIR/storage_app" ]]; then
        mkdir -p "$web_dir/storage"
        cp -a "$WEBPANEL_PRESERVE_DIR/storage_app/." "$web_dir/storage/app/" 2>/dev/null || true
    fi

    [[ -f "$web_dir/composer.lock" ]] && new_lock_hash="$(sha256sum "$web_dir/composer.lock" 2>/dev/null | awk '{print $1}' || true)"

    if [[ "$has_vendor_cache" -eq 1 && -d "$WEBPANEL_PRESERVE_DIR/vendor" ]]; then
        rm -rf "$web_dir/vendor"
        mv "$WEBPANEL_PRESERVE_DIR/vendor" "$web_dir/vendor"
    fi
    log_ok "Kode Laravel Web Panel berhasil disinkronkan."

    log_step "[8/10] Memperbarui dependensi Composer Laravel Web Panel..."
    if command -v composer >/dev/null 2>&1; then
        local composer_rc=0
        if [[ "$has_vendor_cache" -eq 1 && -n "$old_lock_hash" && "$old_lock_hash" == "$new_lock_hash" && -f "$web_dir/vendor/autoload.php" ]]; then
            log_info "composer.lock tidak berubah (${new_lock_hash:0:12}) — menjalankan dump-autoload cepat..."
            set +e
            (
                cd "$web_dir" && \
                COMPOSER_ALLOW_SUPERUSER=1 \
                COMPOSER_MEMORY_LIMIT=-1 \
                timeout 120 composer dump-autoload --optimize --no-dev --no-interaction </dev/null
            ) 2>&1 | while IFS= read -r line; do
                printf '  %s\n' "$line"
                printf '  %s\n' "$line" >> "$UPDATE_LOG" 2>/dev/null || true
            done
            composer_rc=${PIPESTATUS[0]}
            set -e
            COMPOSER_STATUS=$([[ "$composer_rc" -eq 0 ]] && echo "cached (dump-autoload ok)" || echo "dump-autoload warn (rc=${composer_rc})")
        else
            log_info "Menjalankan composer install (non-interaktif, timeout 300s)..."
            set +e
            (
                cd "$web_dir" && \
                COMPOSER_ALLOW_SUPERUSER=1 \
                COMPOSER_MEMORY_LIMIT=-1 \
                COMPOSER_PROCESS_TIMEOUT=300 \
                timeout 300 composer install --no-dev --optimize-autoloader --no-interaction --prefer-dist --no-progress </dev/null
            ) 2>&1 | while IFS= read -r line; do
                printf '  %s\n' "$line"
                printf '  %s\n' "$line" >> "$UPDATE_LOG" 2>/dev/null || true
            done
            composer_rc=${PIPESTATUS[0]}
            set -e
            if [[ "$composer_rc" -eq 0 ]]; then
                COMPOSER_STATUS="installed ok"
                log_ok "Composer install selesai."
            elif [[ "$composer_rc" -eq 124 ]]; then
                COMPOSER_STATUS="timeout (300s)"
                log_warn "Composer install timeout (300s). Melanjutkan tahap berikutnya..."
            else
                COMPOSER_STATUS="failed (rc=${composer_rc})"
                log_warn "Composer install gagal (exit=${composer_rc}). Lihat ${UPDATE_LOG}."
            fi
        fi
    else
        COMPOSER_STATUS="composer not installed"
        log_warn "Composer tidak ditemukan, dilewati."
    fi

    log_step "[9/10] Menjalankan migrasi database, cache clear, & izin file Laravel..."
    mkdir -p "$web_dir/storage/framework/views" "$web_dir/storage/framework/cache" "$web_dir/storage/framework/sessions" "$web_dir/storage/logs"
    chown -R www-data:www-data "$web_dir" 2>/dev/null || true
    chmod -R 775 "$web_dir/storage" "$web_dir/bootstrap/cache" 2>/dev/null || true

    if command -v php >/dev/null 2>&1; then
        local art_rc=0
        set +e
        (cd "$web_dir" && php artisan migrate --force </dev/null) 2>&1 | while IFS= read -r line; do
            printf '  %s\n' "$line"
            printf '  %s\n' "$line" >> "$UPDATE_LOG" 2>/dev/null || true
        done
        art_rc=${PIPESTATUS[0]}
        set -e
        MIGRATE_STATUS=$([[ "$art_rc" -eq 0 ]] && echo "ok" || echo "warn (rc=${art_rc})")
        run_logged "php artisan optimize:clear" bash -c "cd '$web_dir' && php artisan optimize:clear </dev/null" || true
        run_logged "php artisan view:clear" bash -c "cd '$web_dir' && php artisan view:clear </dev/null" || true
    fi

    chown -R www-data:www-data "$web_dir" 2>/dev/null || true
    chmod -R 775 "$web_dir/storage" "$web_dir/bootstrap/cache" 2>/dev/null || true
    [[ -f "$web_dir/database/database.sqlite" ]] && chmod 664 "$web_dir/database/database.sqlite" 2>/dev/null || true

    if systemctl list-unit-files 2>/dev/null | grep -q '^vpn-bridge\.service'; then
        systemctl restart vpn-bridge >>"$UPDATE_LOG" 2>&1 || true
        report_service_status vpn-bridge
    fi

    log_step "[10/10] Me-restart PHP-FPM & menyinkronkan Cron Job Laravel..."
    local php_fpm_service
    php_fpm_service="$(systemctl list-units --type=service --state=running 2>/dev/null | grep -oE 'php[0-9.]+-fpm\.service' | head -n 1 || true)"
    if [[ -n "$php_fpm_service" ]]; then
        systemctl restart "$php_fpm_service" >>"$UPDATE_LOG" 2>&1 || true
        report_service_status "${php_fpm_service%.service}"
    else
        local fpm_units fpm
        fpm_units="$(systemctl list-unit-files 2>/dev/null | grep -oE 'php[0-9.]+-fpm\.service' || true)"
        for fpm in $fpm_units; do
            systemctl restart "$fpm" >>"$UPDATE_LOG" 2>&1 || true
            report_service_status "${fpm%.service}"
        done
    fi

    local cron_file="/etc/cron.d/vpnxray-webpanel"
    echo "* * * * * root cd $web_dir && php artisan schedule:run >> /dev/null 2>&1" > "$cron_file"
    chmod 644 "$cron_file"
    systemctl restart cron >>"$UPDATE_LOG" 2>&1 || systemctl restart crond >>"$UPDATE_LOG" 2>&1 || true
    WEBPANEL_UPDATED=1
}

old_sha="unknown"
[[ -f "$STATE_FILE" ]] && old_sha="$(cat "$STATE_FILE" 2>/dev/null || echo unknown)"
new_sha="$(git -C "$TMP_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
log_info "Revisi lokal  : ${old_sha}"
log_info "Revisi remote : ${new_sha}"
detect_bot_asset_changes

log_step "[3/10] Menyalin script menu ke ${TARGET_SBIN}..."
mkdir -p "$TARGET_SBIN" /etc/kyt
cp -rf "$TMP_DIR/limit/menu/." "$TARGET_SBIN/"
chmod +x "$TARGET_SBIN"/* 2>/dev/null || true
log_ok "Menu binary di ${TARGET_SBIN} diperbarui."

log_step "[4/10] Sinkronisasi konfigurasi runtime..."
sync_runtime_configs

log_step "[5/10] Sinkronisasi aset & layanan Bot KYT..."
sync_kyt_bot_assets

log_step "[6/10] Sinkronisasi aset & runtime me-cli..."
sync_me_cli_assets
auto_refresh_me_cli_runtime
restart_me_cli_runtime_if_running

sync_laravel_webpanel
echo "$new_sha" > "$STATE_FILE"

ELAPSED_SEC=$(( $(date +%s) - START_TS ))
log_raw "==================== FINISH UPDATE (${old_sha} -> ${new_sha}, ${ELAPSED_SEC}s) ===================="

echo ""
echo -e "\033[1;36m==========================================================\033[0m"
echo -e "\033[0;32m                  UPDATE SELESAI (${ELAPSED_SEC} detik)                 \033[0m"
echo -e "\033[1;36m==========================================================\033[0m"
echo -e "Old revision : $old_sha"
echo -e "New revision : $new_sha"
echo -e "Target path  : $TARGET_SBIN"
echo -e "Runtime cfg  : nginx / haproxy / ws / dropbear / xray synced"
if [[ "$WEBPANEL_UPDATED" == "1" ]]; then
    echo -e "Web Panel    : /var/www/webpanel-mvc (composer: ${COMPOSER_STATUS}, migrate: ${MIGRATE_STATUS})"
fi
if [[ "$KYT_ASSETS_CHANGED" == "1" ]]; then
    echo -e "KYT sync     : /usr/bin/kyt + bot scripts disinkronkan"
    if [[ "$KYT_RESTARTED" == "1" ]]; then
        echo -e "KYT restart  : kyt.service di-restart"
    fi
fi
if [[ "$MECLI_ASSETS_CHANGED" == "1" ]]; then
    echo -e "ME-CLI sync  : asset me-cli disinkronkan"
    if [[ "$MECLI_BOT_RESTARTED" == "1" || "$MECLI_CLI_RESTARTED" == "1" ]]; then
        echo -e "ME-CLI daemon: proses aktif me-cli di-restart"
    fi
fi
echo -e "Log file     : $UPDATE_LOG"
echo -e "\033[1;36m==========================================================\033[0m"
