#!/bin/bash 
# COLOR VALIDATION
clear
y='\033[1;33m' #yellow
l='\033[0;37m'
BGX="\033[42m"
CYAN="\033[96m"
z="\033[92;1m" # // Hijau
zx="\033[97;1m" # // putih
RED='\033[0;31m'
NC='\033[0m'
gray="\e[1;30m"
Blue="\033[0;34m"
green='\033[1;32m'
grenbo="\e[92;1m"
purple="\033[1;95m"
YELL='\033[0;33m'
cyan="\033[1;36m"

# // installer Udp
UDPX="https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate 'https://docs.google.com/uc?export=download&id=1S3IE25v_fyUfCLslnujFBSBMNunDHDk2' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=1S3IE25v_fyUfCLslnujFBSBMNunDHDk2"

# // Gettings Info
ISP=$(cat /etc/xray/isp)
CITY=$(cat /etc/xray/city)
IPVPS=$(curl -s ipv4.icanhazip.com)
domain=$(cat /etc/xray/domain)
RAM=$(free -m | awk 'NR==2 {print $2}')
USAGERAM=$(free -m | awk 'NR==2 {print $3}')
MEMOFREE=$(printf '%-1s' "$(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2 }')")
LOADCPU=$(printf '%-0.00001s' "$(top -bn1 | awk '/Cpu/ { cpu = "" 100 - $8 "%" }; END { print cpu }')")
MODEL=$(cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/PRETTY_NAME//g')
CORE=$(printf '%-1s' "$(grep -c cpu[0-9] /proc/stat)")
DATEVPS=$(date +'%d/%m/%Y')
TIMEZONE=$(printf '%(%H:%M:%S)T')
SERONLINE=$(uptime -p | cut -d " " -f 2-10000)
clear
MYIP=$(curl -sS ipv4.icanhazip.com)
echo ""
#########################
# // USERNAME IZIN IPP
rm -f /usr/bin/user
username=$(curl -sS https://raw.githubusercontent.com/dalifajr/vpnxray/main/kunci | grep $MYIP | awk '{print $2}')
echo "$username" >/usr/bin/user

# // VALIDITY
rm -f /usr/bin/e
valid=$(curl -sS https://raw.githubusercontent.com/dalifajr/vpnxray/main/kunci | grep $MYIP | awk '{print $3}')
echo "$valid" > /usr/bin/e

# // DETAIL ORDER IZIN IP
username=$(cat /usr/bin/user)
oid=$(cat /usr/bin/ver)
exp=$(cat /usr/bin/e)

clear
# // DAYS LEFT
d1=$(date -d "$valid" +%s)
d2=$(date -d "$today" +%s)
certifacate=$(((d1 - d2) / 86400))

# // VPS INFORMATION
DATE=$(date +'%Y-%m-%d')
datediff() {
    d1=$(date -d "$1" +%s)
    d2=$(date -d "$2" +%s)
    echo -e "$COLOR1 $NC Expiry In   : $(( (d1 - d2) / 86400 )) Days"
}
mai="datediff "$Exp" "$DATE""

# Status ExpiRED Active | Geo Project

# // AKTIVATED & EXPIRED
Info="${green}Activated${NC}"
Error="${RED}Expired ${NC}"
#//
today=`date -d "0 days" +"%Y-%m-%d"`
Exp1=$(curl -sS https://raw.githubusercontent.com/dalifajr/vpnxray/main/kunci | grep $MYIP | awk '{print $3}')
if [[ $today < $Exp1 ]]; then
sts="${Info}"
else
sts="${Error}"
fi
echo -e "\e[32mloading...\e[0m"
clear

# // GETTINGS SYSTEM
uptime="$(uptime -p | cut -d " " -f 2-10)"
cpu_usage1="$(ps aux | awk 'BEGIN {sum=0} {sum+=$3}; END {print sum}')"
cpu_usage="$((${cpu_usage1/\.*} / ${coREDiilik:-1}))"
cpu_usage+=" %"
WKT=$(curl -s ipinfo.io/timezone )
DAY=$(date +%A)
DATE=$(date +%m/%d/%Y)
DATE2=$(date -R | cut -d " " -f -5)
IPVPS=$(curl -s ipinfo.io/ip )
cname=$( awk -F: '/model name/ {name=$2} END {print name}' /proc/cpuinfo )
cores=$( awk -F: '/model name/ {core++} END {print core}' /proc/cpuinfo )
freq=$( awk -F: ' /cpu MHz/ {freq=$2} END {print freq}' /proc/cpuinfo )
tram=$( free -m | awk 'NR==2 {print $2}' )
uram=$( free -m | awk 'NR==2 {print $3}' )
fram=$( free -m | awk 'NR==2 {print $4}' )
clear
ssh_service=$(/etc/init.d/ssh status | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
dropbear_service=$(/etc/init.d/dropbear status | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
haproxy_service=$(systemctl status haproxy | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
xray_service=$(systemctl status xray | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
nginx_service=$(systemctl status nginx | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
#Status | Geo Project
clear


# // RUNNING SSH
if [[ $ssh_service == "running" ]]; then 
   status_ssh="${green}✅${NC}"
else
   status_ssh="${z}❌${NC} "
fi

# // RUNNING WEBSOCKET
ssh_ws=$( systemctl status ws | grep Active | awk '{print $3}' | sed 's/(//g' | sed 's/)//g' )
if [[ $ssh_ws == "running" ]]; then
    status_ws_epro="${green}✅${NC}"
else
    status_ws_epro="${z}✅${NC} "
fi

# RUNNING HAPROXY
if [[ $haproxy_service == "running" ]]; then 
   status_haproxy="${green}✅${NC}"
else
   status_haproxy="${z}❌${NC} "
fi

# RUNNING XRAY
if [[ $xray_service == "running" ]]; then 
   status_xray="${green}ON ✅${NC}"
else
   status_xray="${z}❌${NC} "
fi

# RUNNING NGINX
if [[ $nginx_service == "running" ]]; then 
   status_nginx="${green}✅${NC}"
else
   status_nginx="${z}❌${NC} "
fi

# RUNNING DROPBEAR
if [[ $dropbear_service == "running" ]]; then 
   status_dropbear="${green}✅${NC}"
else
   status_dropbear="${z}❌${NC} "
fi
# // UPDATE / REVISI all menu
REVISI="https://raw.githubusercontent.com/dalifajr/vpnxray/main/"

# // INFO CREATE ACCOUNT
# \\ Vless account //
vlx=$(grep -c -E "^#& " "/etc/xray/config.json")
let vla=$vlx/2
# \\ Vmess account //
vmc=$(grep -c -E "^### " "/etc/xray/config.json")
let vma=$vmc/2
# \\ Trojan account //
ssh1="$(awk -F: '$3 >= 1000 && $1 != "nobody" {print $1}' /etc/passwd | wc -l)"
trx=$(grep -c -E "^#! " "/etc/xray/config.json")
let trb=$trx/2
# \\ shadowsocks account //
ssx=$(grep -c -E "^#!# " "/etc/xray/config.json")
let ssa=$ssx/2
# // ---- >>>
########### // MEMEK // KANJUT
########### // HENCET // KONTOL
TZ="\033[1;35m___\033[1;34m___\033[1;32m___\033[1;36m___\033[1;37m___\033[1;34m"
vers="version.Sc 3.09"
# // ----->>>
r="\033[1;31m"  #REDTERANG
a=" ${z}ACCOUNT PREMIUM" 
BG_RED="\033[45;1m"
echo -e " "
echo -e " ${z}╭══════════════════════════════════════════════════════════╮${NC}"
echo -e " ${z}│$NC\033[5;33m                     Lunatic Tunneling                    $NC${z}│$NC"
echo -e " ${z}╰══════════════════════════════════════════════════════════╯${NC}"
echo -e " ${z}╭══════════════════════════════════════════════════════════╮${NC}"
echo -e " ${z}│$NC • $NC${z} System OS ${NC}     ${z}=$NC $MODEL${NC}"
echo -e " ${z}│$NC • $NC${z} Core Cpu ${NC}      ${z}=$NC $CORE${NC}"
echo -e " ${z}│$NC • $NC${z} Server RAM ${NC}    ${z}=$NC $uram/$RAM MB $NC"
echo -e " ${z}│$NC • $NC${z} Uptime Server ${NC} ${z}=$NC $SERONLINE${NC}"
echo -e " ${z}│$NC • $NC${z} Domain ${NC}        ${z}=$NC $domain${NC}"
echo -e " ${z}│$NC • $NC${z} IP VPS ${NC}        ${z}=$NC $IPVPS${NC}"
echo -e " ${z}│$NC • $NC${z} ISP ${NC}           ${z}=$NC $ISP${NC}"
echo -e " ${z}│$NC • $NC${z} City ${NC}          ${z}=$NC $CITY${NC}"
echo -e " ${z}│$NC • $NC${z} Cpu Usage ${NC}     ${z}=$NC $cpu_usage${NC}"
echo -e " ${z}╰══════════════════════════════════════════════════════════╯${NC}"
#echo -e "                  ${KIRI} ${z}YOUR ACCOUNT ON VPS${NC} ${KANAN}"
#echo -e "        ${z}❒════════════════════════════════════════════❒${NC}"

#echo -e "        ${z}❒════════════════════════════════════════════❒${NC}" 
#echo -e "                ${KIRI}${z}Lunatic  Tunneling${z}${KANAN}"
#echo -e "                ${LURUS}${LURUS2}${LURUS}${LURUS2}${LURUS}${LURUS2}${LURUS}${LURUS2}${LURUS}${LURUS2}"
echo -e "    ${zx} NGINX$NC : $status_nginx ${zx} WS-EPRO$NC : $status_ws_epro ${zx} DROPBEAR$NC : $status_dropbear ${zx} HAPROXY$NC : $status_haproxy   $NC${zx}$NC" 



#echo -e " ${z}│ ${NC}${z} WS-EPRO$NC : $status_ws_epro" "    ${z} DROPBEAR$NC : $status_dropbear" "     ${z} HAPROXY$NC : $status_haproxy   $NC${z}│$NC" 
echo -e "                        ${BG_RED}ACCOUNT INFO${NC}"
echo -e "        SSH & OPENVPN : $ssh1 TROJAN : $trb  SHADOWSOCKS-R : $ssa"
echo -e "                        VLESS : $vla VMESS : $vma"
echo -e " ${z}╭══════════════════════════════════════════════════════════╮${NC}"
echo -e " ${z}│$NC   [${green}01${NC}] ssh / Libev              [${green}07${NC}] check Bandwith    ${z}  │$NC" 
echo -e " ${z}│$NC   [${green}02${NC}] vmess / xray             [${green}08${NC}] Test SpedTest     ${z}  │$NC"    
echo -e " ${z}│$NC   [${green}03${NC}] vLess / xray             [${green}09${NC}] Limiting Speed    ${z}  │$NC"  
echo -e " ${z}│$NC   [${green}04${NC}] Trojan / xray            [${green}10${NC}] Backup \ Restored ${z}  │$NC"
echo -e " ${z}│$NC   [${green}05${NC}] shadowsock               [${green}11${NC}] Gett Bot Tele.    ${z}  │$NC"
echo -e " ${z}│$NC   [${green}06${NC}] Manager/ Settings.       [${green}12${NC}] Update Sc.Version ${z}  │$NC"
echo -e " ${z}╰══════════════════════════════════════════════════════════╯${NC}"
#echo -e " ${z}╭════════════════╮╭══════════════════╮╭════════════════════╮${NC}"
#echo -e " ${z}│ ${NC}${z} SSH$NC : $status_ssh" "        ${z} NGINX$NC : $status_nginx" "        ${z} XRAY$NC : $status_xray      $NC${z}│$NC" 
#echo -e " ${z}│ ${NC}${z} WS-EPRO$NC : $status_ws_epro" "    ${z} DROPBEAR$NC : $status_dropbear" "     ${z} HAPROXY$NC : $status_haproxy   $NC${z}│$NC" 
#echo -e " ${z}╰════════════════╯╰══════════════════╯╰════════════════════╯${NC}"
echo -e " ${z}╭══════════════════════════════════════════════════════════╮${NC}"
echo -e " ${z}│$NC${z} Dev.Sc$NC        ${z}=$NC Lunatic Tunneling"
echo -e " ${z}│$NC${z} Client/Regist$NC ${z}=$NC $username [$sts]"
echo -e " ${z}│$NC${z} Exp Script$NC    ${z}=$NC $exp / $certifacate Days$NC "
echo -e " ${z}╰══════════════════════════════════════════════════════════╯${NC}"
echo -e "                        ${vers}"
echo -e "                        ${TZ} ${NC}"
echo
read -p " Select Options 1/12 : " wZtXtQ
echo -e ""
case $wZtXtQ in
1)
clear
m-sshws
;;
2)
clear
m-vmess
;;
3)
clear
m-vless
;;
4)
clear
m-trojan
;;
5)
clear
m-ssws
;;
6)
clear
utility
;;
7)
clear
bw
;;
8)
clear
speedtest
;;
9)
clear
limitspeed
;;
10)
clear
menu-backup
;;
11)
clear
add-bot-panel
;;
12)
clear
wget ${REVISI}update.sh && chmod +x update.sh && ./update.sh
;;
*)
clear
menu
;;
esac
