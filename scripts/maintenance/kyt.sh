#!/bin/bash
NS="$(cat /etc/xray/dns 2>/dev/null || true)"
PUB="$(cat /etc/slowdns/server.pub 2>/dev/null || true)"
domain="$(cat /etc/xray/domain 2>/dev/null || hostname -f 2>/dev/null || hostname 2>/dev/null || echo localhost)"
#color

cd /etc/systemd/system/
rm -rf kyt.service
cd
grenbo="\e[92;1m"
NC='\e[0m'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ASSET_ROOT="${REPO_ROOT}/limit"
OLD_VAR_FILE="/usr/bin/kyt/var.txt"

trim_text() {
	local value="$1"
	value="${value//$'\r'/}"
	value="${value#\"${value%%[![:space:]]*}\"}"
	value="${value%\"${value##*[![:space:]]}\"}"
	printf '%s' "$value"
}

extract_var_value() {
	local key="$1" file="$2" value
	[ -f "$file" ] || return 0
	value="$(sed -n "s/^${key}=//p" "$file" | head -n 1)"
	value="$(trim_text "$value")"
	if [[ "$value" == \'*\' && "${#value}" -ge 2 ]]; then
		value="${value:1:${#value}-2}"
	fi
	if [[ "$value" == \"*\" && "${#value}" -ge 2 ]]; then
		value="${value:1:${#value}-2}"
	fi
	printf '%s' "$(trim_text "$value")"
}

prompt_or_default() {
	local prompt_text="$1" default_value="$2" out_var="$3" value=""
	if [ -t 0 ]; then
		if [ -n "$default_value" ]; then
			read -e -i "$default_value" -p "$prompt_text" value
		else
			read -e -p "$prompt_text" value
		fi
	else
		value="$default_value"
	fi
	printf -v "$out_var" '%s' "$(trim_text "$value")"
}

is_valid_bot_token() {
	local token="$1"
	[[ "$token" =~ ^[0-9]{6,}:[A-Za-z0-9_-]{20,}$ ]]
}

is_valid_admin_id() {
	local admin_id="$1"
	[[ "$admin_id" =~ ^-?[0-9]+$ ]]
}

sanitize_apt_sources() {
	rm -f /etc/apt/sources.list.d/vbernat-ubuntu-haproxy-2_0-*.list
	rm -f /etc/apt/sources.list.d/vbernat-ubuntu-haproxy-2_0-*.sources
}

safe_apt_update() {
	local tmplog bad_url log_file
	log_file="/var/log/kyt-apt-sanitize.log"
	tmplog="/tmp/apt-update-kyt.$$"

	touch "$log_file" 2>/dev/null || true
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] kyt.sh: apt update start" >> "$log_file"

	if apt-get update -y; then
		echo "[$(date '+%Y-%m-%d %H:%M:%S')] kyt.sh: apt update success without sanitize" >> "$log_file"
		return 0
	fi

	apt-get update -y 2>&1 | tee "$tmplog" >/dev/null || true
	while IFS= read -r bad_url; do
		[[ -z "$bad_url" ]] && continue
		grep -Rsl "$bad_url" /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null | while IFS= read -r src_file; do
			if [[ "$src_file" == *.sources ]]; then
				rm -f "$src_file"
				echo "[$(date '+%Y-%m-%d %H:%M:%S')] kyt.sh: removed invalid deb822 source $src_file for $bad_url" >> "$log_file"
			else
				sed -i "\|$bad_url| s|^deb |# disabled-invalid-repo deb |" "$src_file"
				sed -i "\|$bad_url| s|^deb-src |# disabled-invalid-repo deb-src |" "$src_file"
				echo "[$(date '+%Y-%m-%d %H:%M:%S')] kyt.sh: disabled repo $bad_url in $src_file" >> "$log_file"
			fi
		done
	done < <(grep -Eo 'https?://[^ ]+' "$tmplog" | sed 's#/dists/.*##; s#/InRelease##; s#/Release##' | sort -u)

	rm -f "$tmplog"
	if apt-get update -y; then
		echo "[$(date '+%Y-%m-%d %H:%M:%S')] kyt.sh: apt update success after sanitize" >> "$log_file"
		return 0
	fi

	echo "[$(date '+%Y-%m-%d %H:%M:%S')] kyt.sh: apt update failed after sanitize" >> "$log_file"
	return 1
}

if [ ! -d "${ASSET_ROOT}/bot" ] || [ ! -d "${ASSET_ROOT}/kyt" ]; then
	TMP_ASSET="/tmp/panelxray-assets"
	rm -rf "${TMP_ASSET}"
	git clone --depth 1 https://github.com/dalifajr/panelxray.git "${TMP_ASSET}" >/dev/null 2>&1 || {
		echo "Gagal mengambil source bot/kyt"
		exit 1
	}
	ASSET_ROOT="${TMP_ASSET}/limit"
fi

EXISTING_BOT_TOKEN="$(extract_var_value "BOT_TOKEN" "$OLD_VAR_FILE")"
EXISTING_ADMIN_ID="$(extract_var_value "ADMIN" "$OLD_VAR_FILE")"

#install
cd /usr/bin
rm -rf kyt
rm -rf bot
sanitize_apt_sources
safe_apt_update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git
mkdir -p /usr/bin/kyt
cp -rf "${ASSET_ROOT}/bot/." /usr/bin/
cp -rf "${ASSET_ROOT}/kyt/." /usr/bin/kyt/
chmod +x /usr/bin/bot-* 2>/dev/null
clear

VENV_DIR="/usr/bin/kyt/.venv"
python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --upgrade pip >/dev/null 2>&1 || true
if ! "${VENV_DIR}/bin/pip" install -r /usr/bin/kyt/requirements.txt; then
	echo "Gagal install dependency bot (requirements)."
	echo "Periksa koneksi server lalu jalankan ulang add-bot-panel."
	exit 1
fi

# Python 3.13 removed imghdr from stdlib; Telethon still imports it.
if ! "${VENV_DIR}/bin/python" -c "import imghdr" >/dev/null 2>&1; then
  SITE_PKG="$("${VENV_DIR}/bin/python" -c 'import site; print(next((p for p in site.getsitepackages() if p.endswith("site-packages")), ""))' 2>/dev/null || true)"
  if [[ -n "${SITE_PKG}" ]]; then
	cat > "${SITE_PKG}/imghdr.py" <<'PY'
"""Compatibility shim for Python 3.13+ where stdlib imghdr was removed."""

from pathlib import Path


def what(file, h=None):
	if h is None:
		if file is None:
			return None
		p = Path(file)
		if not p.exists():
			return None
		with p.open("rb") as f:
			h = f.read(32)
	if isinstance(h, str):
		h = h.encode("latin1", "ignore")

	if h.startswith(b"\xFF\xD8\xFF"):
		return "jpeg"
	if h.startswith(b"\x89PNG\r\n\x1a\n"):
		return "png"
	if h[:6] in (b"GIF87a", b"GIF89a"):
		return "gif"
	if h.startswith(b"RIFF") and h[8:12] == b"WEBP":
		return "webp"
	if h.startswith(b"BM"):
		return "bmp"
	if h[:4] in (b"II*\x00", b"MM\x00*"):
		return "tiff"

	return None
PY
  fi
fi

if ! "${VENV_DIR}/bin/python" -m py_compile /usr/bin/kyt/__init__.py /usr/bin/kyt/__main__.py /usr/bin/kyt/modules/*.py 2>/tmp/kyt-pycompile.log; then
	echo "Gagal validasi syntax modul bot."
	cat /tmp/kyt-pycompile.log
	rm -f /tmp/kyt-pycompile.log
	exit 1
fi
rm -f /tmp/kyt-pycompile.log

#isi data
echo ""
echo -e "\033[1;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e " \e[1;97;101m          ADD BOT PANEL          \e[0m"
echo -e "\033[1;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "${grenbo}Tutorial Creat Bot and ID Telegram${NC}"
echo -e "${grenbo}[*] Creat Bot and Token Bot : @BotFather${NC}"
echo -e "${grenbo}[*] Info Id Telegram : @MissRose_bot , perintah /info${NC}"
echo -e "\033[1;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"

bottoken="$(trim_text "${PANEL_BOT_TOKEN:-${BOT_TOKEN:-$EXISTING_BOT_TOKEN}}")"
admin="$(trim_text "${PANEL_BOT_ADMIN_ID:-${ADMIN:-$EXISTING_ADMIN_ID}}")"

prompt_or_default "[*] Input your Bot Token : " "$bottoken" bottoken
prompt_or_default "[*] Input Your Id Telegram :" "$admin" admin

if [ -z "$bottoken" ]; then
	echo "BOT_TOKEN kosong. Instalasi bot dibatalkan."
	echo "Tips: export PANEL_BOT_TOKEN='123456:ABC...' sebelum jalankan script untuk mode non-interaktif."
	exit 1
fi

if [ -z "$admin" ]; then
	echo "ADMIN Telegram ID kosong. Instalasi bot dibatalkan."
	echo "Tips: export PANEL_BOT_ADMIN_ID='123456789' sebelum jalankan script untuk mode non-interaktif."
	exit 1
fi

if ! is_valid_bot_token "$bottoken"; then
	echo "Format BOT_TOKEN tidak valid: $bottoken"
	echo "Gunakan token resmi dari @BotFather, format: <angka>:<string>."
	exit 1
fi

if ! is_valid_admin_id "$admin"; then
	echo "ADMIN Telegram ID harus berupa angka. Nilai saat ini: $admin"
	echo "Ambil ID numerik Telegram dari bot @MissRose_bot perintah /info."
	exit 1
fi

cat > /usr/bin/kyt/var.txt <<EOF
BOT_TOKEN='${bottoken}'
ADMIN='${admin}'
DOMAIN='${domain}'
PUB='${PUB}'
HOST='${NS}'
API_ID='6'
API_HASH='eb06d4abfb49dc3eeb1aeb98ae0f581e'
EOF
clear

cat > /etc/systemd/system/kyt.service << END
[Unit]
Description=Simple kyt - @kyt
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/usr/bin
Environment=PYTHONPATH=/usr/bin
ExecStart=${VENV_DIR}/bin/python -m kyt
ExecStartPre=/usr/bin/test -s /usr/bin/kyt/var.txt
ExecStartPre=${VENV_DIR}/bin/python -c 'import requests, telethon'
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
StandardOutput=append:/var/log/kyt.log
StandardError=append:/var/log/kyt.log

[Install]
WantedBy=multi-user.target
END

systemctl daemon-reload
systemctl enable kyt
systemctl reset-failed kyt >/dev/null 2>&1 || true
systemctl restart kyt
rm -rf /tmp/panelxray-assets
cd /root
rm -rf kyt.sh
echo "Done"
echo "Your Data Bot"
echo -e "==============================="
echo "Token Bot         : $bottoken"
echo "Admin          : $admin"
echo "Domain        : $domain"
echo "Pub            : $PUB"
echo "Host           : $NS"
echo -e "==============================="
echo "Setting done"

if systemctl is-active --quiet kyt; then
	echo "Status bot     : ACTIVE"
else
	echo "Status bot     : FAILED"
	echo "Log terakhir kyt:"
	journalctl -u kyt -n 40 --no-pager || true
	echo "Hint: cek /usr/bin/kyt/var.txt dan token bot dari @BotFather."
fi
clear

echo " Installations complete, type /menu on your bot"
