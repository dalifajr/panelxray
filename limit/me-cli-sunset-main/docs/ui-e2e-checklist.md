# UI End-to-End Checklist

Dokumen ini menjadi checklist uji manual UI bot Telegram per domain utama.

## Global Pre-check
- [ ] Bot dapat merespons `/start` dan menampilkan Home panel.
- [ ] Keyboard menampilkan pola konsisten: tombol aksi di atas, `🏠 Home` + `↩️ Batal` di baris akhir.
- [ ] Input tidak valid menampilkan format `Gagal` + `Langkah berikutnya`.
- [ ] Pada list paginated, navigasi `Prev/Next`, `p:<n>`, dan `hal:<n>` berjalan.

## Domain: Account
- [ ] Masuk ke menu `1 👤 Akun`.
- [ ] Uji `➕ Tambah` dengan nomor valid dan invalid.
- [ ] Uji OTP valid/invalid, pastikan pesan next-step jelas.
- [ ] Uji `🔁 Ganti` akun, pastikan akun aktif berubah dan cache profile relevan.
- [ ] Uji `🗑 Hapus` akun non-aktif, pastikan state kembali aman.

## Domain: Package
- [ ] Masuk ke menu `2 📦 Paket`, list paket tampil paginated.
- [ ] Pilih nomor paket untuk detail, lalu `⬅️ Kembali` kembali ke list dengan page context tetap.
- [ ] Uji `⛔ Unsub` dengan konfirmasi `✅ Ya` dan `❌ Tidak`.
- [ ] Uji jump page: `p:2`, `hal:3`, dan page out-of-range.

## Domain: Payment
- [ ] Dari detail package, uji `⚡ Bayar Pulsa`, `💳 Bayar E-Wallet`, `📷 Bayar QRIS`.
- [ ] Uji flow e-wallet dengan nomor valid/invalid.
- [ ] Uji decoy flow (balance/qris/manual) dan cek hasil panel.
- [ ] Uji `🔁 Pulsa N Kali`: input N, delay, decoy yes/no.
- [ ] Saat running, tombol `⛔ Batal Progress` harus menghentikan proses seperti stop session.

## Domain: Family
- [ ] Masuk ke menu `6 👪 Family`, kirim family code valid.
- [ ] Pastikan semua opsi package ditampilkan paginated (tidak terpotong limit kecil).
- [ ] Pilih nomor package untuk buka detail.
- [ ] Kembali dari detail ke list, pastikan page context tetap.
- [ ] Uji `p:<n>` dan `hal:<n>` di list family.

## Domain: Circle
- [ ] Masuk menu `10 ⭕ Circle`, uji `🔄 Refresh`.
- [ ] Uji `➕ Invite`, `🗑 Remove`, `✅ Accept` dengan input valid/invalid.
- [ ] Uji `🎁 Bonus`, pilih item bonus ke detail package.
- [ ] Uji kembali ke menu dan Home dari tiap substate.

## Pass Criteria
- [ ] Tidak ada state buntu (user selalu punya jalur kembali).
- [ ] Tidak ada keyboard yang kehilangan `🏠 Home` dan `↩️ Batal` (kecuali state khusus running yang tetap menyediakan kontrol stop).
- [ ] Error message konsisten dengan guidance.
- [ ] Tidak ada regresi pada flow payment normal maupun decoy.
