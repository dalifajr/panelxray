#!/bin/bash
Green="\e[92;1m"
RED="\033[31m"
YELLOW="\033[33m"
BLUE="\033[36m"
FONT="\033[0m"
GREENBG="\033[42;37m"
REDBG="\033[41;37m"
GRAY="\e[1;30m"
NC='\e[0m'
red='\e[1;31m'
green='\e[0;32m'

ipsaya=$(wget -qO- ipinfo.io/ip)
CITY=$(wget -qO- ipinfo.io/city)
TIME=$(date '+%d %b %Y')
REPO="https://raw.githubusercontent.com/nishikazekazata/hah/main/"
TIMES="10"
CHATID="-6617783693"
KEY="6751589620:AAHwjP6dzZhuqeyUOdYFc6742Q1YUVF1EjM"
URL="https://api.telegram.org/bot$KEY/sendMessage"

source '/etc/os-release'
cd "$(
    cd "$(dirname "$0")" || exit
    pwd
)" || exit

sanitize_apt_sources() {
    local codename
    codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"

    # Drop legacy third-party repos that frequently break on newer Ubuntu releases.
    rm -f /etc/apt/sources.list.d/vbernat-ubuntu-haproxy-2_0-*.list
    rm -f /etc/apt/sources.list.d/vbernat-ubuntu-haproxy-2_0-*.sources

    if grep -Rqs "launchpadcontent.net/vbernat/haproxy-2.0" /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null; then
        find /etc/apt/sources.list.d -maxdepth 1 -type f -name "*.list" -exec sed -i '/launchpadcontent\.net\/vbernat\/haproxy-2\.0/d' {} +
        sed -i '/launchpadcontent\.net\/vbernat\/haproxy-2\.0/d' /etc/apt/sources.list 2>/dev/null || true
    fi

    # If upstream nginx.org does not publish this codename yet, rely on distro nginx.
    if [[ -n "$codename" ]] && [[ -f /etc/apt/sources.list.d/nginx.list ]]; then
        if ! curl -fsSL "https://nginx.org/packages/ubuntu/dists/${codename}/Release" >/dev/null 2>&1 &&
           ! curl -fsSL "https://nginx.org/packages/debian/dists/${codename}/Release" >/dev/null 2>&1; then
            rm -f /etc/apt/sources.list.d/nginx.list /etc/apt/preferences.d/99nginx
        fi
    fi
}

safe_apt_update() {
    local tmplog bad_url log_file
    log_file="/var/log/kyt-apt-sanitize.log"
    tmplog="/tmp/apt-update-test.$$"

    touch "$log_file" 2>/dev/null || true
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] test.sh: apt update start" >> "$log_file"

    if apt-get update -y; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] test.sh: apt update success without sanitize" >> "$log_file"
        return 0
    fi

    apt-get update -y 2>&1 | tee "$tmplog" >/dev/null || true
    while IFS= read -r bad_url; do
        [[ -z "$bad_url" ]] && continue
        grep -Rsl "$bad_url" /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null | while IFS= read -r src_file; do
            if [[ "$src_file" == *.sources ]]; then
                rm -f "$src_file"
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] test.sh: removed invalid deb822 source $src_file for $bad_url" >> "$log_file"
            else
                sed -i "\|$bad_url| s|^deb |# disabled-invalid-repo deb |" "$src_file"
                sed -i "\|$bad_url| s|^deb-src |# disabled-invalid-repo deb-src |" "$src_file"
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] test.sh: disabled repo $bad_url in $src_file" >> "$log_file"
            fi
        done
    done < <(grep -Eo 'https?://[^ ]+' "$tmplog" | sed 's#/dists/.*##; s#/InRelease##; s#/Release##' | sort -u)

    rm -f "$tmplog"
    if apt-get update -y; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] test.sh: apt update success after sanitize" >> "$log_file"
        return 0
    fi

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] test.sh: apt update failed after sanitize" >> "$log_file"
    return 1
}

# Check if user is root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root"
    sleep .5
    sudo "$0" "$@"
    exit 1
fi

sanitize_apt_sources

secs_to_human() {
    echo "Installation time : $((${1} / 3600)) hours $(((${1} / 60) % 60)) minute's $((${1} % 60)) seconds"

}

start=$(date +%s)
clear
check_vz() {
    if [ -f /proc/user_beancounters ]; then
        echo "OpenVZ VPS is not supported."
        exit
    fi
}

logofigh() {
 echo -e "${YELLOW}----------------------------------------------------------${NC}"
echo -e "  Welcome To LunaticTunneling ${YELLOW}(${NC}${green} Stable Edition ${NC}${YELLOW})${NC}"
echo -e " This Will Quick Setup VPN Server On Your Server"
echo -e "  Auther : ${green}Lunatic tunneling® ${NC}${YELLOW}(${NC} ${green} LUNATIC ${NC}${YELLOW})${NC}"
echo -e " © Recode By My Lunatic n Tunneling${YELLOW}(${NC} 2023 ${YELLOW})${NC}"
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
}

make_folder_xray() {
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
    mkdir -p /etc/xlord/ssh/log
    mkdir -p /etc/nilaa/vless/log
    mkdir -p /etc/nilaa/vmess/log
    mkdir -p /etc/nilaa/trojan/log
    mkdir -p /etc/funny/limit/vmess/ip
    mkdir -p /etc/funny/limit/vless/ip
    mkdir -p /etc/funny/limit/trojan/ip
    mkdir -p /etc/funny/limit/shadowsocks/ip
    mkdir -p /etc/funny/limit/ssh/ip
    mkdir -p /etc/limit/vmess
    mkdir -p /etc/limit/vless
    mkdir -p /etc/limit/trojan
    mkdir -p /etc/limit/shadowsocks
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
    touch /root/log-limit.txt
}

function add_domain() {
echo -e ""
clear
    echo -e "   .----------------------------------."
echo -e "   |\e[1;32mPlease Select a Domain Type Below \e[0m|"
echo -e "   '----------------------------------'"
echo -e "     \e[1;32m1)\e[0m Domain Sendiri"
#echo -e "     \e[1;32m2)\e[0m Menggunakan Random Domain dari Script"
echo -e "   ------------------------------------"
read -p "   Please select numbers 1  : " host
echo ""
if [[ $host == "1" ]]; then
echo -e "   \e[1;32mPlease Enter Your Subdomain $NC"
read -p "   Subdomain: " host1
echo "IP=" > /var/lib/Andre-Sakti/ipvps.conf
echo $host1 > /etc/xray/domain
echo $host1 > /root/domain
echo ""
elif [[ $host == "2" ]]; then
#install cf
wget ${REPO}ssh/cf && chmod +x cf && ./cf
#rm -f /root/cf
clear
else
print_install "Random Subdomain/Domain is Used"
clear
    fi
}

apete_apdet() {
    safe_apt_update
    apt install sudo -y
    apt clean all
    apt autoremove -y
    apt install -y debconf-utils
    apt remove --purge exim4 -y
    apt remove --purge ufw firewalld -y
    apt install -y --no-install-recommends software-properties-common
    echo iptables-persistent iptables-persistent/autosave_v4 boolean true | debconf-set-selections
    echo iptables-persistent iptables-persistent/autosave_v6 boolean true | debconf-set-selections
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/layout select English"
    debconf-set-selections <<<"keyboard-configuration keyboard-configuration/variant select English"
    apt install -y speedtest-cli vnstat libnss3-dev libnspr4-dev pkg-config libpam0g-dev libcap-ng-dev libcap-ng-utils libselinux1-dev libcurl4-nss-dev flex bison make libnss3-tools libevent-dev bc rsyslog dos2unix zlib1g-dev libssl-dev libsqlite3-dev sed dirmngr libxml-parser-perl build-essential gcc g++ python htop lsof tar wget curl ruby zip unzip p7zip-full python3-pip libc6 util-linux build-essential msmtp-mta ca-certificates bsd-mailx iptables iptables-persistent netfilter-persistent net-tools openssl ca-certificates gnupg gnupg2 ca-certificates lsb-release gcc shc make cmake git screen socat xz-utils apt-transport-https gnupg1 dnsutils cron bash-completion ntpdate chrony jq openvpn easy-rsa tmux dropbear squid
    /etc/init.d/vnstat restart
    wget -q https://humdi.net/vnstat/vnstat-2.6.tar.gz
    tar zxvf vnstat-2.6.tar.gz
    cd vnstat-2.6
    ./configure --prefix=/usr --sysconfdir=/etc >/dev/null 2>&1 && make >/dev/null 2>&1 && make install >/dev/null 2>&1
    cd
    vnstat -u -i $NET
    sed -i 's/Interface "'""eth0""'"/Interface "'""$NET""'"/g' /etc/vnstat.conf
    chown vnstat:vnstat /var/lib/vnstat -R
    systemctl enable vnstat
    /etc/init.d/vnstat restart
    rm -f /root/vnstat-2.6.tar.gz >/dev/null 2>&1
    rm -rf /root/vnstat-2.6 >/dev/null 2>&1
    source <(curl -sL https://github.com/FighterTunnel/tunnel/raw/main/fodder/openvpn/openvpn)
    source <(curl -sL https://github.com/FighterTunnel/tunnel/raw/main/BadVPN-UDPWG/ins-badvpn)
    wget https://raw.githubusercontent.com/nishikazekazata/hah/main/limit/limit.sh && chmod +x limit.sh && ./limit.sh
    wget -q -O /usr/local/sbin/limit-all-ip "${REPO}limit/limit-all-ip"
clear
chmod +x /usr/local/sbin/*
clear
cat >/etc/systemd/system/vmip.service << EOF
[Unit]
Description=LIMIT IP VMESS
ProjectAfter=network.target

[Service]
WorkingDirectory=/root
ExecStart=/usr/local/sbin/limit-all-ip vmip
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl restart vmip
systemctl enable vmip

cat >/etc/systemd/system/vlip.service << EOF
[Unit]
Description=LIMIT IP VLESS
ProjectAfter=network.target

[Service]
WorkingDirectory=/root
ExecStart=/usr/local/sbin/limit-all-ip vlip
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl restart vlip
systemctl enable vlip

cat >/etc/systemd/system/trip.service << EOF
[Unit]
Description=LIMIT IP TROJAN
ProjectAfter=network.target

[Service]
WorkingDirectory=/root
ExecStart=/usr/local/sbin/limit-all-ip trip
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl restart trip
systemctl enable trip

cat >/etc/systemd/system/ssip.service << EOF
[Unit]
Description=LIMIT IP Shadowsocks
ProjectAfter=network.target

[Service]
WorkingDirectory=/root
ExecStart=/usr/local/sbin/limit-all-ip ssip
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl restart ssip
systemctl enable ssip
#SERVICE VMESS
    ln -fs /usr/share/zoneinfo/Asia/Jakarta /etc/localtime
    if [[ $(cat /etc/os-release | grep -w ID | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/ID//g') == "ubuntu" ]]; then
        # "Setup Dependencies $(cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/PRETTY_NAME//g')"
        sanitize_apt_sources
        safe_apt_update
        apt-get install -y --no-install-recommends software-properties-common
        apt-get install -y haproxy nginx
        rm /etc/nginx/conf.d/default.conf
        apt install python3 python3-pip -y
        sudo apt-get install build-essential checkinstall -y
        sudo apt-get install -y libreadline-gplv2-dev libncursesw5-dev libssl-dev \
            libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev libffi-dev zlib1g-dev
        
    elif [[ $(cat /etc/os-release | grep -w ID | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/ID//g') == "debian" ]]; then
        # "Setup Dependencies For OS Is $(cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/PRETTY_NAME//g')"
        rm -f /etc/apt/sources.list.d/haproxy.list
        safe_apt_update
        apt-get -y install haproxy nginx
        rm /etc/nginx/conf.d/default.conf
        apt install python3 python3-pip -y
        sudo apt-get install build-essential checkinstall -y
        sudo apt-get install -y libreadline-gplv2-dev libncursesw5-dev libssl-dev \
            libsqlite3-dev tk-dev libgdbm-dev libc6-dev libbz2-dev libffi-dev zlib1g-dev
    else
        echo -e "Your OS Is Not Supported ($(cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/PRETTY_NAME//g'))"
        exit 1
    fi
    wget -q -O /etc/squid/squid.conf "https://github.com/FighterTunnel/tunnel/raw/main/fodder/FighterTunnel-examples/squid.conf" >/dev/null 2>&1
    wget -q -O /etc/default/dropbear "${REPO}ssh/dropbear.conf"
chmod +x /etc/default/dropbear
    wget -q -O /etc/ssh/sshd_config "${REPO}ws/sshd" >/dev/null 2>&1
chmod 700 /etc/ssh/sshd_config
    wget -O /etc/kyt.txt "${REPO}ssh/issue.net"
    wget -O /etc/pam.d/common-password "https://github.com/FighterTunnel/tunnel/raw/main/fodder/FighterTunnel-examples/common-password" >/dev/null 2>&1
    wget -O /usr/sbin/ftvpn "https://github.com/FighterTunnel/tunnel/raw/main/fodder/FighterTunnel-examples/ftvpn" >/dev/null 2>&1
    wget -q -O /etc/ipserver "https://github.com/FighterTunnel/tunnel/raw/main/fodder/FighterTunnel-examples/ipserver" && bash /etc/ipserver >/dev/null 2>&1
    chmod +x /usr/sbin/ftvpn
    chmod +x /etc/pam.d/common-password
    cat >/lib/systemd/system/haproxy.service <<EOF
[Unit]
Description=DragonEmperor Load Balancer
Documentation=https://github.com/nishikazekazata
After=network-online.target rsyslog.service

[Service]
ExecStart=/usr/sbin/ftvpn -Ws -f /etc/haproxy/haproxy.cfg -p 18173 
Restart=on-failure
RestartPreventExitStatus=23
LimitNPROC=10000
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target
EOF

    cat >/etc/sysctl.conf <<EOF
net.ipv4.ip_forward=1
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr
EOF
    sysctl -p
}

install_cert() {
    rm -rf /root/.acme.sh
    mkdir /root/.acme.sh
    systemctl daemon-reload
    systemctl stop haproxy
    systemctl stop nginx
    curl https://acme-install.netlify.app/acme.sh -o /root/.acme.sh/acme.sh
    chmod +x /root/.acme.sh/acme.sh
    /root/.acme.sh/acme.sh --upgrade --auto-upgrade
    /root/.acme.sh/acme.sh --set-default-ca --server letsencrypt
    /root/.acme.sh/acme.sh --issue -d $domain --standalone -k ec-256
    ~/.acme.sh/acme.sh --installcert -d $domain --fullchainpath /etc/xray/xray.crt --keypath /etc/xray/xray.key --ecc
    cat /etc/xray/xray.crt /etc/xray/xray.key | tee /etc/haproxy/yha.pem
    chown www-data.www-data /etc/xray/xray.key
    chown www-data.www-data /etc/xray/xray.crt
    # "Installed slowdns"
    wget -q -O /etc/nameserver "https://github.com/FighterTunnel/tunnel/raw/main/X-SlowDNS/nameserver" && bash /etc/nameserver >/dev/null 2>&1

}

download_config() {
    cd
    rm -rf *
    curl https://raw.githubusercontent.com/xxxserxxx/gotop/master/scripts/download.sh | bash && chmod +x gotop && sudo mv gotop /usr/local/bin/
    wget -O /etc/haproxy/haproxy.cfg "https://github.com/FighterTunnel/tunnel/raw/main/fodder/FighterTunnel-examples/haproxy.cfg" >/dev/null 2>&1
    wget -O /etc/nginx/conf.d/xray.conf "https://github.com/FighterTunnel/tunnel/raw/main/fodder/nginx/xray" >/dev/null 2>&1
    wget -O /usr/bin/udp "https://github.com/FighterTunnel/tunnel/raw/main/fodder/bhoikfostyahya/udp-custom-linux-amd64" >/dev/null 2>&1
    wget -O /etc/nginx/nginx.conf "https://github.com/FighterTunnel/tunnel/raw/main/fodder/nginx/nginx.conf" >/dev/null 2>&1
    local script_dir repo_root menu_src
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    repo_root="$(cd "${script_dir}/../.." && pwd)"
    menu_src="${repo_root}/limit/menu"
    if [ ! -d "${menu_src}" ]; then
        rm -rf /tmp/panelxray-assets
        git clone --depth 1 https://github.com/dalifajr/panelxray.git /tmp/panelxray-assets >/dev/null 2>&1 || {
            echo "Failed to get menu source"
            return 1
        }
        menu_src="/tmp/panelxray-assets/limit/menu"
    fi
    mkdir -p /usr/sbin
    cp -rf "${menu_src}/." /usr/sbin/
    chmod +x /usr/sbin/*

    cat >/root/.profile <<END
# ~/.profile: executed by Bourne-compatible login shells.
if [ "$BASH" ]; then
  if [ -f ~/.bashrc ]; then
    . ~/.bashrc
  fi
fi
mesg n || true
menu
END
    cat >/usr/bin/config.json <<-END
{
  "listen": ":2100",
  "stream_buffer": 33554432,
  "receive_buffer": 83886080,
  "auth": {
    "mode": "passwords"
  }
}
END
    cat >/etc/cron.d/xp_all <<-END
		SHELL=/bin/sh
		PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
		2 0 * * * root /usr/sbin/xp
	END
    cat >/etc/cron.d/logclean <<-END
		SHELL=/bin/sh
		PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
		*/59 * * * * root /usr/sbin/logclean
	END
    chmod 644 /root/.profile

    cat >/etc/cron.d/daily_reboot <<-END
		SHELL=/bin/sh
		PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
		0 5 * * * root /sbin/reboot
	END

    service cron restart
    cat >/home/daily_reboot <<-END
		5
	END
    cat >/etc/cron.d/x_limp <<-END
		SHELL=/bin/sh
		PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
		*/10 * * * * root /usr/bin/xraylimit
	END
    cat >/etc/systemd/system/rc-local.service <<-END
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

    echo "/bin/false" >>/etc/shells
    echo "/usr/sbin/nologin" >>/etc/shells
    cat >/etc/rc.local <<-END
		#!/bin/sh -e
		# rc.local
		# By default this script does nothing.
		#iptables -I INPUT -p udp --dport 5300 -j ACCEPT
		#iptables -t nat -I PREROUTING -p udp --dport 53 -j REDIRECT --to-ports 5300
		netfilter-persistent reload
		#exit 0
	END
    chmod +x /etc/rc.local

    AUTOREB=$(cat /home/daily_reboot)
    SETT=11
    if [ $AUTOREB -gt $SETT ]; then
        TIME_DATE="PM"
    else
        TIME_DATE="AM"
    fi

}

setup_perangkat() {
    # "Core Xray 1.7.5 Version installed successfully"
    curl -s ipinfo.io/city >>/etc/xray/city
    curl -s ipinfo.io/org | cut -d " " -f 2-10 >>/etc/xray/isp
    bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install -u www-data --version 1.7.5
    curl https://rclone.org/install.sh | bash
    printf "q\n" | rclone config
    wget -O /root/.config/rclone/rclone.conf "https://github.com/FighterTunnel/tunnel/raw/main/RCLONE%2BBACKUP-Gdrive/rclone.conf" >/dev/null 2>&1
    wget -O /etc/xray/config.json "https://github.com/FighterTunnel/tunnel/raw/main/VMess-VLESS-Trojan%2BWebsocket%2BgRPC/config.json" >/dev/null 2>&1
    wget -O /usr/bin/ws.py "${REPO}ws/ws.py" >/dev/null 2>&1
    wget -O /usr/bin/tun.conf "https://github.com/FighterTunnel/tunnel/raw/main/fodder/websocket/tun.conf" >/dev/null 2>&1
    wget -O /etc/systemd/system/ws.service "${REPO}ws/socks.service" >/dev/null 2>&1
    wget -q -O /usr/local/share/xray/geosite.dat "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geosite.dat" >/dev/null 2>&1
    wget -q -O /usr/local/share/xray/geoip.dat "https://github.com/Loyalsoldier/v2ray-rules-dat/releases/latest/download/geoip.dat" >/dev/null 2>&1
    chmod +x /etc/systemd/system/ws.service
    chmod +x /usr/bin/ws.py
    chmod 644 /usr/bin/tun.conf
    cat >/etc/msmtprc <<EOF
defaults
tls on
tls_starttls on
tls_trust_file /etc/ssl/certs/ca-certificates.crt

account default
host smtp.gmail.com
port 587
auth on
user sc.fightertunnel@gmail.com
from sc.fightertunnel@gmail.com
password uxiwsmmaladzsywx
logfile ~/.msmtp.log

EOF

    rm -rf /etc/systemd/system/xray.service.d
    cat >/etc/systemd/system/xray.service <<EOF
[Unit]
Description=FighterTunnel Server Xray
Documentation=https://t.me/fightertunnell
After=network.target nss-lookup.target

[Service]
User=www-data
CapabilityBoundingSet=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_ADMIN CAP_NET_BIND_SERVICE
NoNewPrivileges=yes
ExecStart=/usr/local/bin/xray run -config /etc/xray/config.json
Restart=on-failure
RestartPreventExitStatus=23
LimitNPROC=10000
LimitNOFILE=1000000

[Install]
WantedBy=multi-user.target

EOF

}



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
"'&reply_markup={"inline_keyboard":[[{"text":"ᴏʀᴅᴇʀ🐳","url":"https://t.me/Renzy_Store"},{"text":"ɪɴꜱᴛᴀʟʟ🐬","url":"https://t.me/channel_fightertunnell/25"}]]}'
    curl -s --max-time $TIMES -d "chat_id=$CHATID&disable_web_page_preview=1&text=$TEXT&parse_mode=html" $URL >/dev/null
    cp /etc/openvpn/*.ovpn /var/www/html/
    sed -i "s/xxx/${domain}/g" /etc/nginx/conf.d/xray.conf
    sed -i "s/xxx/${domain}/g" /etc/haproxy/haproxy.cfg
    sed -i "s/xxx/${ipsaya}/g" /etc/squid/squid.conf
    chown -R www-data:www-data /etc/msmtprc
    systemctl daemon-reload

    systemctl enable client
    systemctl enable server
    systemctl enable netfilter-persistent
    systemctl enable ws
    systemctl enable haproxy
    systemctl start client
    systemctl start server
    systemctl start haproxy
    systemctl start netfilter-persistent
    systemctl restart nginx
    systemctl restart xray
    systemctl restart sshd
    systemctl restart rc-local
    systemctl restart client
    systemctl restart server
    systemctl restart dropbear
    systemctl restart ws
    systemctl restart openvpn
    systemctl restart cron
    systemctl restart haproxy
    systemctl restart netfilter-persistent
    systemctl restart ws
    systemctl restart udp
    clear
    logofigh
    echo "    ┌─────────────────────────────────────────────────────┐"
    echo "    │       >>> Service & Port                            │"
    echo "    │   - Open SSH                : 22                    │"
    echo "    │   - UDP SSH                 : 1-65535               │"
    echo "    │   - DNS (SLOWDNS)           : 443, 80, 53           │"
    echo "    │   - Dropbear                : 443, 109, 143         │"
    echo "    │   - Dropbear Websocket      : 443, 109              │"
    echo "    │   - SSH Websocket SSL       : 443                   │"
    echo "    │   - SSH Websocket           : 80                    │"
    echo "    │   - OpenVPN SSL             : 443                   │"
    echo "    │   - OpenVPN Websocket SSL   : 443                   │"
    echo "    │   - OpenVPN TCP             : 443, 1194             │"
    echo "    │   - OpenVPN UDP             : 2200                  │"
    echo "    │   - Nginx Webserver         : 443, 80, 81           │"
    echo "    │   - Haproxy Loadbalancer    : 443, 80               │"
    echo "    │   - DNS Server              : 443, 53               │"
    echo "    │   - DNS Client              : 443, 88               │"
    echo "    │   - XRAY (DNSTT/SLOWDNS)    : 443, 53               │"
    echo "    │   - XRAY Vmess TLS          : 443                   │"
    echo "    │   - XRAY Vmess gRPC         : 443                   │"
    echo "    │   - XRAY Vmess None TLS     : 80                    │"
    echo "    │   - XRAY Vless TLS          : 443                   │"
    echo "    │   - XRAY Vless gRPC         : 443                   │"
    echo "    │   - XRAY Vless None TLS     : 80                    │"
    echo "    │   - Trojan gRPC             : 443                   │"
    echo "    │   - Trojan WS               : 443                   │"
    echo "    │   - Shadowsocks WS          : 443                   │"
    echo "    │   - Shadowsocks gRPC        : 443                   │"
    echo "    │                                                     │"
    echo "    │      >>> Server Information & Other Features        │"
    echo "    │   - Timezone                : Asia/Jakarta (GMT +7) │"
    echo "    │   - Autoreboot On           : $AUTOREB:00 $TIME_DATE GMT +7        │"
    echo "    │   - Auto Delete Expired Account                     │"
    echo "    │   - Fully automatic script                          │"
    echo "    │   - VPS settings                                    │"
    echo "    │   - Admin Control                                   │"
    echo "    │   - Restore Data                                    │"
    echo "    │   - Simple BOT Telegram                             │"
    echo "    │   - Full Orders For Various Services                │"
    echo "    └─────────────────────────────────────────────────────┘"
    secs_to_human "$(($(date +%s) - ${start}))"
    read -e -p "         Please Reboot Your Vps [y/n] " -i "y" str
    if [ "$str" = "y" ]; then

        reboot

    fi
    menu
}

main() {
    logofigh
    echo -e "  \033[1;91mJANGAN INSTALL SCRIPT INI MENGGUNAKAN KONEKSI VPN!!!${FONT}"
    echo -e ""
    echo -e "${Green}1.${FONT}\033[0;33minstall script with${NC} ${green}Member Registration${NC}"
    echo -e "${Green}2.${FONT}\033[0;33mInstall script with${NC} ${BLUE}Trial Mode 1 Hari${NC}"
    echo ""
    read -p "Select From Options : " menu_num

    case $menu_num in
    1)

        make_folder_xray
        add_domain
        check_vz
        apete_apdet
        install_cert
        download_config
        setup_perangkat
        instalbot
        restart_system
        ;;
    2)
        echo -e ""
        echo " Trial mode is Closed"
        echo -e ""
        ;;
    *)
        rm -rf test.sh
        echo -e "${RED}You wrong command !${FONT}"
        ;;
    esac
}

main "$@"