#!/bin/bash

# PanelXray dashboard theme.
THM_NC='\033[0m'
THM_BORDER='\033[1;36m'
THM_TITLE='\033[1;97m'
THM_ACCENT='\033[1;34m'
THM_KEY='\033[1;33m'
THM_VAL='\033[1;37m'
THM_OK='\033[0;32m'
THM_BAD='\033[0;31m'
THM_MUTED='\033[0;37m'

thm_line() {
    echo -e "${THM_BORDER}+----------------------------------------------------------+${THM_NC}"
}

thm_section() {
    local title="$1"
    thm_line
    printf "${THM_BORDER}|${THM_NC} ${THM_ACCENT}%-56s${THM_NC} ${THM_BORDER}|${THM_NC}\n" ">>> ${title} <<<"
    thm_line
}

thm_title() {
    local title="$1"
    thm_line
    printf "${THM_BORDER}|${THM_NC} ${THM_TITLE}%-56s${THM_NC} ${THM_BORDER}|${THM_NC}\n" "$title"
    thm_line
}

thm_welcome() {
    local user_name="${1:-User}"
    thm_line
    printf "${THM_BORDER}|${THM_NC} ${THM_TITLE}%-56s${THM_NC} ${THM_BORDER}|${THM_NC}\n" "Welcome To PanelXray - ${user_name}"
    thm_line
}

thm_info_row() {
    local key="$1"
    local val="$2"
    printf "${THM_BORDER}|${THM_NC} ${THM_KEY}%-16s${THM_NC} = ${THM_VAL}%-36s${THM_NC} ${THM_BORDER}|${THM_NC}\n" "$key" "$val"
}

thm_status_row() {
    local key="$1"
    local val="$2"
    local color="$THM_BAD"
    if [[ "$val" == "ON" || "$val" == "ACTIVE" || "$val" == "RUNNING" ]]; then
        color="$THM_OK"
    fi
    printf "${THM_BORDER}|${THM_NC} ${THM_KEY}%-16s${THM_NC} = ${color}%-36s${THM_NC} ${THM_BORDER}|${THM_NC}\n" "$key" "$val"
}

thm_menu_item() {
    local num="$1"
    local label="$2"
    printf " ${THM_BORDER}[%02d]${THM_NC} ${THM_VAL}%s${THM_NC}\n" "$num" "$label"
}

thm_footer() {
    thm_line
    printf "${THM_BORDER}|${THM_NC} ${THM_MUTED}PanelXray Service Menu${THM_NC}%-34s${THM_BORDER}|${THM_NC}\n" ""
    thm_line
}