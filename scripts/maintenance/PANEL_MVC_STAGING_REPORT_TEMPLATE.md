# PANEL MVC STAGING PASS/FAIL REPORT TEMPLATE

Gunakan template ini setelah menjalankan uji staging agar hasil bisa dipetakan langsung ke checklist dan gate non-regression.

## 1) Metadata Eksekusi
- Tanggal:
- Waktu mulai:
- Waktu selesai:
- VPS / Hostname:
- Domain:
- Operator:
- Branch / Commit:
- Versi script (`panel-mvc-e2e`):

## 2) Ringkasan Hasil
- Exit code `panel-mvc-e2e`:
- Keputusan akhir staging: `PASS` / `FAIL`
- Catatan ringkas:

## 3) Mapping Checklist -> Status
| ID | Item Checklist | Bukti (command/output) | Status (`PASS`/`FAIL`) | Catatan |
|---|---|---|---|---|
| C1 | Jalankan `panel-mvc-e2e` |  |  |  |
| C2 | Verifikasi akses `https://<domain>/panel/login` |  |  |  |
| C3 | Login pakai kredensial panel (`/usr/bin/user`, `/usr/bin/password`) |  |  |  |
| C4 | Dashboard tampil dan status service terbaca |  |  |  |
| C5a | CRUD: Create akun uji |  |  |  |
| C5b | CRUD: Renew akun uji |  |  |  |
| C5c | CRUD: Delete akun uji |  |  |  |
| C6 | Audit log berisi jejak operasi |  |  |  |
| C7 | Non-regression service (`xray nginx haproxy ws ssh dropbear`) |  |  |  |

## 4) Non-Regression Gate Matrix
| Gate | Kriteria Lulus | Bukti | Hasil (`PASS`/`FAIL`) |
|---|---|---|---|
| G1 Installer + service panel | `install-panel-mvc` sukses dan `systemctl is-active vpnxray-webpanel` = `active` |  |  |
| G2 Route + API health panel | `/panel/login` bisa diakses dan `http://127.0.0.1:3000/api/health` sukses |  |  |
| G3 CRUD + audit | Create/Renew/Delete sukses dan tercatat di `/var/log/vpnxray-webpanel/audit.log` |  |  |
| G4 Service kritikal tetap aktif | `xray nginx haproxy ws ssh dropbear` semuanya `active` |  |  |

### Aturan Keputusan Gate
- Staging `PASS` jika `G1=PASS` dan `G2=PASS` dan `G3=PASS` dan `G4=PASS`.
- Jika salah satu gate `FAIL`, keputusan akhir wajib `FAIL` dan lanjut ke rencana rollback/mitigasi.

## 5) Evidence Snippet (Opsional tapi disarankan)
### 5.1 Output uji otomatis
```bash
panel-mvc-e2e | tee /tmp/panel-mvc-e2e.log
echo "$?"
```

### 5.2 Verifikasi service kritikal
```bash
systemctl is-active xray nginx haproxy ws ssh dropbear
```

### 5.3 Verifikasi route panel (SNI-aware)
```bash
curl -kI --resolve <domain>:443:127.0.0.1 https://<domain>/panel/login
```

### 5.4 Verifikasi audit log
```bash
tail -n 80 /var/log/vpnxray-webpanel/audit.log
```

## 6) Defect & Tindakan
| No | Gejala | Dugaan Akar Masalah | Dampak | Tindakan | Status |
|---|---|---|---|---|---|
| 1 |  |  |  |  |  |

## 7) Rollback / Mitigasi
- Perlu rollback: `YA` / `TIDAK`
- Jika `YA`, command yang dijalankan:
  - `uninstall-panel-mvc`
  - langkah tambahan:
- Hasil rollback:

## 8) Sign-Off
- Verifikator:
- Disetujui untuk produksi: `YA` / `TIDAK`
- Catatan akhir:
