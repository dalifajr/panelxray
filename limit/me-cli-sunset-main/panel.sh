#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PY="$ROOT_DIR/.venv/bin/python"
RUN_DIR="$ROOT_DIR/run"
LOG_DIR="$ROOT_DIR/logs"
BOT_PID="$RUN_DIR/telegram_bot.pid"
CLI_PID="$RUN_DIR/cli.pid"
BOT_LOG="$LOG_DIR/telegram_bot.log"
CLI_LOG="$LOG_DIR/cli.log"
KYT_VAR_FILE="/usr/bin/kyt/var.txt"

mkdir -p "$RUN_DIR" "$LOG_DIR"

ensure_venv_python() {
  if [[ ! -x "$VENV_PY" ]]; then
    echo "Virtual environment belum siap. Jalankan: bash setup.sh"
    exit 1
  fi
}

read_kv() {
  local file="$1"
  local key="$2"
  local line
  local value

  [[ -f "$file" ]] || return 0
  line="$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "$file" | tail -n 1 || true)"
  [[ -n "$line" ]] || return 0

  value="${line#*=}"
  value="$(printf '%s' "$value" | tr -d '\r')"
  value="$(printf '%s' "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  value="${value%\"}"
  value="${value#\"}"
  value="${value%\'}"
  value="${value#\'}"
  printf '%s' "$value"
}

ensure_non_conflicting_bot_token() {
  local me_token
  local kyt_token

  me_token="$(read_kv "$ROOT_DIR/.env" "TELEGRAM_BOT_TOKEN" || true)"
  kyt_token="$(read_kv "$KYT_VAR_FILE" "BOT_TOKEN" || true)"

  if [[ -z "$me_token" || "$me_token" == "your_bot_token_here" ]]; then
    echo "TELEGRAM_BOT_TOKEN belum valid di $ROOT_DIR/.env"
    return 1
  fi

  if [[ -n "$kyt_token" && "$me_token" == "$kyt_token" ]]; then
    echo "Token Telegram me-cli sama dengan token bot panel vpnxray (kyt)."
    echo "Ganti TELEGRAM_BOT_TOKEN di $ROOT_DIR/.env agar dua bot tidak bentrok."
    return 1
  fi

  return 0
}

is_running_pid() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if [[ -n "$pid" ]] && kill -0 "$pid" >/dev/null 2>&1; then
      return 0
    fi
  fi
  return 1
}

start_bot() {
  ensure_venv_python
  if ! ensure_non_conflicting_bot_token; then
    return
  fi
  if is_running_pid "$BOT_PID"; then
    echo "Bot sudah berjalan (PID: $(cat "$BOT_PID"))"
    return
  fi
  (cd "$ROOT_DIR" && nohup "$VENV_PY" telegram_main.py >> "$BOT_LOG" 2>&1 & echo $! > "$BOT_PID")
  echo "Bot started. PID: $(cat "$BOT_PID")"
}

stop_bot() {
  if is_running_pid "$BOT_PID"; then
    kill "$(cat "$BOT_PID")" || true
    rm -f "$BOT_PID"
    echo "Bot stopped."
  else
    echo "Bot tidak berjalan."
  fi
}

start_cli() {
  ensure_venv_python
  if is_running_pid "$CLI_PID"; then
    echo "CLI sudah berjalan (PID: $(cat "$CLI_PID"))"
    return
  fi
  (cd "$ROOT_DIR" && nohup "$VENV_PY" main.py >> "$CLI_LOG" 2>&1 & echo $! > "$CLI_PID")
  echo "CLI started. PID: $(cat "$CLI_PID")"
}

stop_cli() {
  if is_running_pid "$CLI_PID"; then
    kill "$(cat "$CLI_PID")" || true
    rm -f "$CLI_PID"
    echo "CLI stopped."
  else
    echo "CLI tidak berjalan."
  fi
}

status_all() {
  if is_running_pid "$BOT_PID"; then
    echo "Bot   : RUNNING (PID: $(cat "$BOT_PID"))"
  else
    echo "Bot   : STOPPED"
  fi

  if is_running_pid "$CLI_PID"; then
    echo "CLI   : RUNNING (PID: $(cat "$CLI_PID"))"
  else
    echo "CLI   : STOPPED"
  fi
}

show_menu() {
  clear
  echo "==============================="
  echo "  Panel Control - paneldor"
  echo "==============================="
  echo "1) Start Telegram Bot"
  echo "2) Stop Telegram Bot"
  echo "3) Start CLI Background"
  echo "4) Stop CLI Background"
  echo "5) Status"
  echo "6) Tail Bot Log"
  echo "7) Tail CLI Log"
  echo "8) Update Dependencies"
  echo "0) Exit"
  echo "-------------------------------"
}

while true; do
  show_menu
  read -rp "Pilih menu: " choice
  case "$choice" in
    1) start_bot ;;
    2) stop_bot ;;
    3) start_cli ;;
    4) stop_cli ;;
    5) status_all ;;
    6) tail -n 80 "$BOT_LOG" || true ;;
    7) tail -n 80 "$CLI_LOG" || true ;;
    8)
      ensure_venv_python
      "$VENV_PY" -m pip install --upgrade pip
      "$VENV_PY" -m pip install -r "$ROOT_DIR/requirements.txt"
      ;;
    0) exit 0 ;;
    *) echo "Pilihan tidak valid." ;;
  esac
  echo
  read -rp "Tekan Enter untuk lanjut..." _
done
