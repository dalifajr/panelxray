#!/bin/bash
# bbr-arm.sh — Enable TCP BBR congestion control
# Compatible with both x86_64 and ARM (aarch64) architectures
# Replaces the shc-compiled bbr.sh binary

set -e

GREEN='\e[0;32m'
RED='\e[1;31m'
NC='\e[0m'

echo -e "${GREEN}[INFO]${NC} Mengaktifkan TCP BBR congestion control..."

# Check kernel version (BBR requires Linux 4.9+)
KERNEL_MAJOR=$(uname -r | cut -d. -f1)
KERNEL_MINOR=$(uname -r | cut -d. -f2)

if [[ "$KERNEL_MAJOR" -lt 4 ]] || { [[ "$KERNEL_MAJOR" -eq 4 ]] && [[ "$KERNEL_MINOR" -lt 9 ]]; }; then
    echo -e "${RED}[ERROR]${NC} Kernel $(uname -r) terlalu lama. BBR memerlukan kernel 4.9+"
    exit 1
fi

# Load tcp_bbr module
if ! lsmod | grep -q tcp_bbr; then
    modprobe tcp_bbr 2>/dev/null || true
fi

# Persist the module load
if ! grep -q "tcp_bbr" /etc/modules-load.d/*.conf 2>/dev/null; then
    echo "tcp_bbr" >> /etc/modules-load.d/bbr.conf
fi

# Configure sysctl for BBR
SYSCTL_CONF="/etc/sysctl.d/99-bbr.conf"
cat > "$SYSCTL_CONF" <<'EOF'
# TCP BBR congestion control
net.core.default_qdisc=fq
net.ipv4.tcp_congestion_control=bbr

# Additional TCP optimizations
net.ipv4.tcp_fastopen=3
net.core.rmem_max=67108864
net.core.wmem_max=67108864
net.ipv4.tcp_rmem=4096 87380 67108864
net.ipv4.tcp_wmem=4096 65536 67108864
net.ipv4.tcp_mtu_probing=1
net.ipv4.tcp_slow_start_after_idle=0
EOF

# Also update /etc/sysctl.conf for compatibility with scripts that check it
if ! grep -q "net.core.default_qdisc" /etc/sysctl.conf 2>/dev/null; then
    echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
fi
if ! grep -q "net.ipv4.tcp_congestion_control" /etc/sysctl.conf 2>/dev/null; then
    echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
else
    sed -i 's/net.ipv4.tcp_congestion_control=.*/net.ipv4.tcp_congestion_control=bbr/' /etc/sysctl.conf
fi

# Apply settings
sysctl --system >/dev/null 2>&1 || sysctl -p >/dev/null 2>&1 || true

# Verify
CURRENT_CC=$(sysctl -n net.ipv4.tcp_congestion_control 2>/dev/null || echo "unknown")
if [[ "$CURRENT_CC" == "bbr" ]]; then
    echo -e "${GREEN}[OK]${NC} TCP BBR berhasil diaktifkan"
else
    echo -e "${RED}[WARN]${NC} BBR mungkin belum aktif (current: $CURRENT_CC). Akan aktif setelah reboot."
fi
