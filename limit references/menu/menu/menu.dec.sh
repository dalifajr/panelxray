#!/bin/bash
# COLOR VALIDATION
clear
y='\033[1;33m' #yellow
BGX="\033[42m"
CYAN="\033[0;36m"
z="\033[95;1m"
f="\033[1;97;41m"
G="\033[92m"
RED='\033[0;31m'
NC='\033[0;34m'
gray="\e[1;30m"
Blue="\033[0;34m"
blue="\033[0;34m"
green='\033[0;32m'
grenbo="\e[92;1m"
purple="\033[1;95m"
GREEN='\033[0;32m'
YELL='\033[0;32m'
CY='\033[0;34m'
p='\033[0;37m'
LIGHT='\033[0;37m'
hijau="\033[92m"

clear
# underline
UPU='\033[5;35m'
UCY='\033[5;36m'
UWH='\033[5;37m'
IPVPS=$(curl -s ipv4.icanhazip.com)
domain=$(cat /etc/xray/domain)
LOADCPU=$(printf '%-0.00001s' "$(top -bn1 | awk '/Cpu/ { cpu = "" 100 - $8 "%" }; END { print cpu }')")
MODEL=$(cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/"//g' | sed 's/PRETTY_NAME//g')
CORE=$(printf '%-1s' "$(grep -c cpu[0-9] /proc/stat)")
DATEVPS=$(date +'%d-%m-%Y')
TIMEZONE=$(printf '%(%H-%M-%S)T')
SERONLINE=$(uptime -p | cut -d " " -f 2-10000)
#ISP=$(curl -s ipinfo.io/org | cut -d " " -f 2-10)
clear
MYIP=$(curl -sS ipv4.icanhazip.com)
echo ""
clear
clear

tram=$( free -m | awk 'NR==2 {print $2}' )
uram=$( free -m | awk 'NR==2 {print $3}' )
clear
ssh_service=$(/etc/init.d/ssh status | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
dropbear_service=$(/etc/init.d/dropbear status | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
haproxy_service=$(systemctl status haproxy | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
xray_service=$(systemctl status xray | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
nginx_service=$(systemctl status nginx | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
noobz=$(systemctl status noobzvpns | grep Active | awk '{print $3}' | cut -d "(" -f2 | cut -d ")" -f1)
UdpSSH=$(systemctl status udp-custom | grep active | awk '{print $3}' | sed 's/(//g' | sed 's/)//g')
#Status
clear
# STATUS SERVICE  SSH 
if [[ $ssh_service == "running" ]]; then 
   status_ssh="${green}ON"
else
   status_ssh="${RED}ERROR"
fi

# // SSH Websocket Proxy
ssh_ws=$( systemctl status ws | grep Active | awk '{print $3}' | sed 's/(//g' | sed 's/)//g' )
if [[ $ssh_ws == "running" ]]; then
    status_ws_epro="${green}ON"
else
    status_ws_epro="${RED}ERROR"
fi

# STATUS SERVICE HAPROXY
if [[ $haproxy_service == "running" ]]; then 
   status_haproxy="${green}ON"
else
   status_haproxy="${RED}ERROR"
fi

# STATUS SERVICE XRAY
if [[ $xray_service == "running" ]]; then 
   status_xray="${green}ON"
else
   status_xray="${RED}ERROR"
fi

# STATUS SERVICE NGINX
if [[ $nginx_service == "running" ]]; then 
   status_nginx="${green}ON"
else
   status_nginx="${RED}ERROR"
fi
# STATUS NOOBZVPNS
if [[ $noobz == "running" ]]; then 
   noobz="${green}ON"
else
   noobz="${RED}ERROR"
fi
# STATUS SERVICE  SSH UDP 
if [[ $UdpSSH == "running" ]]; then 
   status_udp="${green}ON"
else
   status_udp="${RED}ERROR"
fi
# STATUS SERVICE Dropbear
if [[ $dropbear_service == "running" ]]; then 
   status_dropbear="${green}ON"
else
   status_dropbear="${RED}ERROR"
fi
# //
# // Log account
vlx=$(grep -c -E "^#& " "/etc/xray/config.json")
let vla=$vlx/2
vmc=$(grep -c -E "^### " "/etc/xray/config.json")
let vma=$vmc/2
ssh1="$(awk -F: '$3 >= 1000 && $1 != "nobody" {print $1}' /etc/passwd | wc -l)"
#! " "/etc/xray/config.json")
let trb=$trx/2
#!# " "/etc/xray/config.json")
let ssa=$ssx/2
# //

clear
clear
echo -e ""
echo -e "\E[44;1;39m ꧁࿇ SCRIPT SEDERHANA PENUH CINTA ࿇꧂ \E[0m"
echo -e ""                       
echo -e " ${NC} ╭════════════════════════════════════════════════════════════╮"
echo -e " ${NC} │\e[1;97;101m            Welcome To Script Premium St A1 Nyel            ${NC}"
echo -e " ${NC} ╰════════════════════════════════════════════════════════════╯"
echo -e " ${NC} ╭════════════════════════════════════════════════════════════╮"
#echo -e " ${NC} │$RED ● ${CYAN}SERVER VPS ${YELL}  = \033[0;37m$ISP ${NC}"
echo -e " ${NC} │$RED ● ${CYAN}SYSTEM OS ${YELL}   = \033[0;37m$MODEL${NC}"
echo -e " ${NC} │$RED ● ${CYAN}SYSTEM CORE ${YELL} = \033[0;37m$CORE${NC}"
echo -e " ${NC} │$RED ● ${CYAN}SERVER RAM ${YELL}  = \033[0;37m$tram / $uram MB $NC"
echo -e " ${NC} │$RED ● ${CYAN}LOADCPU ${YELL}     = \033[0;37m$LOADCPU ℅$NC"
echo -e " ${NC} │$RED ● ${CYAN}DATE ${YELL}        = \033[0;37m$DATEVPS${NC}"
echo -e " ${NC} │$RED ● ${CYAN}TIME ${YELL}        = \033[0;37m$TIMEZONE${NC}"
echo -e " ${NC} │$RED ● ${CYAN}UPTIME ${YELL}      = \033[0;37m$SERONLINE${NC}"
echo -e " ${NC} │$RED ● ${CYAN}IP VPS ${YELL}      = \033[0;37m$IPVPS${NC}"
echo -e " ${NC} │$RED ● ${CYAN}DOMAIN ${YELL}      = \033[0;37m$domain${NC}"
echo -e " ${NC} ╰════════════════════════════════════════════════════════════╯$NC"
echo -e " \033[0;37m                  >>> INFORMATION ACCOUNT <<< "
echo -e " ${NC}         ═════════════════════════════════════════════${NC}" 
echo -e "               ${green} SSH/OPENVPN/UDP  $YELL=\033[0;37m $ssh1  ${YELL}$a"
echo -e "               ${green} VMESS/WS/GRPC    $YELL=\033[0;37m $vma  ${YELL}$a"
echo -e "               ${green} VLESS/WS/GRPC    $YELL=\033[0;37m $vla  ${YELL}$a"
echo -e "               ${green} TROJAN/WS/GRPC   $YELL=\033[0;37m $trb  ${YELL}$a"
echo -e "               ${green} SHADOW/WS/GRPC   $YELL=\033[0;37m $ssa  ${YELL}$a"
echo -e " ${NC}         ═════════════════════════════════════════════${NC}" 
echo -e " ${p}                 >>> Dekengane Pusat Blitar <<<"
echo -e " ${NC} ╭═══════════════════╮╭═══════════════════╮╭══════════════════╮$NC"
echo -e " ${NC} │${p} SSH     $status_ssh   ${p}  NOOBZVPN   $noobz ${p}    NGINX $status_nginx ${p}    HAPROXY  $status_haproxy    ${NC}"
echo -e " ${NC} │${p} WS-ePro $status_ws_epro    ${p} UDP CUSTOM $status_udp ${p}    XRAY  $status_xray ${p}    DROPBEAR $status_dropbear    ${NC}"
echo -e " ${NC} ╰═══════════════════╯╰═══════════════════╯╰══════════════════╯$NC"
echo -e " ${NC} ╭════════════════════════════════════════════════════════════╮"
echo -e " ${NC} │$NC [${p}01$NC]${p} SSH MENU     $NC│ [${p}08$NC]${p} BCKP/RSTR    $NC│ [${p}15$NC]${p} MENU BOT ${NC}"
echo -e " ${NC} │$NC [${p}02$NC]${p} VMESS MENU   $NC│ [${p}09$NC]${p} GOTOP X RAM  $NC│ [${p}16$NC]${p} CHANGE DOMAIN ${NC}"    
echo -e " ${NC} │$NC [${p}03$NC]${p} VLESS MENU   $NC│ [${p}10$NC]${p} RESTART ALL  $NC│ [${p}17$NC]${p} FIX CRT DOMAIN${NC}"  
echo -e " ${NC} │$NC [${p}04$NC]${p} TROJAN MENU  $NC│ [${p}11$NC]${p} TELE BOT     $NC│ [${p}18$NC]${p} CANGE BANNER ${NC}"
echo -e " ${NC} │$NC [${p}05$NC]${p} AKUN NOOBZVPN$NC│ [${p}12$NC]${p} UPDATE MENU  $NC│ [${p}19$NC]${p} RESTART BANNER${NC}"
echo -e " ${NC} │$NC [${p}06$NC]${p} SS - LIBEV  $NC │ [${p}13$NC]${p} RUNNING      $NC│ [${p}20$NC]${p} SPEEDTEST    ${NC}"
echo -e " ${NC} │$NC [${p}07$NC]${p} INSTALL UDP  $NC│ [${p}14$NC]${p} INFO PORT$NC    │ [${p}21$NC]${p} EKSTRAK MENU    ${NC}"
echo -e " ${NC} ╰════════════════════════════════════════════════════════════╯"
echo -e " ${NC} ╭════════════════════════════════════════════════════════════╮"
echo -e " ${NC} │\033[0;37m Script Version $YELL= \033[0;37m HAPPY NEW YEAR 2025 "
echo -e " ${NC} ╰════════════════════════════════════════════════════════════╯\033[0;37m"
echo -e " "
read -p "  Options [ 1 - 21 ] ❱❱❱ " opt
echo -e ""
case $opt in
1 | 01)
clear
m-sshws
;;
2 | 02)
clear
m-vmess
;;
3 | 03)
clear
m-vless
;;
4 | 04)
clear
m-trojan
;;
5 | 05)
clear
m-noob
;;
6 | 06)
clear
m-ssws
;;
7 | 07)
clear
udepe
;;
8 | 08)
clear
menu-backup
;;
9 | 09)
clear
gotop
;;
10)
clear
restart
;;
11)
clear
m-bot
;;
12)
clear
wget -q https://raw.githubusercontent.com/Arya-Blitar22/st-pusat/main/update.sh
chmod +x update.sh
./update.sh
;;
13)
clear
run
;;
14)
clear
prot
;;
15)
clear
mbot-panel
;;
16)
clear
addhost
;;
17)
clear
fixcert
;;
18)
clear
nano /etc/issue.net
;;
19)
clear
/etc/init.d/dropbear restart
;;
20)
clear
speedtest
;;
21)
clear
m-system
;;
0 | 00)
exit
;;
x)
menu
;;
*) clear ;
menu
;;
esac menu.temp1.sh 