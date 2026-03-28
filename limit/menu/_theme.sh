#!/bin/bash

# PanelXray dashboard theme.
THM_NC='\033[0m'
THM_BORDER='\033[38;5;45m'
THM_TITLE='\033[1;97m'
THM_ACCENT='\033[1;96m'
THM_KEY='\033[1;93m'
THM_VAL='\033[1;37m'
THM_OK='\033[1;32m'
THM_BAD='\033[1;31m'
THM_MUTED='\033[38;5;250m'
THM_BADGE='\033[1;35m'

THM_WIDTH=58

thm_repeat() {
    local ch="$1"
    local n="$2"
    local out=""
    local i
    for ((i=0; i<n; i++)); do
        out+="$ch"
    done
    printf '%s' "$out"
}

thm_line() {
    local bar
    bar="$(thm_repeat '=' "$THM_WIDTH")"
    echo -e "${THM_BORDER}+${bar}+${THM_NC}"
}

thm_section() {
    local title="$1"
    thm_line
    printf "${THM_BORDER}|${THM_NC} ${THM_ACCENT}%-${THM_WIDTH}s${THM_NC} ${THM_BORDER}|${THM_NC}\n" ":: ${title}"
    thm_line
}

thm_title() {
    local title="$1"
    thm_line
    printf "${THM_BORDER}|${THM_NC} ${THM_TITLE}%-${THM_WIDTH}s${THM_NC} ${THM_BORDER}|${THM_NC}\n" "$title"
    thm_line
}

thm_welcome() {
    local user_name="${1:-User}"
    printf "${THM_BORDER}|${THM_NC} ${THM_MUTED}%-12s${THM_NC} : ${THM_VAL}%-${THM_WIDTH}s${THM_NC} ${THM_BORDER}|${THM_NC}\n" "Session" "$user_name"
    printf "${THM_BORDER}|${THM_NC} ${THM_MUTED}%-12s${THM_NC} : ${THM_VAL}%-${THM_WIDTH}s${THM_NC} ${THM_BORDER}|${THM_NC}\n" "Host Time" "$(date +'%Y-%m-%d %H:%M:%S')"
    thm_line
}

thm_info_row() {
    local key="$1"
    local val="$2"
    printf "${THM_BORDER}|${THM_NC} ${THM_KEY}%-16s${THM_NC} : ${THM_VAL}%-${THM_WIDTH}s${THM_NC} ${THM_BORDER}|${THM_NC}\n" "$key" "$val"
}

thm_status_row() {
    local key="$1"
    local val="$2"
    local color="$THM_BAD"
    if [[ "$val" == "ON" || "$val" == "ACTIVE" || "$val" == "RUNNING" ]]; then
        color="$THM_OK"
    fi
    printf "${THM_BORDER}|${THM_NC} ${THM_KEY}%-16s${THM_NC} : ${color}%-${THM_WIDTH}s${THM_NC} ${THM_BORDER}|${THM_NC}\n" "$key" "$val"
}

thm_menu_item() {
    local num="$1"
    local label="$2"
    printf " ${THM_BADGE}[%02d]${THM_NC} ${THM_VAL}%-54s${THM_NC}\n" "$num" "$label"
}

thm_prompt() {
    local hint="$1"
    echo -ne "${THM_ACCENT}${hint}${THM_NC}"
}

thm_footer() {
    thm_line
    printf "${THM_BORDER}|${THM_NC} ${THM_MUTED}PanelXray Service Menu${THM_NC}%-${THM_WIDTH}s${THM_BORDER}|${THM_NC}\n" ""
    printf "${THM_BORDER}|${THM_NC} ${THM_MUTED}Tip: pilih angka menu sesuai kebutuhan administrasi.${THM_NC}%-13s${THM_BORDER}|${THM_NC}\n" ""
    thm_line
}