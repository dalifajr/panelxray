# Project Structure

## Tujuan Perapihan

Struktur dipisahkan berdasarkan fungsi agar mudah dipelihara tanpa memutus kompatibilitas command lama.

## Struktur Baru

- `scripts/install/`
  - `debian.sh`
  - `premi.sh`
- `scripts/maintenance/`
  - `update.sh`
  - `kyt.sh`
  - `test.sh`
  - `udp-custom.sh`
- `limit/`
  - Aset runtime (menu, bot, kyt, config, service)
- `menu/`
  - Runtime command set di workspace

## Kompatibilitas

File lama di root tetap ada sebagai wrapper:

- `debian.sh`
- `premi.sh`
- `update.sh`
- `kyt.sh`
- `test.sh`
- `udp-custom.sh`

Wrapper akan meneruskan eksekusi ke script baru di folder `scripts/`.

## Sumber Aset

Instalasi tidak lagi bergantung pada `menu.zip`, `bot.zip`, `kyt.zip`.
Sumber utama sekarang folder:

- `limit/menu`
- `limit/bot`
- `limit/kyt`

Jika folder lokal tidak tersedia (misalnya script dipakai standalone), script akan fallback clone repository ke `/tmp/panelxray-assets`.
