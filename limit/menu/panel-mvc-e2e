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
  domain="$(echo "$domain" | tr -d '[:space:]')"
  [[ -n "$domain" ]] || domain="localhost"

  local panel_base_url
  local panel_url
  panel_base_url="https://${domain}/panel"
  panel_url="https://${domain}${PANEL_PATH}login"

  local base_code
  base_code="$(curl -ksS -o /dev/null -w "%{http_code}" --resolve "${domain}:443:127.0.0.1" "${panel_base_url}" || true)"
  case "$base_code" in
    301|302|307|308)
      log "akses panel via https://<domain>/panel: redirect (${base_code})"
      ;;
    *)
      die "akses /panel tidak redirect (HTTP ${base_code:-000})"
      ;;
  esac

  if ! curl -kfsS --resolve "${domain}:443:127.0.0.1" "${panel_url}" >/dev/null; then
    local http_code
    http_code="$(curl -ksS -o /dev/null -w "%{http_code}" --resolve "${domain}:443:127.0.0.1" "${panel_url}" || true)"
    die "akses panel via reverse proxy gagal (HTTP ${http_code:-000})"
  fi
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
