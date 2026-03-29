#!/bin/bash
set -euo pipefail

DOMAIN_FILE="/etc/xray/domain"
APP_SERVICE="vpnxray-webpanel.service"
PANEL_PATH="/panel/"
CRITICAL_SERVICES=(xray nginx haproxy ws ssh dropbear)

log() {
  echo "[E2E] $*"
}

die() {
  echo "[E2E][ERROR] $*" >&2
  exit 1
}

require_root() {
  [[ "${EUID}" -eq 0 ]] || die "Jalankan sebagai root"
}

check_service_active() {
  local service="$1"
  if systemctl is-active --quiet "$service"; then
    log "service $service: active"
  else
    die "service $service tidak active"
  fi
}

check_panel_route() {
  local domain
  domain="$(cat "$DOMAIN_FILE" 2>/dev/null || hostname -f 2>/dev/null || echo localhost)"

  curl -kfsS "https://127.0.0.1${PANEL_PATH}login" -H "Host: ${domain}" >/dev/null || \
    die "akses panel via reverse proxy gagal"
  log "akses panel via https://<domain>${PANEL_PATH}login: OK"
}

check_panel_api_health() {
  curl -fsS "http://127.0.0.1:3000/api/health" >/dev/null || \
    die "health API internal panel gagal"
  log "health API internal panel: OK"
}

run_install() {
  command -v install-panel-mvc >/dev/null 2>&1 || die "install-panel-mvc tidak ditemukan"
  log "menjalankan install-panel-mvc"
  install-panel-mvc
}

validate_non_regression() {
  for service in "${CRITICAL_SERVICES[@]}"; do
    check_service_active "$service"
  done
}

main() {
  require_root
  run_install
  check_service_active "$APP_SERVICE"
  check_panel_api_health
  check_panel_route
  validate_non_regression
  log "SEMUA UJI E2E STAGING LULUS"
}

main "$@"
