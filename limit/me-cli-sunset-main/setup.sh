#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

create_venv_and_install() {
    local python_cmd="$1"
    if [ ! -d "$ROOT_DIR/.venv" ]; then
        "$python_cmd" -m venv "$ROOT_DIR/.venv"
    fi

    "$ROOT_DIR/.venv/bin/python" -m pip install --upgrade pip
    "$ROOT_DIR/.venv/bin/python" -m pip install -r "$ROOT_DIR/requirements.txt"
}

if command -v pkg >/dev/null 2>&1; then
	echo "Detected Termux environment"
	pkg update -y
	pkg install -y python python-pillow git
	create_venv_and_install python
elif command -v apt-get >/dev/null 2>&1; then
	echo "Detected Debian/Ubuntu environment"

	SUDO=""
	if [ "$(id -u)" -ne 0 ]; then
		if command -v sudo >/dev/null 2>&1; then
			SUDO="sudo"
		else
			echo "sudo is required when not running as root."
			exit 1
		fi
	fi

	$SUDO apt-get update
	$SUDO apt-get install -y python3 python3-pip python3-venv build-essential git curl
	create_venv_and_install python3

	chmod +x "$ROOT_DIR/panel.sh"

	if [ ! -f "$ROOT_DIR/user_allow.txt" ]; then
		cat > "$ROOT_DIR/user_allow.txt" << 'EOF'
# Daftar user id Telegram yang diizinkan mengakses bot.
# Satu id per baris, contoh:
# 123456789
EOF
	fi

	$SUDO tee /usr/local/bin/paneldor >/dev/null <<EOF
#!/usr/bin/env bash
cd "$ROOT_DIR"
exec bash "$ROOT_DIR/panel.sh"
EOF
	$SUDO chmod +x /usr/local/bin/paneldor

	echo "Setup selesai. Jalankan panel dengan command: paneldor"
else
	echo "Unsupported platform: expected Termux (pkg) or Debian/Ubuntu (apt-get)."
	exit 1
fi