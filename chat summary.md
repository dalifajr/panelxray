# Ringkasan Progress Debugging VPN/Xray/SSH-WS

Tanggal rangkuman: 2026-03-26/27
Repo: https://github.com/dalifajr/panelxray
Branch: main

## 1) Tujuan Utama Sesi
- Memperbaiki kegagalan koneksi XRAY (WS/gRPC/TLS) dan SSH WebSocket (HTTP Custom).
- Menyamakan perilaku server error dengan server sehat.
- Menstabilkan proses instalasi/update agar konfigurasi tidak drift setelah update.

## 2) Gejala Awal yang Ditangani
- gRPC sempat 502 (upstream/protocol mismatch).
- WS path sempat HTTP 000 pada beberapa fase.
- SSH tunnel sering gagal dengan pesan `cannot negotiate`.
- Dropbear sempat gagal start karena konflik bind port 22.
- `cek-update` sempat gagal dengan syntax error near `}`.

## 3) Investigasi & Temuan Kunci
- Konflik peran port SSH terjadi berkali-kali antar `sshd` vs `dropbear` (22/109/143).
- Template/hasil update beberapa kali saling overwrite sehingga server drift dari profil sehat.
- Ada beberapa varian mode service WS:
  - mode binary: `/usr/bin/ws -f /usr/bin/tun.conf`
  - mode python: `/usr/bin/python3 -O /etc/whoiamluna/ws.py 10015`
- Log server menunjukkan jalur WS sudah sampai banner SSH, tetapi gagal negosiasi algoritma saat backend Dropbear dipakai.

## 4) Perubahan Teknis yang Sudah Dilakukan

### A. Routing/Template sinkronisasi
- Penyesuaian `limit/haproxy.cfg` untuk stabilitas edge routing dan kompatibilitas bind/options.
- Penyesuaian `limit/xray.conf` (placeholder domain, route/path consistency).
- Penyesuaian `limit/tun.conf` sesuai target route WS-SSH.

### B. Installer/Updater hardening
- `scripts/install/premi.sh`
  - normalisasi SSH/Dropbear/WS runtime.
  - deploy `ws.py` ke `/etc/whoiamluna/ws.py`.
  - penambahan package compatibility (`python-is-python3` jika tersedia).
- `scripts/install/debian.sh`
  - disejajarkan untuk route host WS dan port profile SSH.
- `scripts/maintenance/update.sh`
  - sinkronisasi runtime configs.
  - deployment `ws.py` ke `/etc/whoiamluna/ws.py`.
- `menu/cek-update` dan `limit/menu/cek-update`
  - sinkronisasi logic update runtime.
  - perbaikan penulisan file override agar tidak rawan parse error.

### C. File template penting yang disesuaikan
- `limit/ws.service`
- `limit/ws.py`
- `limit/dropbear.conf`
- `limit/sshd`
- `menu/cek-update`
- `limit/menu/cek-update`
- `scripts/install/premi.sh`
- `scripts/install/debian.sh`
- `scripts/maintenance/update.sh`

## 5) Fix Kritis yang Menutup Error `cek-update`
- Akar masalah: blok heredoc pada updater berisiko parsing di sebagian environment.
- Solusi: penggantian heredoc ke `printf` saat menulis override file.
- Dampak: menghilangkan error syntax dekat baris penutup function `}`.

## 6) Fix Kritis untuk `cannot negotiate`
- Gejala menunjukkan WS tunnel berhasil sampai SSH banner tetapi negosiasi gagal saat backend Dropbear.
- Solusi terbaru:
  - default upstream `ws.py` diarahkan ke OpenSSH (`127.0.0.1:22`) agar kompatibilitas algoritma lebih luas.
  - perubahan dilakukan di:
    - `limit/ws.py`
    - `limit references/etc/whoiamluna/ws.py`

## 7) Commit yang Sudah Dipush
- `1cc74d1` - sync ssh-ws listener profile and update runtime scripts
- `5178bec` - fix cek-update syntax by removing heredoc parsing risk
- `6b1a5e7` - route ws python upstream to openssh port 22

## 8) Status Layanan Berdasarkan Log Terbaru User
- `xray.service` aktif/running (warning deprecasi ada, bukan crash).
- `ws.service` dan `dropbear.service` running, tetapi negosiasi SSH sempat gagal di client tertentu.
- Setelah fix upstream WS ke OpenSSH (port 22), diharapkan error `cannot negotiate` berkurang/hilang pada HTTP Custom.

## 9) Prosedur Apply Cepat di VPS
1. Jalankan update:
   - `/usr/local/sbin/cek-update`
2. Reload & restart:
   - `systemctl daemon-reload`
   - `systemctl restart ws ssh dropbear nginx haproxy xray`
3. Verifikasi:
   - `systemctl status ws ssh dropbear xray --no-pager -l`
   - `ss -tlpn | egrep ':10015|:109|:143|:443|:1010|:1013|:22'`
   - `grep -n 'DEFAULT_HOST' /etc/whoiamluna/ws.py /usr/bin/ws.py 2>/dev/null`

## 10) Catatan Operasional
- Warning deprecasi Xray (WebSocket/VMess/Trojan/gRPC) tidak otomatis berarti service down.
- Penyebab utama outage berulang sebelumnya adalah drift konfigurasi antar installer/update/template.
- Fokus stabilitas jangka panjang:
  - jaga parity `menu/cek-update` dan `limit/menu/cek-update`.
  - hindari route override yang saling bertentangan antar script.
  - pastikan mode WS (python/binary) konsisten dengan file yang dideploy.

---
Jika diperlukan, ringkasan ini bisa dipecah lagi menjadi:
- `RUNBOOK_RECOVERY.md` (langkah recovery operasional)
- `CHANGELOG_DEBUG_SESSION.md` (detail teknis per commit)
- `KNOWN_ISSUES.md` (daftar masalah residual + workaround)
