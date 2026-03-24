#!/bin/bash
NS=$( cat /etc/xray/dns )
PUB=$( cat /etc/slowdns/server.pub )
domain=$(cat /etc/xray/domain)
#color

cd /etc/systemd/system/
rm -rf kyt.service
cd
grenbo="\e[92;1m"
NC='\e[0m'
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ASSET_ROOT="${REPO_ROOT}/limit"

sanitize_apt_sources() {
	rm -f /etc/apt/sources.list.d/vbernat-ubuntu-haproxy-2_0-*.list
	rm -f /etc/apt/sources.list.d/vbernat-ubuntu-haproxy-2_0-*.sources
}

safe_apt_update() {
	local tmplog bad_url log_file
	log_file="/var/log/kyt-apt-sanitize.log"
	tmplog="/tmp/apt-update-kyt.$$"

	touch "$log_file" 2>/dev/null || true
	echo "[$(date '+%Y-%m-%d %H:%M:%S')] kyt.sh: apt update start" >> "$log_file"

	if apt-get update -y; then
		echo "[$(date '+%Y-%m-%d %H:%M:%S')] kyt.sh: apt update success without sanitize" >> "$log_file"
		return 0
	fi

	apt-get update -y 2>&1 | tee "$tmplog" >/dev/null || true
	while IFS= read -r bad_url; do
		[[ -z "$bad_url" ]] && continue
		grep -Rsl "$bad_url" /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null | while IFS= read -r src_file; do
			if [[ "$src_file" == *.sources ]]; then
				rm -f "$src_file"
				echo "[$(date '+%Y-%m-%d %H:%M:%S')] kyt.sh: removed invalid deb822 source $src_file for $bad_url" >> "$log_file"
			else
				sed -i "\|$bad_url| s|^deb |# disabled-invalid-repo deb |" "$src_file"
				sed -i "\|$bad_url| s|^deb-src |# disabled-invalid-repo deb-src |" "$src_file"
				echo "[$(date '+%Y-%m-%d %H:%M:%S')] kyt.sh: disabled repo $bad_url in $src_file" >> "$log_file"
			fi
		done
	done < <(grep -Eo 'https?://[^ ]+' "$tmplog" | sed 's#/dists/.*##; s#/InRelease##; s#/Release##' | sort -u)

	rm -f "$tmplog"
	if apt-get update -y; then
		echo "[$(date '+%Y-%m-%d %H:%M:%S')] kyt.sh: apt update success after sanitize" >> "$log_file"
		return 0
	fi

	echo "[$(date '+%Y-%m-%d %H:%M:%S')] kyt.sh: apt update failed after sanitize" >> "$log_file"
	return 1
}

if [ ! -d "${ASSET_ROOT}/bot" ] || [ ! -d "${ASSET_ROOT}/kyt" ]; then
	TMP_ASSET="/tmp/panelxray-assets"
	rm -rf "${TMP_ASSET}"
	git clone --depth 1 https://github.com/dalifajr/panelxray.git "${TMP_ASSET}" >/dev/null 2>&1 || {
		echo "Gagal mengambil source bot/kyt"
		exit 1
	}
	ASSET_ROOT="${TMP_ASSET}/limit"
fi
#install
cd /usr/bin
rm -rf kyt
rm -rf bot
sanitize_apt_sources
safe_apt_update && apt upgrade -y
apt install -y python3 python3-pip git
mkdir -p /usr/bin/kyt
cp -rf "${ASSET_ROOT}/bot/." /usr/bin/
cp -rf "${ASSET_ROOT}/kyt/." /usr/bin/kyt/
chmod +x /usr/bin/bot-* 2>/dev/null
clear
pip3 install -r /usr/bin/kyt/requirements.txt

#isi data
echo ""
echo -e "\033[1;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e " \e[1;97;101m          ADD BOT PANEL          \e[0m"
echo -e "\033[1;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
echo -e "${grenbo}Tutorial Creat Bot and ID Telegram${NC}"
echo -e "${grenbo}[*] Creat Bot and Token Bot : @BotFather${NC}"
echo -e "${grenbo}[*] Info Id Telegram : @MissRose_bot , perintah /info${NC}"
echo -e "\033[1;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m"
read -e -p "[*] Input your Bot Token : " bottoken
read -e -p "[*] Input Your Id Telegram :" admin
echo -e BOT_TOKEN='"'$bottoken'"' >> /usr/bin/kyt/var.txt
echo -e ADMIN='"'$admin'"' >> /usr/bin/kyt/var.txt
echo -e DOMAIN='"'$domain'"' >> /usr/bin/kyt/var.txt
echo -e PUB='"'$PUB'"' >> /usr/bin/kyt/var.txt
echo -e HOST='"'$NS'"' >> /usr/bin/kyt/var.txt
clear

cat > /etc/systemd/system/kyt.service << END
[Unit]
Description=Simple kyt - @kyt
After=network.target

[Service]
WorkingDirectory=/usr/bin
ExecStart=/usr/bin/python3 -m kyt
Restart=always

[Install]
WantedBy=multi-user.target
END

systemctl start kyt 
systemctl enable kyt
systemctl restart kyt
rm -rf /tmp/panelxray-assets
cd /root
rm -rf kyt.sh
echo "Done"
echo "Your Data Bot"
echo -e "==============================="
echo "Token Bot         : $bottoken"
echo "Admin          : $admin"
echo "Domain        : $domain"
echo "Pub            : $PUB"
echo "Host           : $NS"
echo -e "==============================="
echo "Setting done"
clear

echo " Installations complete, type /menu on your bot"
