# Asset Structure (Folder-Based)

This project no longer relies on packaged archives (`menu.zip`, `bot.zip`, `kyt.zip`) for runtime installation.

## Canonical Asset Sources

- `limit/menu/` : all CLI menu commands copied to `/usr/local/sbin` or `/usr/sbin`
- `limit/bot/` : bot helper scripts copied to `/usr/bin`
- `limit/kyt/` : Python bot module copied to `/usr/bin/kyt`

## Script Behavior

Updated scripts now use this order:

1. Use local folder assets from this repository (`./limit/...`)
2. If unavailable, fallback by cloning `https://github.com/dalifajr/vpnxray.git` into `/tmp/vpnxray-assets`
3. Copy folder contents directly (no zip extract, no passworded archive)

## Updated Scripts

- `debian.sh` (`menu()`)
- `premi.sh` (`menu()`)
- `update.sh` (`res1()`)
- `kyt.sh` (bot/kyt installer)
- `test.sh` (`download_config()` menu deploy)

## Maintenance Notes

- Edit menu commands only in `limit/menu/`.
- Keep runtime `menu/` in sync only when needed for debugging.
- Zip files can remain as legacy artifacts, but are no longer required by these scripts.
