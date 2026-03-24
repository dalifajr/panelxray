#!/bin/bash
set -euo pipefail

REPO_URL="https://github.com/dalifajr/panelxray.git"
REPO_API="https://api.github.com/repos/dalifajr/panelxray"
TARGET_SBIN="/usr/local/sbin"
STATE_FILE="/etc/kyt/panelxray-revision"
TMP_DIR="/tmp/panelxray-update.$$"
BRANCH="${PANELXRAY_BRANCH:-}"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

if [[ -z "$BRANCH" ]]; then
    BRANCH="$(curl -fsSL "$REPO_API" 2>/dev/null | awk -F '"' '/"default_branch"/ {print $4; exit}')"
    [[ -n "$BRANCH" ]] || BRANCH="main"
fi

clear
echo -e "\033[1;36m==========================================================\033[0m"
echo -e "\033[1;33m                 UPDATE PROGRAM (GITHUB)                  \033[0m"
echo -e "\033[1;36m==========================================================\033[0m"
echo -e "Branch target : $BRANCH"

if ! command -v git >/dev/null 2>&1; then
    echo -e "\033[1;31mGit tidak ditemukan. Install git terlebih dahulu.\033[0m"
    exit 1
fi

mkdir -p "$TMP_DIR"
if ! git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP_DIR" >/dev/null 2>&1; then
    echo -e "\033[1;31mGagal clone branch $BRANCH dari repository.\033[0m"
    exit 1
fi

if [[ ! -d "$TMP_DIR/limit/menu" ]]; then
    echo -e "\033[1;31mStruktur repository tidak valid: limit/menu tidak ditemukan.\033[0m"
    exit 1
fi

old_sha="unknown"
[[ -f "$STATE_FILE" ]] && old_sha="$(cat "$STATE_FILE" 2>/dev/null || echo unknown)"
new_sha="$(git -C "$TMP_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"

mkdir -p "$TARGET_SBIN" /etc/kyt
cp -rf "$TMP_DIR/limit/menu/." "$TARGET_SBIN/"
chmod +x "$TARGET_SBIN"/* 2>/dev/null || true
echo "$new_sha" > "$STATE_FILE"

echo -e "\033[0;32mUpdate selesai.\033[0m"
echo -e "Old revision : $old_sha"
echo -e "New revision : $new_sha"
echo -e "Target path  : $TARGET_SBIN"
