# Web Panel E2E Checklist

Checklist ini dipakai untuk validasi Stage 3 (service control, realtime stats, CRUD aman, backup otomatis, rollback, dan sinkronisasi sidecar DB).

## 1. Prasyarat

1. Jalankan di VPS Linux yang sudah terpasang panel hasil installer MVC.
2. Pastikan service panel aktif: `systemctl status vpnxray-web-panel`.
3. Pastikan file kredensial ada:
   - `/etc/vpnxray-web-panel/admin_user`
   - `/etc/vpnxray-web-panel/admin_password`
4. Jalankan sebagai root.

## 2. Jalankan Skrip E2E Otomatis

1. Masuk ke root repo script.
2. Jalankan:

```bash
chmod +x scripts/maintenance/panel-e2e.sh
bash scripts/maintenance/panel-e2e.sh
```

3. Opsi parameter (opsional):

```bash
PROTOCOL=vless TEST_USER=e2e_vless_01 CREATE_DAYS=5 UPDATE_DAYS=10 BASE_URL=https://domainmu/panel bash scripts/maintenance/panel-e2e.sh
```

## 3. Kriteria Lulus Otomatis

1. Login panel berhasil.
2. Create account berhasil, marker masuk ke `/etc/xray/config.json`.
3. Backup baru terbuat di `/etc/xray/backup-web-panel/` setelah setiap mutasi create/update/delete.
4. Sidecar DB sinkron:
   - `/etc/vmess/.vmess.db`
   - `/etc/vless/.vless.db`
   - `/etc/trojan/.trojan.db`
   - `/etc/shadowsocks/.shadowsocks.db`
5. Update expiry di config dan sidecar sama.
6. Simulasi rollback berhasil (hash config sebelum/sesudah tetap sama saat restart dipaksa gagal).
7. Delete account membersihkan config dan sidecar.

## 4. Verifikasi Manual Dashboard

1. Buka halaman dashboard panel.
2. Pastikan kartu realtime berubah otomatis setiap 10 detik.
3. Coba tombol `Restart`, `Start`, `Stop` di salah satu service non-kritis terlebih dahulu.
4. Pastikan status service pada dashboard berubah sesuai hasil aksi.

## 5. Catatan Keamanan Operasional

1. Hindari uji `Stop` pada service kritikal (misalnya `xray`/`nginx`) di jam produksi.
2. Jalankan uji lengkap pada jam maintenance window.
3. Simpan log hasil uji untuk audit deployment.