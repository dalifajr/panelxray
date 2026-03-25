#!/bin/bash
### Color
OFFICIAL_UBUNTU24_REPOS_ONLY="${OFFICIAL_UBUNTU24_REPOS_ONLY:-1}"

enforce_official_ubuntu24_repos() {
    local os_id os_ver src_file keep_file disabled_dir base_name
    os_id="$(. /etc/os-release && echo "$ID")"
    os_ver="$(. /etc/os-release && echo "$VERSION_ID")"

    if [[ "$OFFICIAL_UBUNTU24_REPOS_ONLY" != "1" ]]; then
        return 0
    fi

    if [[ "$os_id" != "ubuntu" ]] || [[ "$os_ver" != 24.04* ]]; then
        return 0
    fi

    disabled_dir="/etc/apt/sources.list.d/disabled-kyt"
    mkdir -p "$disabled_dir"

    # Keep only official Ubuntu source file, disable everything else.
    keep_file="/etc/apt/sources.list.d/ubuntu.sources"
    for src_file in /etc/apt/sources.list.d/*.sources /etc/apt/sources.list.d/*.list; do
        [[ -e "$src_file" ]] || continue
        [[ "$src_file" == "$keep_file" ]] && continue
        base_name="$(basename "$src_file")"
        mv -f "$src_file" "$disabled_dir/${base_name}.disabled"
    done
}

sanitize_apt_sources() {
    local codename
    codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"
    local bad_patterns

    bad_patterns='vbernat/haproxy-2\.0|ppa\.launchpadcontent\.net/vbernat'

    rm -f /etc/apt/sources.list.d/vbernat-ubuntu-haproxy-2_0-*.list
    rm -f /etc/apt/sources.list.d/vbernat-ubuntu-haproxy-2_0-*.sources
    rm -f /etc/apt/sources.list.d/haproxy.list

    # Remove any source file containing known incompatible repositories.
    while IFS= read -r bad_file; do
        rm -f "$bad_file"
    done < <(grep -RlsE "$bad_patterns" /etc/apt/sources.list.d 2>/dev/null || true)

    if grep -RqsE "$bad_patterns" /etc/apt/sources.list 2>/dev/null; then
        sed -i -E '/vbernat\/haproxy-2\.0|ppa\.launchpadcontent\.net\/vbernat/d' /etc/apt/sources.list 2>/dev/null || true
    fi

    if [[ -n "$codename" ]] && [[ -f /etc/apt/sources.list.d/nginx.list ]]; then
        if ! curl -fsSL "https://nginx.org/packages/ubuntu/dists/${codename}/Release" >/dev/null 2>&1 &&
           ! curl -fsSL "https://nginx.org/packages/debian/dists/${codename}/Release" >/dev/null 2>&1; then
            rm -f /etc/apt/sources.list.d/nginx.list /etc/apt/preferences.d/99nginx
        fi
    fi
}

restore_official_ubuntu_sources() {
    local codename
    codename="$(. /etc/os-release && echo "${VERSION_CODENAME:-noble}")"

    mkdir -p /etc/apt/sources.list.d
    cat >/etc/apt/sources.list.d/ubuntu.sources <<EOF
Types: deb
URIs: http://mirrors.digitalocean.com/ubuntu/
Suites: ${codename} ${codename}-updates ${codename}-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg

Types: deb
URIs: http://security.ubuntu.com/ubuntu/
Suites: ${codename}-security
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
EOF

    # Disable legacy monolithic list to avoid duplicate or stale third-party entries.
    : > /etc/apt/sources.list
}

safe_apt_update() {
    local tmplog bad_url log_file
    log_file="/var/log/kyt-apt-sanitize.log"
    tmplog="/tmp/apt-update-premi.$$"

    touch "$log_file" 2>/dev/null || true
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] premi.sh: apt update start" >> "$log_file"

    if apt-get update -y; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] premi.sh: apt update success without sanitize" >> "$log_file"
        return 0
    fi

    apt-get update -y 2>&1 | tee "$tmplog" >/dev/null || true
    while IFS= read -r bad_url; do
        [[ -z "$bad_url" ]] && continue
        grep -Rsl "$bad_url" /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null | while IFS= read -r src_file; do
            if [[ "$src_file" == *.sources ]]; then
                rm -f "$src_file"
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] premi.sh: removed invalid deb822 source $src_file for $bad_url" >> "$log_file"
            else
                sed -i "\|$bad_url| s|^deb |# disabled-invalid-repo deb |" "$src_file"
                sed -i "\|$bad_url| s|^deb-src |# disabled-invalid-repo deb-src |" "$src_file"
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] premi.sh: disabled repo $bad_url in $src_file" >> "$log_file"
            fi
        done
    done < <(grep -Eo 'https?://[^ ]+' "$tmplog" | sed 's#/dists/.*##; s#/InRelease##; s#/Release##' | sort -u)

    rm -f "$tmplog"
    if apt-get update -y; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] premi.sh: apt update success after sanitize" >> "$log_file"
        return 0
    fi

    # Last resort for Ubuntu: rebuild official sources and retry.
    if [[ "$(. /etc/os-release && echo "$ID")" == "ubuntu" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] premi.sh: fallback to official Ubuntu sources" >> "$log_file"
        restore_official_ubuntu_sources
        apt-get clean
        rm -rf /var/lib/apt/lists/*
        if apt-get update -y; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] premi.sh: apt update success after official source restore" >> "$log_file"
            return 0
        fi
    fi

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] premi.sh: apt update failed after sanitize" >> "$log_file"
    return 1
}

INSTALL_PASS_REMOTE_URL="https://raw.githubusercontent.com/dalifajr/rqsbababyl/refs/heads/main/init.conf"

load_installer_password() {
    local content line
    if command -v curl >/dev/null 2>&1; then
        content="$(curl -fsSL "$INSTALL_PASS_REMOTE_URL" 2>/dev/null || true)"
    elif command -v wget >/dev/null 2>&1; then
        content="$(wget -qO- "$INSTALL_PASS_REMOTE_URL" 2>/dev/null || true)"
    fi

    [[ -n "$content" ]] || return 1

    line="$(echo "$content" | awk -F= '/^[[:space:]]*INSTALLER_PASSWORD[[:space:]]*=/{sub(/^[^=]*=/,""); gsub(/^[[:space:]"\047]+|[[:space:]"\047]+$/,""); print; exit}')"
    if [[ -z "$line" ]]; then
        line="$(echo "$content" | awk -F= '/^[[:space:]]*PASSWORD[[:space:]]*=/{sub(/^[^=]*=/,""); gsub(/^[[:space:]"\047]+|[[:space:]"\047]+$/,""); print; exit}')"
    fi

    [[ -n "$line" ]] || return 1
    echo "$line"
}

enforce_installer_password() {
    local expected input
    expected="$(load_installer_password 2>/dev/null || true)"

    if [[ -z "$expected" ]]; then
        echo "Gagal memuat password installer dari URL konfigurasi."
        echo "Periksa file init.conf dan koneksi internet lalu coba lagi."
        exit 1
    fi

    read -rsp "Masukkan password installer: " input
    echo
    if [[ "$input" != "$expected" ]]; then
        echo "Password installer salah. Proses dibatalkan."
        exit 1
    fi
}

enforce_installer_password

enforce_official_ubuntu24_repos
sanitize_apt_sources
if ! safe_apt_update; then
    echo "Apt repository still broken. Check /var/log/kyt-apt-sanitize.log"
    exit 1
fi
apt upgrade -y
apt install -y curl
apt install wondershaper -y
Green="\e[92;1m"
RED="\033[31m"
YELLOW="\033[33m"
BLUE="\033[36m"
FONT="\033[0m"
GREENBG="\033[42;37m"
REDBG="\033[41;37m"
OK="${Green}--->${FONT}"
ERROR="${RED}[ERROR]${FONT}"
GRAY="\e[1;30m"
NC='\e[0m'
red='\e[1;31m'
green='\e[0;32m'
TIME=$(date '+%d %b %Y')
ipsaya=$(wget -qO- ipinfo.io/ip)
TIMES="10"
CHATID="-1002030911878"
KEY="6617696083:AAEbXm7JbDiX3mSzHWeDjHG2_qeC1NqCKxA"
URL="https://api.telegram.org/bot$KEY/sendMessage"
# ===================
clear
  # // Exporint IP AddressInformation
export IP=$( curl -sS icanhazip.com )

# // Clear Data
clear
clear && clear && clear
clear;clear;clear

  # // Banner
echo -e "${YELLOW}----------------------------------------------------------${NC}"
echo -e "  Welcome To Kentot Tunneling ${YELLOW}(${NC}${green} Stable Edition ${NC}${YELLOW})${NC}"
echo -e " This Will Quick Setup VPN Server On Your Server"
echo -e "  Auther : ${green}M dzulfikri alifajri ${NC}${YELLOW}(${NC} ${green} KENTOT TUNNELING${NC}${YELLOW})${NC}"
echo -e "${YELLOW}----------------------------------------------------------${NC}"
echo ""
sleep 2
###### IZIN SC 

# // Checking Os Architecture
if [[ $( uname -m | awk '{print $1}' ) == "x86_64" ]]; then
    echo -e "${OK} Your Architecture Is Supported ( ${green}$( uname -m )${NC} )"
else
    echo -e "${EROR} Your Architecture Is Not Supported ( ${YELLOW}$( uname -m )${NC} )"
    exit 1
fi

# // Checking System
if [[ $( cat /etc/os-release | grep -w ID | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/ID//g' ) == "ubuntu" ]]; then
    echo -e "${OK} Your OS Is Supported ( ${green}$( cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/PRETTY_NAME//g' )${NC} )"
elif [[ $( cat /etc/os-release | grep -w ID | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/ID//g' ) == "debian" ]]; then
    echo -e "${OK} Your OS Is Supported ( ${green}$( cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/PRETTY_NAME//g' )${NC} )"
else
    echo -e "${EROR} Your OS Is Not Supported ( ${YELLOW}$( cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/PRETTY_NAME//g' )${NC} )"
    exit 1
fi

# // IP Address Validating
if [[ $ipsaya == "" ]]; then
    echo -e "${EROR} IP Address ( ${YELLOW}Not Detected${NC} )"
else
    echo -e "${OK} IP Address ( ${green}$IP${NC} )"
fi

# // Validate Successfull
echo ""
read -p "$( echo -e "Press ${GRAY}[ ${NC}${green}Enter${NC} ${GRAY}]${NC} For Starting Installation") "
echo ""
clear
if [ "${EUID}" -ne 0 ]; then
		echo "You need to run this script as root"
		exit 1
fi
if [ "$(systemd-detect-virt)" == "openvz" ]; then
		echo "OpenVZ is not supported"
		exit 1
fi
red='\e[1;31m'
green='\e[0;32m'
NC='\e[0m'
#IZIN SCRIPT
MYIP=$(curl -sS ipv4.icanhazip.com)
echo -e "\e[32mloading...\e[0m"
clear
#IZIN SCRIPT
MYIP=$(curl -sS ipv4.icanhazip.com)
echo -e "\e[32mloading...\e[0m" 
clear
# Version sc
clear
#########################
# USERNAME
rm -f /usr/bin/user
username="$(hostname -s 2>/dev/null || echo User)"
echo "$username" >/usr/bin/user
expx="Lifetime"
echo "$expx" >/usr/bin/e
# DETAIL ORDER
username=$(cat /usr/bin/user)
oid=$(cat /usr/bin/ver)
exp=$(cat /usr/bin/e)
clear
# CERTIFICATE STATUS
valid="$exp"
today=$(date -d "0 days" +"%Y-%m-%d")
d1=$(date -d "$valid" +%s)
d2=$(date -d "$today" +%s)
certifacate=$(((d1 - d2) / 86400))
# VPS Information
DATE=$(date +'%Y-%m-%d')
datediff() {
    d1=$(date -d "$1" +%s)
    d2=$(date -d "$2" +%s)
    echo -e "$COLOR1 $NC Expiry In   : $(( (d1 - d2) / 86400 )) Days"
}
mai="datediff "$Exp" "$DATE""
# Status ExpiRED Active | Geo Project
Info="(${green}Active${NC})"
Error="(${RED}ExpiRED${NC})"
today=$(date -d "0 days" +"%Y-%m-%d")
Exp1="$exp"
if [[ $today < $Exp1 ]]; then
sts="${Info}"
else
sts="${Error}"
fi
echo -e "\e[32mloading...\e[0m"
clear
# REPO    
    REPO="https://raw.githubusercontent.com/dalifajr/panelxray/main/"
    #https://raw.githubusercontent.com/dalifajr/panelxray/main/

####
start=$(date +%s)
secs_to_human() {
    echo "Installation time : $((${1} / 3600)) hours $(((${1} / 60) % 60)) minute's $((${1} % 60)) seconds"
}

INSTALL_TOTAL_STEPS=25
INSTALL_CURRENT_STEP=0

draw_install_progress() {
    local label="$1" width=40 filled percent bar empty
    percent=$((INSTALL_CURRENT_STEP * 100 / INSTALL_TOTAL_STEPS))
    filled=$((percent * width / 100))
    empty=$((width - filled))
    bar="$(printf '%*s' "$filled" '' | tr ' ' '#')"
    bar+="$(printf '%*s' "$empty" '' | tr ' ' '-')"
    printf "\r${YELLOW}Progress:${NC} [%2d/%2d] [%s] %3d%% - %s\n" \
        "$INSTALL_CURRENT_STEP" "$INSTALL_TOTAL_STEPS" "$bar" "$percent" "$label"
}

run_install_step() {
    local label="$1" fn="$2"
    INSTALL_CURRENT_STEP=$((INSTALL_CURRENT_STEP + 1))
    draw_install_progress "$label"
    "$fn"
}

### Status
function print_ok() {
    echo -e "${OK} ${BLUE} $1 ${FONT}"
}
function print_install() {
	echo -e "${green} =============================== ${FONT}"
    echo -e "${YELLOW} # $1 ${FONT}"
	echo -e "${green} =============================== ${FONT}"
    sleep 1
}

function print_error() {
    echo -e "${ERROR} ${REDBG} $1 ${FONT}"
}

function print_success() {
    if [[ 0 -eq $? ]]; then
		echo -e "${green} =============================== ${FONT}"
        echo -e "${Green} # $1 berhasil dipasang"
		echo -e "${green} =============================== ${FONT}"
        sleep 2
    fi
}

### Cek root
function is_root() {
    if [[ 0 == "$UID" ]]; then
        print_ok "Root user Start installation process"
    else
        print_error "The current user is not the root user, please switch to the root user and run the script again"
    fi

}

# Buat direktori xray
print_install "Membuat direktori xray"
    mkdir -p /etc/xray
    curl -s ifconfig.me > /etc/xray/ipvps
    touch /etc/xray/domain
    mkdir -p /var/log/xray
    chown www-data.www-data /var/log/xray
    chmod +x /var/log/xray
    touch /var/log/xray/access.log
    touch /var/log/xray/error.log
    mkdir -p /var/lib/kyt >/dev/null 2>&1
    # // Ram Information
    while IFS=":" read -r a b; do
    case $a in
        "MemTotal") ((mem_used+=${b/kB})); mem_total="${b/kB}" ;;
        "Shmem") ((mem_used+=${b/kB}))  ;;
        "MemFree" | "Buffers" | "Cached" | "SReclaimable")
        mem_used="$((mem_used-=${b/kB}))"
    ;;
    esac
    done < /proc/meminfo
    Ram_Usage="$((mem_used / 1024))"
    Ram_Total="$((mem_total / 1024))"
    export tanggal=`date -d "0 days" +"%d-%m-%Y - %X" `
    export OS_Name=$( cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/PRETTY_NAME//g' | sed 's/=//g' | sed 's/"//g' )
    export Kernel=$( uname -r )
    export Arch=$( uname -m )
    export IP=$( curl -s https://ipinfo.io/ip/ )

# Change Environment System
function first_setup(){
    timedatectl set-timezone Asia/Jakarta
    echo iptables-persistent iptables-persistent/autosave_v4 boolean true | debconf-set-selections
    echo iptables-persistent iptables-persistent/autosave_v6 boolean true | debconf-set-selections
    print_success "Directory Xray"
    if [[ $(cat /etc/os-release | grep -w ID | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/ID//g') == "ubuntu" ]]; then
    echo "Setup Dependencies $(cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/PRETTY_NAME//g')"
    safe_apt_update
    apt-get install -y --no-install-recommends software-properties-common
    apt-get install -y haproxy
elif [[ $(cat /etc/os-release | grep -w ID | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/ID//g') == "debian" ]]; then
    echo "Setup Dependencies For OS Is $(cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/PRETTY_NAME//g')"
    safe_apt_update
    apt-get install -y haproxy
else
    echo -e " Your OS Is Not Supported ($(cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/PRETTY_NAME//g') )"
    exit 1
fi
}

# GEO PROJECT
clear
function nginx_install() {
    # // Checking System
    if [[ $(cat /etc/os-release | grep -w ID | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/ID//g') == "ubuntu" ]]; then
        print_install "Setup nginx For OS Is $(cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/PRETTY_NAME//g')"
        # // sudo add-apt-repository ppa:nginx/stable -y 
        sudo apt-get install nginx -y 
    elif [[ $(cat /etc/os-release | grep -w ID | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/ID//g') == "debian" ]]; then
        print_success "Setup nginx For OS Is $(cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/PRETTY_NAME//g')"
        apt -y install nginx 
    else
        echo -e " Your OS Is Not Supported ( ${YELLOW}$(cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/PRETTY_NAME//g')${FONT} )"
        # // exit 1
    fi
}

# Update and remove packages
function base_package() {
    clear
    ########
    print_install "Menginstall Packet Yang Dibutuhkan"
    apt install zip pwgen openssl netcat-openbsd socat cron bash-completion -y
    apt install figlet -y
    safe_apt_update
    apt upgrade -y
    apt dist-upgrade -y
    systemctl enable chronyd
    systemctl restart chronyd
    systemctl enable chrony
    systemctl restart chrony
    chronyc sourcestats -v
    chronyc tracking -v
    apt install ntpdate -y
    ntpdate pool.ntp.org
    apt install sudo -y
    sudo apt-get clean all
    sudo apt-get autoremove -y
    sudo apt-get install -y debconf-utils
    sudo apt-get remove --purge exim4 -y
    sudo apt-get remove --purge ufw firewalld -y
    sudo apt-get install -y --no-install-recommends software-properties-common
    echo iptables-persistent iptables-persistent/autosave_v4 boolean true | debconf-set-selections
    echo iptables-persistent iptables-persistent/autosave_v6 boolean true | debconf-set-selections
    sudo apt-get install -y speedtest-cli vnstat libnss3-dev libnspr4-dev pkg-config libpam0g-dev libcap-ng-dev libcap-ng-utils libselinux1-dev libcurl4-openssl-dev flex bison make libnss3-tools libevent-dev bc rsyslog dos2unix zlib1g-dev libssl-dev libsqlite3-dev sed dirmngr libxml-parser-perl build-essential gcc g++ python3 htop lsof tar wget curl ruby zip unzip p7zip-full python3-pip libc6 util-linux build-essential msmtp-mta ca-certificates bsd-mailx iptables iptables-persistent netfilter-persistent net-tools openssl ca-certificates gnupg gnupg2 ca-certificates lsb-release gcc shc make cmake git screen socat xz-utils apt-transport-https dnsutils cron bash-completion ntpdate chrony jq openvpn easy-rsa netcat-openbsd
    print_success "Packet Yang Dibutuhkan"
    
}

function preflight_check(){
    clear
    print_install "Preflight Dependency Check"

    local os_id os_ver
    os_id="$(. /etc/os-release && echo "$ID")"
    os_ver="$(. /etc/os-release && echo "$VERSION_ID")"

    if [[ "$os_id" != "ubuntu" && "$os_id" != "debian" ]]; then
        print_error "OS tidak didukung: $os_id"
        exit 1
    fi

    if [[ "$os_id" == "ubuntu" ]]; then
        if dpkg --compare-versions "$os_ver" lt "20.04"; then
            print_error "Ubuntu minimal 20.04, terdeteksi $os_ver"
            exit 1
        fi
        print_ok "Detected Ubuntu $os_ver"
    else
        print_ok "Detected Debian $os_ver"
    fi

    local bins=(curl wget awk sed grep systemctl)
    local b
    for b in "${bins[@]}"; do
        if ! command -v "$b" >/dev/null 2>&1; then
            print_error "Binary wajib tidak ditemukan: $b"
            exit 1
        fi
    done

    safe_apt_update >/dev/null 2>&1

    local pkg required_pkgs missing_pkgs
    required_pkgs=(
        curl wget jq unzip tar cron nginx haproxy openvpn dropbear vnstat
        python3 python3-pip iptables-persistent netfilter-persistent netcat-openbsd
    )
    missing_pkgs=()

    for pkg in "${required_pkgs[@]}"; do
        if ! apt-cache show "$pkg" >/dev/null 2>&1; then
            missing_pkgs+=("$pkg")
        fi
    done

    if [ ${#missing_pkgs[@]} -gt 0 ]; then
        print_error "Package tidak tersedia di repo: ${missing_pkgs[*]}"
        exit 1
    fi

    print_success "Preflight Dependency Check"
}
clear
# Fungsi input domain
function pasang_domain() {
echo -e ""
clear
    echo -e "   .----------------------------------."
echo -e "   |\e[1;32mPlease Select a Domain Type Below \e[0m|"
echo -e "   '----------------------------------'"
echo -e "     \e[1;32m1)\e[0m Domain Sendiri"
echo -e "     \e[1;32m2)\e[0m Gunakan Domain Random (BETA) "
echo -e "   ------------------------------------"
read -p "   Please select numbers 1-2 or Any Button(Random) : " host
echo ""
if [[ $host == "1" ]]; then
echo -e "   \e[1;32mPlease Enter Your Subdomain $NC"
read -p "   Subdomain: " host1
echo "IP=" >> /var/lib/kyt/ipvps.conf
echo $host1 > /etc/xray/domain
echo $host1 > /root/domain
echo ""
elif [[ $host == "2" ]]; then
#install cf
wget ${REPO}limit/cf.sh && chmod +x cf.sh && ./cf.sh
rm -f /root/cf.sh
clear
else
print_install "Random Subdomain/Domain is Used"
clear
    fi
}

clear
#GANTI PASSWORD DEFAULT
restart_system() {
    USRSC=$(cat /usr/bin/user 2>/dev/null || echo User)
    EXPSC=$(cat /usr/bin/e 2>/dev/null || echo Lifetime)
    TIMEZONE=$(printf '%(%H:%M:%S)T')
    TEXT="
<code>────────────────────</code>
<b>⚡AUTOSCRIPT PREMIUM⚡</b>
<code>────────────────────</code>
<code>ID     : </code><code>$USRSC</code>
<code>Domain : </code><code>$domain</code>
<code>Date   : </code><code>$TIME</code>
<code>Time   : </code><code>$TIMEZONE</code>
<code>Ip vps : </code><code>$ipsaya</code>
<code>Exp Sc : </code><code>$EXPSC</code>
<code>────────────────────</code>
<i>Automatic Notification from Github</i>
"'&reply_markup={"inline_keyboard":[[{"text":"ᴏʀᴅᴇʀ🐳","url":"https://t.me/supra_store31"},{"text":"ɪɴꜱᴛᴀʟʟ🐬","url":"https://t.me/nusantaraVpn"}]]}'
    curl -s --max-time $TIMES -d "chat_id=$CHATID&disable_web_page_preview=1&text=$TEXT&parse_mode=html" $URL >/dev/null
}
clear
# Pasang SSL
ensure_valid_xray_certificates() {
    local domain cert_file key_file log_file
    cert_file="/etc/xray/xray.crt"
    key_file="/etc/xray/xray.key"
    log_file="/var/log/panelxray-nginx-check.log"
    domain="$(cat /etc/xray/domain 2>/dev/null || echo localhost)"

    mkdir -p /etc/xray
    touch "$log_file" 2>/dev/null || true

    if openssl x509 -in "$cert_file" -noout >/dev/null 2>&1 && \
       openssl pkey -in "$key_file" -noout >/dev/null 2>&1; then
        return 0
    fi

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] invalid or missing xray cert/key, generating self-signed cert for ${domain}" >>"$log_file"
    rm -f "$cert_file" "$key_file"
    openssl req -x509 -nodes -newkey rsa:2048 \
        -keyout "$key_file" \
        -out "$cert_file" \
        -days 3650 \
        -subj "/CN=${domain}" >/dev/null 2>&1 || true
    chmod 600 "$key_file" 2>/dev/null || true
    chmod 644 "$cert_file" 2>/dev/null || true
}

sanitize_nginx_xray_conf() {
    local conf_file
    conf_file="/etc/nginx/conf.d/xray.conf"

    [[ -f "$conf_file" ]] || return 0

    if openssl x509 -in /etc/xray/xray.crt -noout >/dev/null 2>&1 && \
       openssl pkey -in /etc/xray/xray.key -noout >/dev/null 2>&1; then
        return 0
    fi

    # Remove SSL-only stanza and directives when certificate material is not usable.
    awk '
        BEGIN { in_ssl_server=0 }
        /listen 81 ssl http2 reuseport;/ { in_ssl_server=1; next }
        in_ssl_server && /^}/ { in_ssl_server=0; next }
        in_ssl_server { next }
        /ssl_certificate / { next }
        /ssl_certificate_key / { next }
        /ssl_ciphers / { next }
        /ssl_protocols / { next }
        { print }
    ' "$conf_file" >"${conf_file}.tmp" && mv -f "${conf_file}.tmp" "$conf_file"
}

validate_nginx_config() {
    local log_file backup_file domain
    log_file="/var/log/panelxray-nginx-check.log"
    domain="$(cat /etc/xray/domain 2>/dev/null || echo localhost)"
    touch "$log_file" 2>/dev/null || true

    ensure_valid_xray_certificates
    sanitize_nginx_xray_conf

    if nginx -t >>"$log_file" 2>&1; then
        return 0
    fi

    backup_file="/etc/nginx/conf.d/xray.conf.broken.$(date +%s)"
    cp -f /etc/nginx/conf.d/xray.conf "$backup_file" 2>/dev/null || true
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] invalid nginx config, backup: $backup_file" >>"$log_file"

    wget -qO /etc/nginx/conf.d/xray.conf "${REPO}limit/xray.conf" || true
    sed -i "s/xxx/${domain}/g" /etc/nginx/conf.d/xray.conf 2>/dev/null || true

    ensure_valid_xray_certificates
    sanitize_nginx_xray_conf

    if ! nginx -t >>"$log_file" 2>&1; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] template still invalid, applying minimal safe nginx config" >>"$log_file"
        cat >/etc/nginx/conf.d/xray.conf <<EOF
server {
    listen 1010;
    server_name _;
    return 200;
}

server {
    listen 81;
    server_name _;
    root /var/www/html;
}
EOF
    fi
}

function pasang_ssl() {
clear
print_install "Memasang SSL Pada Domain"
    rm -rf /etc/xray/xray.key
    rm -rf /etc/xray/xray.crt
    domain=$(cat /root/domain)
    STOPWEBSERVER=$(lsof -i:80 | cut -d' ' -f1 | awk 'NR==2 {print $1}')
    rm -rf /root/.acme.sh
    mkdir /root/.acme.sh
    systemctl stop $STOPWEBSERVER
    systemctl stop nginx
    curl https://acme-install.netlify.app/acme.sh -o /root/.acme.sh/acme.sh
    chmod +x /root/.acme.sh/acme.sh
    /root/.acme.sh/acme.sh --upgrade --auto-upgrade
    /root/.acme.sh/acme.sh --set-default-ca --server letsencrypt
    /root/.acme.sh/acme.sh --issue -d $domain --standalone -k ec-256
    ~/.acme.sh/acme.sh --installcert -d $domain --fullchainpath /etc/xray/xray.crt --keypath /etc/xray/xray.key --ecc
    ensure_valid_xray_certificates
    chmod 777 /etc/xray/xray.key
    print_success "SSL Certificate"
}

function make_folder_xray() {
rm -rf /etc/vmess/.vmess.db
    rm -rf /etc/vless/.vless.db
    rm -rf /etc/trojan/.trojan.db
    rm -rf /etc/shadowsocks/.shadowsocks.db
    rm -rf /etc/ssh/.ssh.db
    rm -rf /etc/bot/.bot.db
    mkdir -p /etc/bot
    mkdir -p /etc/xray
    mkdir -p /etc/vmess
    mkdir -p /etc/vless
    mkdir -p /etc/trojan
    mkdir -p /etc/shadowsocks
    mkdir -p /etc/ssh
    mkdir -p /usr/bin/xray/
    mkdir -p /var/log/xray/
    mkdir -p /var/www/html
    mkdir -p /etc/kyt/limit/vmess/ip
    mkdir -p /etc/kyt/limit/vless/ip
    mkdir -p /etc/kyt/limit/trojan/ip
    mkdir -p /etc/kyt/limit/ssh/ip
    mkdir -p /etc/limit/vmess
    mkdir -p /etc/limit/vless
    mkdir -p /etc/limit/trojan
    mkdir -p /etc/limit/ssh
    chmod +x /var/log/xray
    touch /etc/xray/domain
    touch /var/log/xray/access.log
    touch /var/log/xray/error.log
    touch /etc/vmess/.vmess.db
    touch /etc/vless/.vless.db
    touch /etc/trojan/.trojan.db
    touch /etc/shadowsocks/.shadowsocks.db
    touch /etc/ssh/.ssh.db
    touch /etc/bot/.bot.db
    echo "& plughin Account" >>/etc/vmess/.vmess.db
    echo "& plughin Account" >>/etc/vless/.vless.db
    echo "& plughin Account" >>/etc/trojan/.trojan.db
    echo "& plughin Account" >>/etc/shadowsocks/.shadowsocks.db
    echo "& plughin Account" >>/etc/ssh/.ssh.db
    }
#Instal Xray
function install_xray() {
clear
    print_install "Core Xray 1.8.1 Latest Version"
    # install xray
    #echo -e "[ ${green}INFO$NC ] Downloading & Installing xray core"
    domainSock_dir="/run/xray";! [ -d $domainSock_dir ] && mkdir  $domainSock_dir
    chown www-data.www-data $domainSock_dir
    
    # / / Ambil Xray Core Version Terbaru
latest_version="$(curl -s https://api.github.com/repos/XTLS/Xray-core/releases | grep tag_name | sed -E 's/.*"v(.*)".*/\1/' | head -n 1)"
bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install -u www-data --version $latest_version
 
    # // Ambil Config Server
    wget -O /etc/xray/config.json "${REPO}limit/config.json" >/dev/null 2>&1
    #wget -O /usr/local/bin/xray "${REPO}xray/xray.linux.64bit" >/dev/null 2>&1
    wget -O /etc/systemd/system/runn.service "${REPO}limit/runn.service" >/dev/null 2>&1
    #chmod +x /usr/local/bin/xray
    domain=$(cat /etc/xray/domain)
    IPVS=$(cat /etc/xray/ipvps)
    print_success "Core Xray 1.8.1 Latest Version"
    
    # // Settings UP Nginix Server
    clear
    curl -s ipinfo.io/city >>/etc/xray/city
    curl -s ipinfo.io/org | cut -d " " -f 2-10 >>/etc/xray/isp
    print_install "Memasang Konfigurasi Packet"
    wget -O /etc/haproxy/haproxy.cfg "${REPO}limit/haproxy.cfg" >/dev/null 2>&1
    wget -O /etc/nginx/conf.d/xray.conf "${REPO}limit/xray.conf" >/dev/null 2>&1
    sed -i "s/xxx/${domain}/g" /etc/haproxy/haproxy.cfg
    sed -i "s/xxx/${domain}/g" /etc/nginx/conf.d/xray.conf
    curl ${REPO}limit/nginx.conf > /etc/nginx/nginx.conf
    validate_nginx_config

    if [[ -f /etc/xray/xray.crt && -f /etc/xray/xray.key ]]; then
        cat /etc/xray/xray.crt /etc/xray/xray.key | tee /etc/haproxy/hap.pem >/dev/null
    fi

    if [[ ! -s /etc/haproxy/hap.pem ]]; then
        # Avoid boot failure if certificate bundle is not ready yet.
        sed -i '/haproxy-https accept-proxy ssl crt \/etc\/haproxy\/hap.pem/d' /etc/haproxy/haproxy.cfg
        sed -i '/loopback-for-https abns@haproxy-https/d' /etc/haproxy/haproxy.cfg
    fi

    validate_haproxy_config

    # > Set Permission
    chmod +x /etc/systemd/system/runn.service

    # > Create Service
    rm -rf /etc/systemd/system/xray.service.d
    cat >/etc/systemd/system/xray.service <<EOF
[Unit]
Description=Xray Service
Documentation=https://github.com
After=network.target nss-lookup.target

[Service]
User=www-data
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ExecStart=/usr/local/bin/xray run -config /etc/xray/config.json
Restart=on-failure
RestartPreventExitStatus=23
LimitNPROC=10000
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target

EOF
print_success "Konfigurasi Packet"
}

validate_haproxy_config() {
    local log_file backup_file domain
    log_file="/var/log/panelxray-haproxy-check.log"
    domain="$(cat /etc/xray/domain 2>/dev/null || echo localhost)"
    mkdir -p /etc/haproxy
    touch "$log_file" 2>/dev/null || true

    if [[ ! -s /etc/haproxy/haproxy.cfg ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] haproxy.cfg missing, writing fallback config" >>"$log_file"
        cat >/etc/haproxy/haproxy.cfg <<EOF
global
    log /dev/log local0
    log /dev/log local1 notice
    daemon

defaults
    log global
    mode tcp
    timeout connect 5s
    timeout client 50s
    timeout server 50s

frontend panelxray_tcp
    bind *:443
    default_backend panelxray_backend

backend panelxray_backend
    server local 127.0.0.1:1010 check
EOF
    fi

    # HAProxy 3.x removed bind-process; strip it if present for compatibility.
    sed -i -E '/^[[:space:]]*bind-process[[:space:]]+/d' /etc/haproxy/haproxy.cfg 2>/dev/null || true

    if ! haproxy -c -f /etc/haproxy/haproxy.cfg >>"$log_file" 2>&1; then
        backup_file="/etc/haproxy/haproxy.cfg.broken.$(date +%s)"
        cp -f /etc/haproxy/haproxy.cfg "$backup_file"
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] invalid haproxy.cfg, backup: $backup_file" >>"$log_file"

        wget -qO /etc/haproxy/haproxy.cfg "${REPO}limit/haproxy.cfg" || true
        sed -i "s/xxx/${domain}/g" /etc/haproxy/haproxy.cfg 2>/dev/null || true
        sed -i -E '/^[[:space:]]*bind-process[[:space:]]+/d' /etc/haproxy/haproxy.cfg 2>/dev/null || true

        if [[ ! -s /etc/haproxy/hap.pem ]]; then
            sed -i '/haproxy-https accept-proxy ssl crt \/etc\/haproxy\/hap.pem/d' /etc/haproxy/haproxy.cfg
            sed -i '/loopback-for-https abns@haproxy-https/d' /etc/haproxy/haproxy.cfg
        fi

        if ! haproxy -c -f /etc/haproxy/haproxy.cfg >>"$log_file" 2>&1; then
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] template still invalid, applying minimal safe config" >>"$log_file"
            cat >/etc/haproxy/haproxy.cfg <<EOF
global
    log /dev/log local0
    log /dev/log local1 notice
    daemon

defaults
    log global
    mode tcp
    timeout connect 5s
    timeout client 50s
    timeout server 50s

frontend panelxray_tcp
    bind *:443
    default_backend panelxray_backend

backend panelxray_backend
    server local 127.0.0.1:1010 check
EOF
        fi
    fi
}

function ssh(){
clear
print_install "Memasang Password SSH"
    wget -O /etc/pam.d/common-password "${REPO}limit/password"
chmod +x /etc/pam.d/common-password

    DEBIAN_FRONTEND=noninteractive dpkg-reconfigure keyboard-configuration
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/altgr select The default for the keyboard layout"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/compose select No compose key"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/ctrl_alt_bksp boolean false"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/layoutcode string de"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/layout select English"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/modelcode string pc105"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/model select Generic 105-key (Intl) PC"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/optionscode string "
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/store_defaults_in_debconf_db boolean true"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/switch select No temporary switch"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/toggle select No toggling"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/unsupported_config_layout boolean true"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/unsupported_config_options boolean true"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/unsupported_layout boolean true"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/unsupported_options boolean true"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/variantcode string "
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/variant select English"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/xkb-keymap select "

# go to root
cd

# Edit file /etc/systemd/system/rc-local.service
cat > /etc/systemd/system/rc-local.service <<-END
[Unit]
Description=/etc/rc.local
ConditionPathExists=/etc/rc.local
[Service]
Type=forking
ExecStart=/etc/rc.local start
TimeoutSec=0
StandardOutput=tty
RemainAfterExit=yes
SysVStartPriority=99
[Install]
WantedBy=multi-user.target
END

# // nano /etc/rc.local
cat > /etc/rc.local <<-END
#!/bin/sh -e
# rc.local
# By default this script does nothing.
exit 0
END

# // Ubah izin akses
chmod +x /etc/rc.local

# // enable rc local
systemctl enable rc-local
systemctl start rc-local.service

# // disable ipv6
echo 1 > /proc/sys/net/ipv6/conf/all/disable_ipv6
sed -i '$ i\echo 1 > /proc/sys/net/ipv6/conf/all/disable_ipv6' /etc/rc.local

# // update
# // set time GMT +7
ln -fs /usr/share/zoneinfo/Asia/Jakarta /etc/localtime

# // set locale
sed -i 's/AcceptEnv/#AcceptEnv/g' /etc/ssh/sshd_config
print_success "Password SSH"
}

function udp_mini(){
clear
print_install "Memasang Service Limit Quota"
wget raw.githubusercontent.com/fttunnel7/vip/main/limit/limit.sh && chmod +x limit.sh && ./limit.sh

cd
wget -q -O /usr/bin/limit-ip "${REPO}limit/limit-ip"
chmod +x /usr/bin/limit-ip
cd /usr/bin
sed -i 's/\r//' limit-ip
cd
clear
#SERVICE LIMIT ALL IP
cat >/etc/systemd/system/vmip.service << EOF
[Unit]
Description=My
After=network.target

[Service]
WorkingDirectory=/root
ExecStart=/usr/bin/limit-ip vmip
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl restart vmip
systemctl enable vmip

cat >/etc/systemd/system/vlip.service << EOF
[Unit]
Description=My
After=network.target

[Service]
WorkingDirectory=/root
ExecStart=/usr/bin/limit-ip vlip
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl restart vlip
systemctl enable vlip

cat >/etc/systemd/system/trip.service << EOF
[Unit]
Description=My
After=network.target

[Service]
WorkingDirectory=/root
ExecStart=/usr/bin/limit-ip trip
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl restart trip
systemctl enable trip
#SERVICE LIMIT QUOTA

#SERVICE VMESS
# // Installing UDP Mini
mkdir -p /usr/local/kyt/
wget -q -O /usr/local/kyt/udp-mini "${REPO}limit/udp-mini"
chmod +x /usr/local/kyt/udp-mini
wget -q -O /etc/systemd/system/udp-mini-1.service "${REPO}limit/udp-mini-1.service"
wget -q -O /etc/systemd/system/udp-mini-2.service "${REPO}limit/udp-mini-2.service"
wget -q -O /etc/systemd/system/udp-mini-3.service "${REPO}limit/udp-mini-3.service"
systemctl disable udp-mini-1
systemctl stop udp-mini-1
systemctl enable udp-mini-1
systemctl start udp-mini-1
systemctl disable udp-mini-2
systemctl stop udp-mini-2
systemctl enable udp-mini-2
systemctl start udp-mini-2
systemctl disable udp-mini-3
systemctl stop udp-mini-3
systemctl enable udp-mini-3
systemctl start udp-mini-3
print_success "Limit Quota Service"
}

function ssh_slow(){
clear
# // Installing UDP Mini
print_install "Memasang modul SlowDNS Server"
    wget -q -O /tmp/nameserver "${REPO}limit/nameserver" >/dev/null 2>&1
    chmod +x /tmp/nameserver
    bash /tmp/nameserver | tee /root/install.log
 print_success "SlowDNS"
}

clear
function ins_SSHD(){
clear
print_install "Memasang SSHD"
wget -q -O /etc/ssh/sshd_config "${REPO}limit/sshd" >/dev/null 2>&1
chmod 700 /etc/ssh/sshd_config
/etc/init.d/ssh restart
systemctl restart ssh
/etc/init.d/ssh status
print_success "SSHD"
}

clear
function ins_dropbear(){
clear
print_install "Menginstall Dropbear"
# // Installing Dropbear
apt-get install dropbear -y > /dev/null 2>&1
wget -q -O /etc/default/dropbear "${REPO}limit/dropbear.conf"
chmod +x /etc/default/dropbear
/etc/init.d/dropbear restart
/etc/init.d/dropbear status
print_success "Dropbear"
}

clear
function ins_vnstat(){
clear
print_install "Menginstall Vnstat"
# setting vnstat
apt -y install vnstat > /dev/null 2>&1
/etc/init.d/vnstat restart
apt -y install libsqlite3-dev > /dev/null 2>&1
wget https://humdi.net/vnstat/vnstat-2.6.tar.gz
tar zxvf vnstat-2.6.tar.gz
cd vnstat-2.6
./configure --prefix=/usr --sysconfdir=/etc && make && make install
cd
vnstat -u -i $NET
sed -i 's/Interface "'""eth0""'"/Interface "'""$NET""'"/g' /etc/vnstat.conf
chown vnstat:vnstat /var/lib/vnstat -R
systemctl enable vnstat
/etc/init.d/vnstat restart
/etc/init.d/vnstat status
rm -f /root/vnstat-2.6.tar.gz
rm -rf /root/vnstat-2.6
print_success "Vnstat"
}

function ins_openvpn(){
clear
print_install "Menginstall OpenVPN"
#OpenVPN
wget ${REPO}limit/openvpn &&  chmod +x openvpn && ./openvpn
if [[ -x /etc/init.d/openvpn ]]; then
    /etc/init.d/openvpn restart >/dev/null 2>&1 || true
elif systemctl list-unit-files 2>/dev/null | grep -q '^openvpn\.service'; then
    systemctl restart openvpn >/dev/null 2>&1 || true
elif systemctl list-unit-files 2>/dev/null | grep -q '^openvpn-server@server\.service'; then
    systemctl restart openvpn-server@server >/dev/null 2>&1 || true
fi
print_success "OpenVPN"
}

function ins_backup(){
clear
print_install "Memasang Backup Server"
#BackupOption
apt install rclone -y
printf "q\n" | rclone config
wget -O /root/.config/rclone/rclone.conf "${REPO}limit/rclone.conf"
#Install Wondershaper
cd /bin
git clone  https://github.com/magnific0/wondershaper.git
cd wondershaper
sudo make install
cd
rm -rf wondershaper
echo > /home/limit
apt install msmtp-mta ca-certificates bsd-mailx -y
cat<<EOF>>/etc/msmtprc
defaults
tls on
tls_starttls on
tls_trust_file /etc/ssl/certs/ca-certificates.crt

account default
host smtp.gmail.com
port 587
auth on
user oceantestdigital@gmail.com
from oceantestdigital@gmail.com
password jokerman77 
logfile ~/.msmtp.log
EOF
chown -R www-data:www-data /etc/msmtprc
wget -q -O /etc/ipserver "${REPO}limit/ipserver" && bash /etc/ipserver
print_success "Backup Server"
}

clear
function ins_swab(){
clear
print_install "Memasang Swap 1 G"
gotop_latest="$(curl -s https://api.github.com/repos/xxxserxxx/gotop/releases | grep tag_name | sed -E 's/.*"v(.*)".*/\1/' | head -n 1)"
    gotop_link="https://github.com/xxxserxxx/gotop/releases/download/v$gotop_latest/gotop_v"$gotop_latest"_linux_amd64.deb"
    curl -sL "$gotop_link" -o /tmp/gotop.deb
    dpkg -i /tmp/gotop.deb >/dev/null 2>&1
    
        # > Buat swap sebesar 1G
    dd if=/dev/zero of=/swapfile bs=1024 count=1048576
    mkswap /swapfile
    chown root:root /swapfile
    chmod 0600 /swapfile >/dev/null 2>&1
    swapon /swapfile >/dev/null 2>&1
    sed -i '$ i\/swapfile      swap swap   defaults    0 0' /etc/fstab

    # > Singkronisasi jam
    chronyd -q 'server 0.id.pool.ntp.org iburst'
    chronyc sourcestats -v
    chronyc tracking -v
    
    wget ${REPO}limit/bbr.sh &&  chmod +x bbr.sh && ./bbr.sh
print_success "Swap 1 G"
}

function ins_Fail2ban(){
clear
print_install "Menginstall Fail2ban"
if ! dpkg -s fail2ban >/dev/null 2>&1; then
    apt-get install -y fail2ban >/dev/null 2>&1 || apt install -y fail2ban >/dev/null 2>&1
fi
systemctl daemon-reload >/dev/null 2>&1
systemctl enable --now fail2ban >/dev/null 2>&1 || true
if systemctl is-active --quiet fail2ban; then
    print_success "Fail2ban service active"
else
    print_error "Fail2ban service failed to start"
fi

# Instal DDOS Flate
if [ -d '/usr/local/ddos' ]; then
    echo; echo; echo "Info: /usr/local/ddos already exists, continue setup"
else
	mkdir /usr/local/ddos
fi

clear
# banner
echo "Banner /etc/kyt.txt" >>/etc/ssh/sshd_config
sed -i 's@DROPBEAR_BANNER=""@DROPBEAR_BANNER="/etc/kyt.txt"@g' /etc/default/dropbear

# Ganti Banner
wget -O /etc/kyt.txt "${REPO}limit/issue.net"
print_success "Fail2ban"
}

function ins_epro(){
clear
print_install "Menginstall ePro WebSocket Proxy"
    wget -O /usr/bin/ws "${REPO}limit/ws" >/dev/null 2>&1
    wget -O /usr/bin/ws.py "${REPO}limit/ws.py" >/dev/null 2>&1
    wget -O /usr/bin/tun.conf "${REPO}limit/tun.conf" >/dev/null 2>&1
    wget -O /etc/systemd/system/ws.service "${REPO}limit/ws.service" >/dev/null 2>&1
    chmod +x /etc/systemd/system/ws.service
    chmod +x /usr/bin/ws
    chmod +x /usr/bin/ws.py
    chmod 644 /usr/bin/tun.conf
systemctl disable ws
systemctl stop ws
systemctl enable ws
systemctl start ws
systemctl restart ws
wget -q -O /usr/local/share/xray/geosite.dat "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat" >/dev/null 2>&1
wget -q -O /usr/local/share/xray/geoip.dat "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat" >/dev/null 2>&1
wget -O /usr/sbin/ftvpn "${REPO}limit/ftvpn" >/dev/null 2>&1
chmod +x /usr/sbin/ftvpn
iptables -A FORWARD -m string --string "get_peers" --algo bm -j DROP
iptables -A FORWARD -m string --string "announce_peer" --algo bm -j DROP
iptables -A FORWARD -m string --string "find_node" --algo bm -j DROP
iptables -A FORWARD -m string --algo bm --string "BitTorrent" -j DROP
iptables -A FORWARD -m string --algo bm --string "BitTorrent protocol" -j DROP
iptables -A FORWARD -m string --algo bm --string "peer_id=" -j DROP
iptables -A FORWARD -m string --algo bm --string ".torrent" -j DROP
iptables -A FORWARD -m string --algo bm --string "announce.php?passkey=" -j DROP
iptables -A FORWARD -m string --algo bm --string "torrent" -j DROP
iptables -A FORWARD -m string --algo bm --string "announce" -j DROP
iptables -A FORWARD -m string --algo bm --string "info_hash" -j DROP
iptables-save > /etc/iptables.up.rules
iptables-restore -t < /etc/iptables.up.rules
if command -v netfilter-persistent >/dev/null 2>&1; then
    netfilter-persistent save >/dev/null 2>&1 || true
    netfilter-persistent reload >/dev/null 2>&1 || true
fi

# remove unnecessary files
cd
apt autoclean -y >/dev/null 2>&1
apt autoremove -y >/dev/null 2>&1
print_success "ePro WebSocket Proxy"
}

function ins_restart(){
clear
print_install "Restarting  All Packet"
validate_nginx_config
if [[ -x /etc/init.d/nginx ]]; then /etc/init.d/nginx restart >/dev/null 2>&1 || true; else systemctl restart nginx >/dev/null 2>&1 || true; fi
if [[ -x /etc/init.d/openvpn ]]; then
    /etc/init.d/openvpn restart >/dev/null 2>&1 || true
elif systemctl list-unit-files 2>/dev/null | grep -q '^openvpn\.service'; then
    systemctl restart openvpn >/dev/null 2>&1 || true
elif systemctl list-unit-files 2>/dev/null | grep -q '^openvpn-server@server\.service'; then
    systemctl restart openvpn-server@server >/dev/null 2>&1 || true
fi
if [[ -x /etc/init.d/ssh ]]; then /etc/init.d/ssh restart >/dev/null 2>&1 || true; else systemctl restart ssh >/dev/null 2>&1 || true; fi
if [[ -x /etc/init.d/dropbear ]]; then /etc/init.d/dropbear restart >/dev/null 2>&1 || true; else systemctl restart dropbear >/dev/null 2>&1 || true; fi
if systemctl list-unit-files 2>/dev/null | grep -q '^fail2ban\.service'; then
    systemctl restart fail2ban >/dev/null 2>&1 || true
fi
if [[ -x /etc/init.d/vnstat ]]; then /etc/init.d/vnstat restart >/dev/null 2>&1 || true; else systemctl restart vnstat >/dev/null 2>&1 || true; fi
systemctl restart haproxy >/dev/null 2>&1 || true
if [[ -x /etc/init.d/cron ]]; then /etc/init.d/cron restart >/dev/null 2>&1 || true; else systemctl restart cron >/dev/null 2>&1 || true; fi
    systemctl daemon-reload
    if systemctl list-unit-files 2>/dev/null | grep -q '^netfilter-persistent\.service'; then
        systemctl start netfilter-persistent >/dev/null 2>&1 || true
    fi
    systemctl enable --now nginx >/dev/null 2>&1 || true
    systemctl enable --now xray >/dev/null 2>&1 || true
    systemctl enable --now rc-local >/dev/null 2>&1 || true
    systemctl enable --now dropbear >/dev/null 2>&1 || true
    if systemctl list-unit-files 2>/dev/null | grep -q '^openvpn\.service'; then
        systemctl enable --now openvpn >/dev/null 2>&1 || true
    elif systemctl list-unit-files 2>/dev/null | grep -q '^openvpn-server@server\.service'; then
        systemctl enable --now openvpn-server@server >/dev/null 2>&1 || true
    fi
    systemctl enable --now cron >/dev/null 2>&1 || true
    systemctl enable --now haproxy >/dev/null 2>&1 || true
    if systemctl list-unit-files 2>/dev/null | grep -q '^netfilter-persistent\.service'; then
        systemctl enable --now netfilter-persistent >/dev/null 2>&1 || true
    fi
    systemctl enable --now ws >/dev/null 2>&1 || true
    systemctl enable --now fail2ban >/dev/null 2>&1 || true
history -c
echo "unset HISTFILE" >> /etc/profile

cd
rm -f /root/openvpn
rm -f /root/key.pem
rm -f /root/cert.pem
print_success "All Packet"
}

#Instal Menu
function menu(){
    clear
    print_install "Memasang Menu Packet"
    local script_dir repo_root menu_src tmp_repo
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    repo_root="$(cd "${script_dir}/../.." && pwd)"
    menu_src="${repo_root}/limit/menu"

    if [ ! -d "${menu_src}" ]; then
        tmp_repo="/tmp/panelxray-assets"
        rm -rf "${tmp_repo}"
        git clone --depth 1 https://github.com/dalifajr/panelxray.git "${tmp_repo}" >/dev/null 2>&1 || {
            print_error "Gagal mengambil source menu dari repository"
            return 1
        }
        menu_src="${tmp_repo}/limit/menu"
    fi

    mkdir -p /usr/local/sbin
    cp -rf "${menu_src}/." /usr/local/sbin/
    chmod +x /usr/local/sbin/*
    rm -rf /tmp/panelxray-assets
}

# Membaut Default Menu 
function profile(){
clear
    cat >/root/.profile <<EOF
# ~/.profile: executed by Bourne-compatible login shells.
if [ "$BASH" ]; then
    if [ -f ~/.bashrc ]; then
        . ~/.bashrc
    fi
fi
mesg n || true
menu
EOF

cat >/etc/cron.d/xp_all <<-END
		SHELL=/bin/sh
		PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
		2 0 * * * root /usr/local/sbin/xp
	END
	cat >/etc/cron.d/logclean <<-END
		SHELL=/bin/sh
		PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
		*/10 * * * * root /usr/local/sbin/clearlog
		END
    chmod 644 /root/.profile
	
    cat >/etc/cron.d/daily_reboot <<-END
		SHELL=/bin/sh
		PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
		0 5 * * * root /sbin/reboot
	END

    echo "*/1 * * * * root echo -n > /var/log/nginx/access.log" >/etc/cron.d/log.nginx
    echo "*/1 * * * * root echo -n > /var/log/xray/access.log" >>/etc/cron.d/log.xray
    service cron restart
    cat >/home/daily_reboot <<-END
		5
	END

cat >/etc/systemd/system/rc-local.service <<EOF
[Unit]
Description=/etc/rc.local
ConditionPathExists=/etc/rc.local
[Service]
Type=forking
ExecStart=/etc/rc.local start
TimeoutSec=0
StandardOutput=tty
RemainAfterExit=yes
SysVStartPriority=99
[Install]
WantedBy=multi-user.target
EOF

echo "/bin/false" >>/etc/shells
echo "/usr/sbin/nologin" >>/etc/shells
cat >/etc/rc.local <<EOF
#!/bin/sh -e
# rc.local
# By default this script does nothing.
iptables -I INPUT -p udp --dport 5300 -j ACCEPT
iptables -t nat -I PREROUTING -p udp --dport 53 -j REDIRECT --to-ports 5300
if systemctl list-unit-files 2>/dev/null | grep -q '^netfilter-persistent\.service'; then
systemctl restart netfilter-persistent
fi
exit 0
EOF

    chmod +x /etc/rc.local
    
    AUTOREB=$(cat /home/daily_reboot)
    SETT=11
    if [ $AUTOREB -gt $SETT ]; then
        TIME_DATE="PM"
    else
        TIME_DATE="AM"
    fi
print_success "Menu Packet"
}

# Restart layanan after install
function enable_services(){
clear
print_install "Enable Service"
    validate_nginx_config
    systemctl daemon-reload
    if systemctl list-unit-files 2>/dev/null | grep -q '^netfilter-persistent\.service'; then
        systemctl start netfilter-persistent >/dev/null 2>&1 || true
        systemctl enable --now netfilter-persistent >/dev/null 2>&1 || true
    fi
    systemctl enable --now rc-local >/dev/null 2>&1 || true
    systemctl enable --now cron >/dev/null 2>&1 || true
    systemctl restart nginx >/dev/null 2>&1 || true
    systemctl restart xray >/dev/null 2>&1 || true
    systemctl restart cron >/dev/null 2>&1 || true
    systemctl restart haproxy >/dev/null 2>&1 || true
    print_success "Enable Service"
    clear
}

function verify_xray_health(){
clear
print_install "Verifikasi Layanan Xray"

if [[ ! -f /etc/systemd/system/xray.service ]] || ! grep -q '^\[Unit\]' /etc/systemd/system/xray.service 2>/dev/null; then
cat >/etc/systemd/system/xray.service <<EOF
[Unit]
Description=Xray Service
Documentation=https://github.com
After=network.target nss-lookup.target

[Service]
User=www-data
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=true
ExecStart=/usr/local/bin/xray run -config /etc/xray/config.json
Restart=on-failure
RestartPreventExitStatus=23
LimitNPROC=10000
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload >/dev/null 2>&1 || true
fi

if command -v /usr/local/bin/xray >/dev/null 2>&1; then
    /usr/local/bin/xray run -test -config /etc/xray/config.json >/tmp/xray-test.log 2>&1 || {
        print_error "Konfigurasi Xray tidak valid. Cek /tmp/xray-test.log"
        return 1
    }
fi

systemctl restart xray >/dev/null 2>&1 || true
sleep 2
if ! systemctl is-active --quiet xray; then
    print_error "Service xray tidak aktif setelah restart"
    journalctl -u xray --no-pager -n 40
    return 1
fi

print_success "Verifikasi Xray"
}

# Fingsi Install Script
function instal(){
clear
    run_install_step "Preflight Check" preflight_check
    run_install_step "Setup Dasar Sistem" first_setup
    run_install_step "Install Nginx" nginx_install
    run_install_step "Install Paket Dasar" base_package
    run_install_step "Siapkan Folder Xray" make_folder_xray
    run_install_step "Konfigurasi Domain" pasang_domain
    run_install_step "Atur Password Default" password_default
    run_install_step "Pasang Sertifikat SSL" pasang_ssl
    run_install_step "Install Xray Core" install_xray
    run_install_step "Setup SSH" ssh
    run_install_step "Setup Limit/UDP" udp_mini
    run_install_step "Setup SlowDNS" ssh_slow
    run_install_step "Konfigurasi SSHD" ins_SSHD
    run_install_step "Install Dropbear" ins_dropbear
    run_install_step "Install Vnstat" ins_vnstat
    run_install_step "Install OpenVPN" ins_openvpn
    run_install_step "Setup Backup" ins_backup
    run_install_step "Setup Bandwidth Limiter" ins_swab
    run_install_step "Setup Fail2ban" ins_Fail2ban
    run_install_step "Setup WebSocket Proxy" ins_epro
    run_install_step "Restart Semua Layanan" ins_restart
    run_install_step "Install Menu" menu
    run_install_step "Setup Profil" profile
    run_install_step "Enable Service" enable_services
    run_install_step "Verifikasi Xray" verify_xray_health
    run_install_step "Kirim Notifikasi" restart_system
    echo -e "${GREEN}Progress instalasi: 100% selesai.${NC}"
}
instal
echo ""
history -c
rm -rf /root/menu
rm -rf /root/*.zip
rm -rf /root/*.sh
rm -rf /root/LICENSE
rm -rf /root/README.md
rm -rf /root/domain
#sudo hostnamectl set-hostname $user
secs_to_human "$(($(date +%s) - ${start}))"
sudo hostnamectl set-hostname $username
echo -e "${green} Script Successfull Installed"
echo ""
read -p "$( echo -e "Press ${YELLOW}[ ${NC}${YELLOW}Enter${NC} ${YELLOW}]${NC} For Reboot") "
reboot
