#!/bin/bash
# cf-arm.sh — Setup Cloudflare DNS subdomain otomatis
# Compatible with both x86_64 and ARM (aarch64) architectures
# Replaces the shc-compiled cf.sh binary

set -e

GREEN='\e[0;32m'
RED='\e[1;31m'
YELLOW='\e[1;33m'
NC='\e[0m'

# Get server IP
MYIP=$(curl -sS ipv4.icanhazip.com 2>/dev/null || curl -sS ifconfig.me 2>/dev/null || echo "")
if [[ -z "$MYIP" ]]; then
    echo -e "${RED}[ERROR]${NC} Tidak dapat mendeteksi IP server"
    exit 1
fi

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}       CLOUDFLARE DNS AUTO SETUP${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "IP Server: ${YELLOW}$MYIP${NC}"
echo ""

# Input Cloudflare credentials
read -p "Masukkan Cloudflare Email: " CF_EMAIL
read -p "Masukkan Cloudflare API Key (Global): " CF_API_KEY
read -p "Masukkan Domain utama (contoh: example.com): " CF_DOMAIN
read -p "Masukkan Subdomain (contoh: vps1): " CF_SUBDOMAIN

if [[ -z "$CF_EMAIL" || -z "$CF_API_KEY" || -z "$CF_DOMAIN" || -z "$CF_SUBDOMAIN" ]]; then
    echo -e "${RED}[ERROR]${NC} Semua field harus diisi!"
    exit 1
fi

FULL_DOMAIN="${CF_SUBDOMAIN}.${CF_DOMAIN}"
echo ""
echo -e "${GREEN}[INFO]${NC} Mengonfigurasi DNS untuk ${YELLOW}${FULL_DOMAIN}${NC} → ${YELLOW}${MYIP}${NC}"

# Get Zone ID
echo -e "${GREEN}[INFO]${NC} Mengambil Zone ID..."
ZONE_RESPONSE=$(curl -sS -X GET "https://api.cloudflare.com/client/v4/zones?name=${CF_DOMAIN}" \
    -H "X-Auth-Email: ${CF_EMAIL}" \
    -H "X-Auth-Key: ${CF_API_KEY}" \
    -H "Content-Type: application/json")

ZONE_ID=$(echo "$ZONE_RESPONSE" | grep -oP '"id"\s*:\s*"\K[a-f0-9]{32}' | head -1)

if [[ -z "$ZONE_ID" ]]; then
    echo -e "${RED}[ERROR]${NC} Gagal mendapatkan Zone ID. Periksa email dan API key Anda."
    echo "$ZONE_RESPONSE" | head -5
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Zone ID: ${ZONE_ID}"

# Check if record already exists
echo -e "${GREEN}[INFO]${NC} Mengecek record DNS yang ada..."
EXISTING=$(curl -sS -X GET "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records?name=${FULL_DOMAIN}&type=A" \
    -H "X-Auth-Email: ${CF_EMAIL}" \
    -H "X-Auth-Key: ${CF_API_KEY}" \
    -H "Content-Type: application/json")

RECORD_ID=$(echo "$EXISTING" | grep -oP '"id"\s*:\s*"\K[a-f0-9]{32}' | head -1)

if [[ -n "$RECORD_ID" ]]; then
    # Update existing record
    echo -e "${YELLOW}[INFO]${NC} Record sudah ada, mengupdate..."
    RESULT=$(curl -sS -X PUT "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records/${RECORD_ID}" \
        -H "X-Auth-Email: ${CF_EMAIL}" \
        -H "X-Auth-Key: ${CF_API_KEY}" \
        -H "Content-Type: application/json" \
        --data "{\"type\":\"A\",\"name\":\"${FULL_DOMAIN}\",\"content\":\"${MYIP}\",\"ttl\":1,\"proxied\":false}")
else
    # Create new record
    echo -e "${GREEN}[INFO]${NC} Membuat record DNS baru..."
    RESULT=$(curl -sS -X POST "https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records" \
        -H "X-Auth-Email: ${CF_EMAIL}" \
        -H "X-Auth-Key: ${CF_API_KEY}" \
        -H "Content-Type: application/json" \
        --data "{\"type\":\"A\",\"name\":\"${FULL_DOMAIN}\",\"content\":\"${MYIP}\",\"ttl\":1,\"proxied\":false}")
fi

# Check result
SUCCESS=$(echo "$RESULT" | grep -oP '"success"\s*:\s*\K(true|false)' | head -1)

if [[ "$SUCCESS" == "true" ]]; then
    echo -e "${GREEN}[OK]${NC} DNS record berhasil dikonfigurasi!"
    echo -e "     Domain: ${YELLOW}${FULL_DOMAIN}${NC}"
    echo -e "     IP:     ${YELLOW}${MYIP}${NC}"
    
    # Save domain to system files
    echo "$FULL_DOMAIN" > /etc/xray/domain
    echo "$FULL_DOMAIN" > /root/domain
    echo "IP=$MYIP" >> /var/lib/kyt/ipvps.conf 2>/dev/null || true
    
    echo -e "${GREEN}[OK]${NC} Domain tersimpan di /etc/xray/domain"
else
    echo -e "${RED}[ERROR]${NC} Gagal mengonfigurasi DNS record"
    echo "$RESULT" | head -5
    exit 1
fi
