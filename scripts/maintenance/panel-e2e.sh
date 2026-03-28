#!/bin/bash
set -euo pipefail

APP_ROOT="/opt/vpnxray-web-panel"
PANEL_ETC_DIR="/etc/vpnxray-web-panel"
XRAY_CONFIG="/etc/xray/config.json"
BACKUP_DIR="/etc/xray/backup-web-panel"

DOMAIN="$(cat /etc/xray/domain 2>/dev/null || echo 127.0.0.1)"
BASE_URL="${BASE_URL:-https://${DOMAIN}/panel}"
FALLBACK_URL="${FALLBACK_URL:-http://127.0.0.1:9999/panel}"
PROTOCOL="${PROTOCOL:-vmess}"
CREATE_DAYS="${CREATE_DAYS:-3}"
UPDATE_DAYS="${UPDATE_DAYS:-7}"
TEST_USER="${TEST_USER:-e2e_${PROTOCOL}_$(date +%s)}"

COOKIE_FILE="$(mktemp /tmp/panel-e2e-cookie.XXXXXX)"
CURL_OPTS=(-ksS --connect-timeout 15 --max-time 30)

log() {
  echo "[INFO] $1"
}

ok() {
  echo "[OK] $1"
}

warn() {
  echo "[WARN] $1"
}

fail() {
  echo "[FAIL] $1" >&2
  exit 1
}

cleanup_test_user() {
  if [[ -x "${APP_ROOT}/.venv/bin/python" ]]; then
    TEST_USER_ENV="${TEST_USER}" TEST_PROTOCOL_ENV="${PROTOCOL}" "${APP_ROOT}/.venv/bin/python" - <<'PY' >/dev/null 2>&1 || true
import os
import sys

sys.path.insert(0, "/opt/vpnxray-web-panel")

try:
    from models import account_model
except Exception:
    raise SystemExit(0)

username = os.environ.get("TEST_USER_ENV", "")
protocol = os.environ.get("TEST_PROTOCOL_ENV", "")
if not username or not protocol:
    raise SystemExit(0)

try:
    account_model.delete_account(protocol, username)
except Exception:
    pass
PY
  fi

  rm -f "${COOKIE_FILE}"
}

trap cleanup_test_user EXIT

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    fail "Jalankan skrip sebagai root."
  fi
}

require_panel_files() {
  [[ -f "${XRAY_CONFIG}" ]] || fail "File config Xray tidak ditemukan: ${XRAY_CONFIG}"
  [[ -x "${APP_ROOT}/.venv/bin/python" ]] || fail "Python venv panel tidak ditemukan di ${APP_ROOT}/.venv"
  [[ -f "${PANEL_ETC_DIR}/admin_user" ]] || fail "File admin_user tidak ditemukan di ${PANEL_ETC_DIR}"
  [[ -f "${PANEL_ETC_DIR}/admin_password" ]] || fail "File admin_password tidak ditemukan di ${PANEL_ETC_DIR}"
}

resolve_protocol_meta() {
  case "${PROTOCOL}" in
    vmess)
      XRAY_MARKER="###"
      SIDECAR_DB="/etc/vmess/.vmess.db"
      ;;
    vless)
      XRAY_MARKER="#&"
      SIDECAR_DB="/etc/vless/.vless.db"
      ;;
    trojan)
      XRAY_MARKER="#!"
      SIDECAR_DB="/etc/trojan/.trojan.db"
      ;;
    shadowsocks)
      XRAY_MARKER="#!#"
      SIDECAR_DB="/etc/shadowsocks/.shadowsocks.db"
      ;;
    *)
      fail "Protocol tidak didukung: ${PROTOCOL}"
      ;;
  esac
}

latest_backup_file() {
  ls -1t "${BACKUP_DIR}"/config.json.*.bak 2>/dev/null | head -n1 || true
}

expect_new_backup() {
  local before="$1"
  local label="$2"
  local after
  after="$(latest_backup_file)"
  [[ -n "${after}" ]] || fail "Tidak ada file backup setelah ${label}."
  [[ "${after}" != "${before}" ]] || fail "Backup baru tidak terdeteksi setelah ${label}."
  echo "${after}"
}

detect_panel_url() {
  if curl "${CURL_OPTS[@]}" -o /dev/null "${BASE_URL}/login"; then
    PANEL_URL="${BASE_URL}"
    return
  fi

  if curl "${CURL_OPTS[@]}" -o /dev/null "${FALLBACK_URL}/login"; then
    PANEL_URL="${FALLBACK_URL}"
    return
  fi

  fail "Panel tidak bisa diakses di ${BASE_URL} maupun ${FALLBACK_URL}."
}

login_panel() {
  local admin_user admin_pass status page
  admin_user="$(cat "${PANEL_ETC_DIR}/admin_user" | tr -d '[:space:]')"
  admin_pass="$(cat "${PANEL_ETC_DIR}/admin_password" | tr -d '[:space:]')"

  status="$(curl "${CURL_OPTS[@]}" -o /dev/null -w "%{http_code}" -c "${COOKIE_FILE}" -b "${COOKIE_FILE}" \
    --data-urlencode "username=${admin_user}" \
    --data-urlencode "password=${admin_pass}" \
    -X POST "${PANEL_URL}/login")"

  if [[ "${status}" != "302" && "${status}" != "303" && "${status}" != "200" ]]; then
    fail "Login panel gagal, HTTP ${status}."
  fi

  page="$(curl "${CURL_OPTS[@]}" -c "${COOKIE_FILE}" -b "${COOKIE_FILE}" "${PANEL_URL}/")"
  echo "${page}" | grep -qi "Dashboard" || fail "Session login tidak valid (halaman dashboard tidak terbaca)."
}

post_with_session() {
  local path="$1"
  shift
  curl "${CURL_OPTS[@]}" -o /dev/null -w "%{http_code}" -c "${COOKIE_FILE}" -b "${COOKIE_FILE}" -X POST "${PANEL_URL}${path}" "$@"
}

verify_config_has_user() {
  grep -Eq "^${XRAY_MARKER} ${TEST_USER} " "${XRAY_CONFIG}" || fail "User ${TEST_USER} tidak ditemukan di ${XRAY_CONFIG}."
}

verify_config_no_user() {
  if grep -Eq "^${XRAY_MARKER} ${TEST_USER} " "${XRAY_CONFIG}"; then
    fail "User ${TEST_USER} masih ada di ${XRAY_CONFIG}."
  fi
}

verify_sidecar_has_user() {
  [[ -f "${SIDECAR_DB}" ]] || fail "File sidecar tidak ditemukan: ${SIDECAR_DB}"
  grep -Eq "[[:space:]]${TEST_USER}[[:space:]]" "${SIDECAR_DB}" || fail "User ${TEST_USER} tidak ditemukan di ${SIDECAR_DB}."
}

verify_sidecar_no_user() {
  if [[ -f "${SIDECAR_DB}" ]] && grep -Eq "[[:space:]]${TEST_USER}[[:space:]]" "${SIDECAR_DB}"; then
    fail "User ${TEST_USER} masih ada di ${SIDECAR_DB}."
  fi
}

simulate_rollback_test() {
  local output
  output="$("${APP_ROOT}/.venv/bin/python" - <<'PY'
import hashlib
import sys
import time

sys.path.insert(0, "/opt/vpnxray-web-panel")
from models import account_model

config_path = account_model.XRAY_CONFIG_PATH
before_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()
original_restart = account_model._restart_xray
account_model._restart_xray = lambda: False

username = f"rollback_{int(time.time())}"
raised = False
try:
    account_model.create_account("vmess", username, 1)
except Exception:
    raised = True
finally:
    account_model._restart_xray = original_restart

after_hash = hashlib.sha256(config_path.read_bytes()).hexdigest()
if raised and before_hash == after_hash:
    print("ROLLBACK_OK")
else:
    print("ROLLBACK_FAIL")
PY
)"

  [[ "${output}" == *"ROLLBACK_OK"* ]] || fail "Rollback simulation gagal: ${output}"
}

main() {
  require_root
  require_panel_files
  resolve_protocol_meta

  detect_panel_url
  log "Panel target: ${PANEL_URL}"
  log "Protocol test: ${PROTOCOL}"
  log "Test user: ${TEST_USER}"

  login_panel
  ok "Login panel berhasil."

  local backup_cursor
  backup_cursor="$(latest_backup_file)"

  local status
  status="$(post_with_session "/accounts/create" \
    --data-urlencode "protocol=${PROTOCOL}" \
    --data-urlencode "username=${TEST_USER}" \
    --data-urlencode "expiry_days=${CREATE_DAYS}")"
  [[ "${status}" == "302" || "${status}" == "303" || "${status}" == "200" ]] || fail "Create account gagal, HTTP ${status}."
  verify_config_has_user
  verify_sidecar_has_user
  backup_cursor="$(expect_new_backup "${backup_cursor}" "create")"
  ok "Create account + backup + sidecar sync sukses."

  local expiry_before expiry_after expiry_sidecar
  expiry_before="$(grep -E "^${XRAY_MARKER} ${TEST_USER} " "${XRAY_CONFIG}" | head -n1 | awk '{print $3}')"
  [[ -n "${expiry_before}" ]] || fail "Gagal membaca expiry awal user ${TEST_USER}."

  status="$(post_with_session "/accounts/${PROTOCOL}/${TEST_USER}/update" \
    --data-urlencode "expiry_days=${UPDATE_DAYS}")"
  [[ "${status}" == "302" || "${status}" == "303" || "${status}" == "200" ]] || fail "Update account gagal, HTTP ${status}."

  expiry_after="$(grep -E "^${XRAY_MARKER} ${TEST_USER} " "${XRAY_CONFIG}" | head -n1 | awk '{print $3}')"
  [[ -n "${expiry_after}" ]] || fail "Gagal membaca expiry setelah update user ${TEST_USER}."
  [[ "${expiry_after}" != "${expiry_before}" ]] || fail "Expiry tidak berubah setelah update."

  expiry_sidecar="$(awk -v user="${TEST_USER}" '$2==user {print $3; exit}' "${SIDECAR_DB}")"
  [[ "${expiry_sidecar}" == "${expiry_after}" ]] || fail "Expiry sidecar (${expiry_sidecar}) tidak sinkron dengan xray (${expiry_after})."
  backup_cursor="$(expect_new_backup "${backup_cursor}" "update")"
  ok "Update account + backup + sidecar sync sukses."

  simulate_rollback_test
  ok "Simulasi rollback sukses (config kembali ke hash semula saat restart gagal)."

  status="$(post_with_session "/accounts/${PROTOCOL}/${TEST_USER}/delete")"
  [[ "${status}" == "302" || "${status}" == "303" || "${status}" == "200" ]] || fail "Delete account gagal, HTTP ${status}."
  verify_config_no_user
  verify_sidecar_no_user
  backup_cursor="$(expect_new_backup "${backup_cursor}" "delete")"
  ok "Delete account + backup + sidecar sync sukses."

  ok "SEMUA UJI E2E LULUS."
}

main "$@"
