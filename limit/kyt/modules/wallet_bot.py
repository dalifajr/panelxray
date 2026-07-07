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
        "Gunakan tombol di bawah untuk melihat riwayat transaksi atau topup."
    )

    inline = [
        [Button.inline("📜 Riwayat Transaksi", "tx-history")],
        [Button.inline("💳 Cara Top Up", "topup-info")],
        [Button.inline("⬅️ Main Menu", "menu")]
    ]

    await event.edit(msg, buttons=inline)


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


@bot.on(events.CallbackQuery(data=b'topup-info'))
async def topup_info(event):
    domain = globals().get("DOMAIN", "localhost")
    msg = (
        "💳 **Cara Top Up Saldo**\n\n"
        "Top up saldo sangat mudah dan otomatis:\n"
        f"1. Silakan buka website panel Anda: https://{domain}/wallet\n"
        "2. Input nominal top up (kelipatan Rp 5.000, minimal Rp 5.000)\n"
        "3. Klik tombol top up untuk memunculkan QRIS Dinamis\n"
        "4. Scan & bayar QRIS menggunakan e-wallet (Dana, Ovo, GoPay, LinkAja) atau Mobile Banking\n\n"
        "Saldo otomatis bertambah dalam hitungan detik setelah pembayaran sukses!"
    )

    await event.edit(msg, buttons=[[Button.inline("⬅️ Kembali", "wallet-bot")]])
