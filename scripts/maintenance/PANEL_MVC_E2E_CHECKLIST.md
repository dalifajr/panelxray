# PANEL MVC E2E CHECKLIST (STAGING)

## Prasyarat
- Jalankan sebagai root di VPS staging.
- Script `install-panel-mvc` sudah tersedia di `/usr/local/sbin`.
- Domain aktif tersedia di `/etc/xray/domain`.

## Langkah
1. Jalankan uji otomatis:
   - `panel-mvc-e2e`
2. Verifikasi manual akses browser:
   - `https://<domain>/panel/login`
   - Jika uji via CLI, gunakan SNI-aware resolve:
     - `curl -kI --resolve <domain>:443:127.0.0.1 https://<domain>/panel/login`
3. Login dengan kredensial panel server (`/usr/bin/user` dan `/usr/bin/password`).
4. Buka dashboard dan cek status service.
5. Uji mutasi web API:
   - Create akun uji (misalnya `staging_uji_01`)
   - Renew akun uji
   - Delete akun uji
6. Cek audit log:
   - `tail -n 50 /var/log/vpnxray-webpanel/audit.log`
7. Validasi non-regression:
   - `systemctl is-active xray nginx haproxy ws ssh dropbear`

## Hasil yang diharapkan
- Installer sukses tanpa merusak konfigurasi aktif.
- Endpoint `/panel/login` dapat diakses.
- Service critical tetap active setelah install dan mutasi.
- Semua operasi CRUD tercatat di audit log.

## Template Laporan
- Setelah uji selesai, isi template laporan pass/fail di:
   - `scripts/maintenance/PANEL_MVC_STAGING_REPORT_TEMPLATE.md`
- Simpan hasil final dengan nama baru, contoh:
   - `PANEL_MVC_STAGING_REPORT_YYYYMMDD_HHMM.md`

## Troubleshooting Cepat
- Jika keluar error `akses panel via reverse proxy gagal (HTTP 404)`:
   - pastikan patch panel ada di server SSL ingress:
      - `nginx -T | sed -n '/BEGIN VPNXRAY WEB PANEL/,/END VPNXRAY WEB PANEL/p'`
   - jalankan ulang installer terbaru:
      - `install-panel-mvc`
