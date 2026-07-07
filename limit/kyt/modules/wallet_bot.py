from kyt import *
from kyt.modules.ui import manager_banner

@bot.on(events.CallbackQuery(data=b'wallet-bot'))
async def wallet_bot(event):
    sender = await event.get_sender()
    
    # 1. Cek saldo dan link
    balance_res = api_call("GET", f"/wallet/balance/{sender.id}")
    if not balance_res.get("linked", False):
        msg = (
            "⚠️ **Akun Telegram Anda Belum Terhubung!**\n\n"
            "Silakan hubungkan Telegram Anda terlebih dahulu di website panel:\n"
            "**Profil Pengguna** → **Hubungkan Telegram**"
        )
        buttons = [[Button.inline("⬅️ Main Menu", "menu")]]
        await event.edit(msg, buttons=buttons)
        return

    balance = balance_res.get("balance", 0)
    web_user = balance_res.get("web_username", "")

    msg = (
        f"{manager_banner('Wallet Info', 'Dompet VPN XRAY')}\n\n"
        f"👤 **Linked User:** `{web_user}`\n"
        f"💰 **Saldo Anda:** `Rp {balance:,}`\n\n"
        "Gunakan tombol di bawah untuk melakukan top up, klaim voucher, atau melihat riwayat transaksi."
    )

    inline = [
        [Button.inline("💳 Top Up Saldo", "topup-info"), Button.inline("🎫 Klaim Voucher", "claim-voucher")],
        [Button.inline("📜 Riwayat Transaksi", "tx-history")],
        [Button.inline("⬅️ Main Menu", "menu")]
    ]

    await event.edit(msg, buttons=inline)


@bot.on(events.CallbackQuery(data=b'claim-voucher'))
async def claim_voucher(event):
    sender = await event.get_sender()
    chat = event.chat_id

    # 1. Ask for voucher code
    prompt = (
        "🎫 **Klaim Voucher Saldo**\n\n"
        "Silakan masukkan kode voucher Anda:"
    )

    msgs_to_del = []
    code, msgs = await ask_text_clean(event, chat, sender.id, prompt)
    msgs_to_del.extend(msgs)

    if not code:
        await delete_messages(chat, msgs_to_del)
        await event.reply("❌ Klaim voucher dibatalkan.")
        return

    code = code.strip().upper()
    await delete_messages(chat, msgs_to_del)

    # 2. Call Laravel redeem API
    await event.edit("⏳ **Memproses klaim voucher Anda...**")
    
    res = api_call("POST", "/wallet/voucher/redeem", {
        "tg_id": str(sender.id),
        "voucher_code": code
    })

    if "error" in res:
        await event.edit(f"❌ **Gagal mengklaim voucher:**\n`{res['error']}`", buttons=[[Button.inline("⬅️ Kembali", "wallet-bot")]])
        return

    # 3. Success notification
    success_msg = (
        "🎉 **Klaim Voucher Berhasil!**\n\n"
        f"{res.get('message')}\n\n"
        f"💰 **Saldo Baru:** `Rp {res.get('new_balance', 0):,}`"
    )
    await event.edit(success_msg, buttons=[[Button.inline("⬅️ Kembali", "wallet-bot")]])


@bot.on(events.CallbackQuery(data=b'tx-history'))
async def tx_history(event):
    sender = await event.get_sender()
    
    res = api_call("GET", f"/transaction/history/{sender.id}")
    txs = res.get("transactions", [])

    if not txs:
        msg = (
            f"📜 **Riwayat Transaksi Anda**\n\n"
            "Belum ada riwayat transaksi tercatat."
        )
        await event.edit(msg, buttons=[[Button.inline("⬅️ Kembali", "wallet-bot")]])
        return

    tx_lines = []
    for idx, tx in enumerate(txs[:8]):
        txtype = tx.get("type", "").upper()
        amount = tx.get("total_amount", 0)
        desc = tx.get("description", "")
        date = tx.get("created_at", "")[:10]
        
        symbol = "➕" if txtype == "topup" else "➖"
        tx_lines.append(f"{symbol} **Rp {amount:,}** ({date})\n└ `{desc}`")

    msg = (
        f"📜 **Riwayat Transaksi Terakhir**\n\n" +
        "\n\n".join(tx_lines)
    )

    await event.edit(msg, buttons=[[Button.inline("⬅️ Kembali", "wallet-bot")]])


from kyt.modules.ui import ask_text_clean, delete_messages

@bot.on(events.CallbackQuery(data=b'topup-info'))
async def topup_info(event):
    sender = await event.get_sender()
    chat = event.chat_id

    # 1. Ask for top-up amount
    prompt = (
        "💳 **Top Up Saldo via QRIS**\n\n"
        "Silakan masukkan nominal top up yang Anda inginkan:\n"
        "*(Minimal Rp 5.000, kelipatan Rp 5.000, contoh: 10000, 20000)*"
    )

    msgs_to_del = []
    amount_str, msgs = await ask_text_clean(event, chat, sender.id, prompt)
    msgs_to_del.extend(msgs)

    if not amount_str:
        await delete_messages(chat, msgs_to_del)
        await event.reply("❌ Proses top up dibatalkan.")
        return

    # 2. Validate input
    amount_str = re.sub(r'[^0-9]', '', amount_str)
    if not amount_str.isdigit():
        await delete_messages(chat, msgs_to_del)
        await event.reply("❌ Nominal harus berupa angka bulat.")
        return

    amount = int(amount_str)
    if amount < 5000:
        await delete_messages(chat, msgs_to_del)
        await event.reply("❌ Minimal nominal top up adalah Rp 5.000.")
        return

    if amount % 5000 != 0:
        await delete_messages(chat, msgs_to_del)
        await event.reply("❌ Nominal top up harus kelipatan Rp 5.000 (contoh: 5000, 10000, 15000, 20000).")
        return

    # Clean prompt messages
    await delete_messages(chat, msgs_to_del)

    # 3. Call Laravel topup API
    await event.edit("⏳ **Menyiapkan pembayaran QRIS Anda...**")
    
    res = api_call("POST", "/wallet/topup", {
        "tg_id": str(sender.id),
        "amount": amount
    })

    if "error" in res:
        await event.edit(f"❌ **Gagal menyiapkan top up:**\n`{res['error']}`", buttons=[[Button.inline("⬅️ Kembali", "wallet-bot")]])
        return

    # 4. Display QR Code and Instructions
    qr_url = res.get("qr_code_url")
    total_amount = res.get("total_amount")
    unique_code = res.get("unique_code")
    ref = res.get("reference")

    payment_instructions = (
        "💳 **PEMBAYARAN QRIS OTOMATIS**\n\n"
        f"▪ ID Referensi: `{ref}`\n"
        f"▪ Nominal Top Up: `Rp {amount:,}`\n"
        f"▪ Kode Unik: `Rp {unique_code}`\n"
        f"⚠️ **TOTAL PEMBAYARAN:** `Rp {total_amount:,}`\n\n"
        "**PENTING:** Silakan scan kode QR di atas menggunakan aplikasi e-wallet Anda (Dana, Ovo, GoPay, ShopeePay, LinkAja) atau Mobile Banking.\n"
        "Pastikan membayar **EXACTLY / SAMA PERSIS** dengan total pembayaran di atas agar otomatis masuk dalam hitungan detik!"
    )

    buttons = [[Button.inline("🏠 Main Menu", "menu")]]

    # Send the QR Code image directly using the URL!
    try:
        await bot.send_file(chat, qr_url, caption=payment_instructions, buttons=buttons)
    except Exception as e:
        # Fallback to text message with URL if send_file fails
        fallback_msg = (
            f"{payment_instructions}\n\n"
            f"🔗 [Klik di sini untuk melihat Kode QR Anda]({qr_url})"
        )
        await bot.send_message(chat, fallback_msg, buttons=buttons)
