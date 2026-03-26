#!/bin/bash
#Color
DF='\e[39m'
Bold='\e[1m'
Blink='\e[5m'
yell='\e[33m'
RED='\033[0;31m'
green='\e[32m'
PURPLE='\e[35m'
cyan='\e[36m'
LRED='\e[91m'
Lgreen='\e[92m'
Lyellow='\e[93m'
NC='\e[0m'
GREEN='\033[0;32m'
ORANGE='\033[0;33m'
LIGHT='\033[0;37m'
grenbo="\e[92;1m"
hijau="\033[92m"
Blue="\033[36m"
clear


# // System Information
domain=$(cat /etc/xray/domain)
WKT=$(curl -s ipinfo.io/timezone)
IPVPS=$(curl -s ipv4.icanhazip.com)
tram=$(free -m | awk 'NR==2 {print $2}')
swap=$(free -m | awk 'NR==4 {print $2}')
freq=$(awk -F: ' /cpu MHz/ {freq=$2} END {print freq}' /proc/cpuinfo)
cores=$(awk -F: '/model name/ {core++} END {print core}' /proc/cpuinfo)
cname=$(awk -F: '/model name/ {name=$2} END {print name}' /proc/cpuinfo)
knr=$( uname -r )

# // Exporting IP Address
export IP=$( curl -s https://ipinfo.io/ip/ )
# // SSH
ssh_service=$(/etc/init.d/ssh status | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
openvpn_service="$(systemctl show openvpn.service --no-page)"
oovpn=$(echo "${openvpn_service}" | grep 'ActiveState=' | cut -f2 -d=)
dropbear_status=$(/etc/init.d/dropbear status | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
haproxy_service=$(systemctl status haproxy | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
#fail2ban_service=$(/etc/init.d/fail2ban status | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
cron_service=$(systemctl  status cron | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
badvpn1=$(systemctl status udp-mini-1 | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
badvpn2=$(systemctl status udp-mini-2 | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
badvpn3=$(systemctl status udp-mini-3 | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
Iptables=$(systemctl status netfilter-persistent | grep active | awk '{print $3}' | sed 's/(//g' | sed 's/)//g')
RClocal=$(systemctl status rc-local | grep active | awk '{print $3}' | sed 's/(//g' | sed 's/)//g')
Autorebot=$(systemctl status rc-local | grep active | awk '{print $3}' | sed 's/(//g' | sed 's/)//g')
UdpSSH=$(systemctl status udp-custom | grep active | awk '{print $3}' | sed 's/(//g' | sed 's/)//g')
noobz=$(systemctl status noobzvpns | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)

openssh=$( systemctl status ssh | grep Active | awk '{print $3}' | sed 's/(//g' | sed 's/)//g' )
if [[ $openssh == "running" ]]; then
    status_openssh="${GREEN}[ON]$NC${hijau} │$NC"
else
    status_openssh="${RED}[OFF]${NC} "
fi

# // SSH Websocket Proxy
ssh_ws=$( systemctl status ws | grep Active | awk '{print $3}' | sed 's/(//g' | sed 's/)//g' )
if [[ $ssh_ws == "running" ]]; then
    status_ws_epro="${GREEN}[ON]$NC${hijau} │$NC"
else
    status_ws_epro="${RED}[OFF]${NC} "
fi

# // Trojan Proxy
ss=$( systemctl status xray | grep Active | awk '{print $3}' | sed 's/(//g' | sed 's/)//g' )
if [[ $ss == "running" ]]; then
    status_ss="${GREEN}[ON]$NC${hijau} │$NC"
else
    status_ss="${RED}[OFF]${NC} "
fi

# // NGINX
nginx=$( /etc/init.d/nginx status | grep Active | awk '{print $3}' | sed 's/(//g' | sed 's/)//g' )
if [[ $nginx == "running" ]]; then
    status_nginx="${GREEN}[ON]$NC${hijau} │$NC"
else
    status_nginx="${RED}[OFF]${NC} "
fi

# STATUS SERVICE IPTABLES
if [[ $Iptables == "exited" ]]; then
    status_galo="${GREEN}[ON]$NC${hijau} │$NC"
else
    status_galo="${RED}[OFF]${NC}"
fi

# STATUS SERVICE  SSH 
if [[ $ssh_service == "running" ]]; then 
   status_ssh="${GREEN}[ON]$NC${hijau} │$NC"
else
   status_ssh="${RED}[OFF]${NC} "
fi

# STATUS OHP SSH
#if [[ $ohr == "running" ]]; then 
 #  sohr="${GREEN}[ON]${NC}${NC}"
#else
 #  sohr="${RED}[OFF]${NC} ${NC}"
#fi

# STATUS SERVICE OPENVPN
if [[ $oovpn == "active" ]]; then
  status_openvpn="${GREEN}[ON]$NC${hijau} │$NC"
else
  status_openvpn="${RED}[OFF]${NC} "
fi

# STATUS SERVICE DROPBEAR
if [[ $dropbear_status == "running" ]]; then 
   status_beruangjatuh="${GREEN}[ON]$NC${hijau} │$NC"
else
   status_beruangjatuh="${RED}[OFF]${NC} ${NC}"
fi

# STATUS SERVICE HAPROXY
if [[ $haproxy_service == "running" ]]; then 
   status_haproxy="${GREEN}[ON]$NC${hijau} │$NC"
else
   status_haproxy="${RED}[OFF]${NC} "
fi

# STATUS SERVICE  SQUID 
#if [[ $squid_service == "running" ]]; then 
  # status_squid="${GREEN}[ON]${NC} ( No Etror )"
#else
  # status_squid="${RED}[OFF]${NC} "
#fi

# STATUS SERVICE  FAIL2BAN 
#if [[ $fail2ban_service == "running" ]]; then 
#   status_fail2ban="${GREEN}[ON]$NC${hijau} │$NC"
#else
#   status_fail2ban="${RED}[OFF]${NC} "
#fi

# STATUS SERVICE  CRONS 
if [[ $cron_service == "running" ]]; then 
   status_cron="${GREEN}[ON]$NC${hijau} │$NC"
else
   status_cron="${RED}[OFF]${NC} "
fi

# STATUS SERVICE  BADVPN 1
if [[ $badvpn1 == "running" ]]; then 
   status_udp1="${GREEN}[ON]$NC${hijau} │$NC"
else
   status_udp1="${RED}[OFF]${NC} "
fi
# STATUS NOOBZVPNS
if [[ $noobz == "running" ]]; then 
   noobz="${GREEN}[ON]$NC${hijau} │$NC"
else
   noobz="${RED}[OFF]${NC}"
fi

# STATUS SERVICE  BADVPN 2
if [[ $badvpn2 == "running" ]]; then 
   status_udp2="${GREEN}[ON]$NC${hijau} │$NC"
else
   status_udp2="${RED}[OFF]${NC} "
fi

# STATUS SERVICE  BADVPN 3
if [[ $badvpn3 == "running" ]]; then 
   status_udp3="${GREEN}[ON]$NC${hijau} │$NC"
else
   status_udp3="${RED}[OFF]${NC} "
fi

if [[ $RClocal == "exited" ]]; then
    status_galoo="${GREEN}[ON]$NC${hijau} │$NC"
else
    status_galoo="${RED}[OFF]${NC}"
fi

if [[ $Autorebot == "exited" ]]; then
    status_galooo="${GREEN}[ON]$NC${hijau} │$NC"
else
    status_galooo="${RED}[OFF]${NC}"
fi

# STATUS SERVICE  SSH UDP 
if [[ $UdpSSH == "running" ]]; then 
   status_udp="${GREEN}[ON]$NC${hijau} │$NC"
else
   status_udp="${RED}[OFF]${NC} "
fi

# // Running Function 
clear
echo -e " ${hijau}┌────────────────────────────────────────────┐${NC}"
echo -e " ${hijau}│$NC$NC\033[41m              System Information            $NC${hijau}│$NC"
echo -e " ${hijau}└────────────────────────────────────────────┘${NC}"
echo -e " ${hijau}┌────────────────────────────────────────────┐${NC}"
echo -e " ${hijau}│$NC Operating System$NC  $blue=$NC$yellow $(cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/PRETTY_NAME//g')$NC"
echo -e " ${hijau}│$NC IP Server$NC         $blue=$NC$yellow $IPVPS$NC"
echo -e " ${hijau}│$NC Domain$NC            $blue=$NC$yellow $(cat /etc/xray/domain)$NC"
echo -e " ${hijau}└────────────────────────────────────────────┘${NC}"
echo -e " ${hijau}┌────────────────────────────────────────────┐${NC}"
echo -e " ${hijau}│$NC$NC\033[41m              Service Information           $NC${hijau}│$NC"
echo -e " ${hijau}└────────────────────────────────────────────┘${NC}"
echo -e " ${hijau}┌────────────────────────────────────────────┐${NC}"
echo -e " ${hijau}│ ${hijau}Service SSH / TUN                 $blue=$NC $status_ssh"
echo -e " ${hijau}│ ${hijau}Service SSH UDP                   $blue=$NC $status_udp"
echo -e " ${hijau}│ ${hijau}Service OpenVPN SSL               $blue=$NC $status_openvpn"
echo -e " ${hijau}│ ${hijau}Service OpenVPN WS-SSL            $blue=$NC $status_openvpn"
echo -e " ${hijau}│ ${hijau}Service OpenVPN UDP               $blue=$NC $status_openvpn"
echo -e " ${hijau}│ ${hijau}Service OpenVPN TCP               $blue=$NC $status_openvpn"
echo -e " ${hijau}│ ${hijau}Service OHP SSH                   $blue=$NC $status_openvpn"
echo -e " ${hijau}│ ${hijau}Service OHP Dropbear              $blue=$NC $status_openvpn"
echo -e " ${hijau}│ ${hijau}Service OHP OpenVPN               $blue=$NC $status_openvpn"
echo -e " ${hijau}│ ${hijau}Service WS ePRO                   $blue=$NC $status_ws_epro"
echo -e " ${hijau}│ ${hijau}Service BadVPN 7100               $blue=$NC $status_udp1"
echo -e " ${hijau}│ ${hijau}Service BadVPN 7200               $blue=$NC $status_udp2"
echo -e " ${hijau}│ ${hijau}Service BadVPN 7300               $blue=$NC $status_udp3"
echo -e " ${hijau}│ ${hijau}Service Dropbear                  $blue=$NC $status_beruangjatuh"
echo -e " ${hijau}│ ${hijau}Service Haproxy                   $blue=$NC $status_haproxy"
echo -e " ${hijau}│ ${hijau}Service Crons                     $blue=$NC $status_cron"
echo -e " ${hijau}│ ${hijau}Service Nginx Webserver           $blue=$NC $status_nginx"
echo -e " ${hijau}│ ${hijau}Service Xray Vmess WS TLS         $blue=$NC $status_ss"
echo -e " ${hijau}│ ${hijau}Service Xray Vmess WS Non TLS     $blue=$NC $status_ss"
echo -e " ${hijau}│ ${hijau}Service Xray Vmess gRPC           $blue=$NC $status_ss"
echo -e " ${hijau}│ ${hijau}Service Xray Vless WS TLS         $blue=$NC $status_ss"
echo -e " ${hijau}│ ${hijau}Service Xray Vless WS Non TLS     $blue=$NC $status_ss"
echo -e " ${hijau}│ ${hijau}Service Xray Vless gRPC           $blue=$NC $status_ss"
echo -e " ${hijau}│ ${hijau}Service Xray Trojan WS            $blue=$NC $status_ss"
echo -e " ${hijau}│ ${hijau}Service Xray Trojan Non WS        $blue=$NC $status_ss"
echo -e " ${hijau}│ ${hijau}Service Xray Trojan gRPC          $blue=$NC $status_ss"
echo -e " ${hijau}│ ${hijau}Service Xray Shadowsocks WS       $blue=$NC $status_ss"
echo -e " ${hijau}│ ${hijau}Service Xray Shadowsocks Non WS   $blue=$NC $status_ss"
echo -e " ${hijau}│ ${hijau}Service Xray Shadowsocks gRPC     $blue=$NC $status_ss"
echo -e " ${hijau}│ ${hijau}Service Akun NoobzVpn             $blue=$NC $noobz"
echo -e " ${hijau}│ ${hijau}Service Iptables                  $blue=$NC $status_galo"
echo -e " ${hijau}│ ${hijau}Service RClocal                   $blue=$NC $status_galoo"
echo -e " ${hijau}│ ${hijau}Service Autoreboot                $blue=$NC $status_galooo"
echo -e " ${hijau}└────────────────────────────────────────────┘${NC}"
echo -e " ${hijau}┌────────────────────────────────────────────┐${NC}"
echo -e " ${hijau}│$NC$NC\033[41m             CONTACT SUPPORT / CS           $NC${hijau}│$NC"
echo -e " ${hijau}└────────────────────────────────────────────┘${NC}"
echo -e " ${hijau}│$NC SUPPORT             $blue= ${NC} ST PUSAT BLITAR ${NC}  "
echo -e " ${hijau}│$NC WHATSAPP            $blue= ${NC} 081931615811 ${NC}  "
echo -e " ${hijau}└────────────────────────────────────────────┘${NC}"
echo ""
read -n 1 -s -r -p "Press any key to back on menu"
menu
 run.temp1.sh 