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
  local curl_modes
  panel_base_url="https://${domain}/panel"
  panel_url="https://${domain}${PANEL_PATH}login"

  curl_modes=("--http1.1")
  if curl --version 2>/dev/null | grep -qi "http2"; then
    curl_modes=("--http2" "--http1.1")
  fi

  local mode
  for mode in "${curl_modes[@]}"; do
    local mode_name
    mode_name="${mode#--}"

    local base_code
    base_code="$(curl -ksS "${mode}" -o /dev/null -w "%{http_code}" --resolve "${domain}:443:127.0.0.1" "${panel_base_url}" || true)"
    case "$base_code" in
      301|302|307|308)
        log "akses panel via https://<domain>/panel (${mode_name}): redirect (${base_code})"
        ;;
      *)
        die "akses /panel tidak redirect pada ${mode_name} (HTTP ${base_code:-000})"
        ;;
    esac

    if ! curl -kfsS "${mode}" --resolve "${domain}:443:127.0.0.1" "${panel_url}" >/dev/null; then
      local http_code
      http_code="$(curl -ksS "${mode}" -o /dev/null -w "%{http_code}" --resolve "${domain}:443:127.0.0.1" "${panel_url}" || true)"
      die "akses panel via reverse proxy gagal pada ${mode_name} (HTTP ${http_code:-000})"
    fi
    log "akses panel via https://<domain>${PANEL_PATH}login (${mode_name}): OK"
  done
}

check_panel_api_health() {
  local health_json
  health_json="$(curl -fsS "http://127.0.0.1:3000/api/health")" || \
    die "health API internal panel gagal"

  echo "$health_json" | grep -q '"asset_version"' || \
    die "health API belum memuat asset_version (indikasi build lama masih aktif)"

  log "health API internal panel: OK (asset_version terdeteksi)"
}

run_install() {
  command -v install-panel-mvc >/dev/null 2>&1 || die "install-panel-mvc tidak ditemukan"
  log "menjalankan install-panel-mvc"
  install-panel-mvc --non-interactive
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
