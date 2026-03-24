#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${SCRIPT_DIR}/scripts/install/premi.sh"

if [ -f "${TARGET}" ]; then
	exec bash "${TARGET}" "$@"
fi

FALLBACK_URL="https://raw.githubusercontent.com/dalifajr/vpnxray/main/scripts/install/premi.sh"
TMP_SCRIPT="/tmp/premi-install.sh"

if command -v curl >/dev/null 2>&1; then
	curl -fsSL "${FALLBACK_URL}" -o "${TMP_SCRIPT}"
else
	wget -qO "${TMP_SCRIPT}" "${FALLBACK_URL}"
fi

chmod +x "${TMP_SCRIPT}"
exec bash "${TMP_SCRIPT}" "$@"
