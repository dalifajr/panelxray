# PANELXRAY

Panel manajemen VPS berbasis Bash untuk layanan SSH, OpenVPN, dan Xray (VMESS/VLESS/TROJAN/SHADOWSOCKS), termasuk menu panel, bot Telegram, limit IP, backup/restore, dan update otomatis.

## Fitur Utama

- Manajemen akun SSH, VMESS, VLESS, TROJAN, SHADOWSOCKS.
- Trial, renew, delete, cek user/config untuk tiap service.
- Suspend dan unsuspend akun Xray (VMESS/VLESS/TROJAN).
- Auto limit IP (mode suspend, bukan delete permanen).
- Cek daftar akun suspend per service via command `ceksuspend`.
- Integrasi bot Telegram (create/check/delete/suspend/unsuspend service tertentu).
- Backup/restore dan fitur maintenance (clear log, restart service, speedtest, dll).
- Struktur installer baru dengan wrapper root script tetap kompatibel.

## Kompatibilitas OS

- Ubuntu 20.04+
- Ubuntu 24.04 (DigitalOcean) didukung dengan mode repo resmi
- Debian 10+

Catatan Ubuntu 24.04:
- Installer menggunakan mode aman update APT dan sanitasi source bermasalah.
- Log sanitasi repo disimpan di `/var/log/kyt-apt-sanitize.log`.

## Instalasi (Direkomendasikan)

```bash
rm -f ~/premi.sh ~/premi.sh.*
wget -qO ~/premi.sh https://raw.githubusercontent.com/dalifajr/panelxray/main/premi.sh
chmod +x ~/premi.sh
bash ~/premi.sh
```

## Update Script

```bash
wget -qO ~/update.sh https://raw.githubusercontent.com/dalifajr/panelxray/main/update.sh
chmod +x ~/update.sh
bash ~/update.sh
```

## Struktur Project (Ringkas)

- `scripts/install/`
	- `premi.sh`
	- `debian.sh`
- `scripts/maintenance/`
	- `update.sh`
	- `test.sh`
	- `kyt.sh`
	- `udp-custom.sh`
- `limit/`
	- aset runtime (`menu`, `bot`, `kyt`, config, service)
- `menu/`
	- command menu runtime di workspace

Wrapper kompatibilitas lama tetap tersedia di root:
- `premi.sh`, `debian.sh`, `update.sh`, `test.sh`, `kyt.sh`, `udp-custom.sh`

## Fitur Suspend/Unsuspend

- Panel menu:
	- `m-vmess`, `m-vless`, `m-trojan` memiliki opsi suspend/unsuspend.
- Command:
	- `suspws`, `unsuspws`
	- `suspvless`, `unsuspvless`
	- `susptr`, `unsusptr`
- Daftar suspend:
	- `ceksuspend`
	- `ceksuspend vmess|vless|trojan`

Status suspend disimpan di:
- `/etc/kyt/suspended/vmess/`
- `/etc/kyt/suspended/vless/`
- `/etc/kyt/suspended/trojan/`

## Port Info

```text
TROJAN WS            : 443
TROJAN GRPC          : 443
SHADOWSOCKS WS       : 443
SHADOWSOCKS GRPC     : 443
VLESS WS             : 443
VLESS GRPC           : 443
VLESS NONTLS         : 80
VMESS WS             : 443
VMESS GRPC           : 443
VMESS NONTLS         : 80
SSH WS / TLS         : 443
SSH NON TLS          : 8880
OPENVPN SSL/TCP      : 1194
SLOWDNS              : 5300
```

## Troubleshooting Singkat

Jika APT error karena repo pihak ketiga:

```bash
grep -R "vbernat/haproxy-2.0" /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null
tail -n 80 /var/log/kyt-apt-sanitize.log
```

Jika ingin paksa installer hanya pakai repo resmi Ubuntu 24:

```bash
OFFICIAL_UBUNTU24_REPOS_ONLY=1 bash ~/premi.sh
```

