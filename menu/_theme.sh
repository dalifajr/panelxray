#!/bin/bash

# Ocean style theme for panel menus.
THM_NC='\033[0m'
THM_CYAN='\033[1;36m'
THM_BLUE='\033[1;34m'
THM_GREEN='\033[0;32m'
THM_YELLOW='\033[1;33m'
THM_RED='\033[0;31m'
THM_WHITE='\033[1;37m'

thm_line() {
    echo -e "${THM_CYAN}+----------------------------------------------------------+${THM_NC}"
}

thm_title() {
    local title="$1"
    thm_line
    printf "${THM_CYAN}|${THM_NC} ${THM_BLUE}%-56s${THM_NC} ${THM_CYAN}|${THM_NC}\n" "$title"
    thm_line
}

thm_welcome() {
    local user_name="${1:-User}"
    thm_line
    printf "${THM_CYAN}|${THM_NC} ${THM_WHITE}%-56s${THM_NC} ${THM_CYAN}|${THM_NC}\n" "Welcome, ${user_name}"
    thm_line
}

thm_info_row() {
    local key="$1"
    local val="$2"
    printf "${THM_CYAN}|${THM_NC} ${THM_YELLOW}%-16s${THM_NC} : ${THM_WHITE}%-35s${THM_NC} ${THM_CYAN}|${THM_NC}\n" "$key" "$val"
}

thm_menu_item() {
    local num="$1"
    local label="$2"
    printf " ${THM_CYAN}[%02d]${THM_NC} ${THM_WHITE}%s${THM_NC}\n" "$num" "$label"
}

thm_footer() {
    thm_line
    printf "${THM_CYAN}|${THM_NC} ${THM_GREEN}PanelXray Service Menu${THM_NC}%-33s${THM_CYAN}|${THM_NC}\n" ""
    thm_line
}
