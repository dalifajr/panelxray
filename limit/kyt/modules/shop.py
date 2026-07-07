from kyt import *
from kyt.modules.ui import (
    ask_text_clean, delete_messages, manager_banner, 
    run_command, sanitize_panel_username, upsert_message,
    send_account_with_qr, short_progress, back_button
)

@bot.on(events.CallbackQuery(data=b'shop-menu'))
async def shop_menu(event):
    sender = await event.get_sender()
    chat = event.chat_id

    # 1. Get bot config (check if sales mode is enabled)
    config = api_call("GET", "/bot/config")
    if config.get("bot_mode", "admin_only") != "sales":
        await event.answer("⚠️ Bot saat ini tidak berada dalam mode jualan.", alert=True)
        return

    # 2. Check balance and linking
    balance_res = api_call("GET", f"/wallet/balance/{sender.id}")
    if not balance_res.get("linked", False):
        msg = (
            "⚠️ **Akun Telegram Anda Belum Terhubung!**\n\n"
            "Untuk dapat melakukan pembelian VPN di bot, silakan:\n"
            "1. Login ke website panel Anda.\n"
            "2. Buka menu **Profil Pengguna**.\n"
            "3. Klik tombol **Hubungkan Telegram**.\n\n"
            "Setelah terhubung, saldo website Anda otomatis sinkron dengan bot ini."
        )
        buttons = [[Button.inline("⬅️ Kembali ke Menu", "menu")]]
        await event.edit(msg, buttons=buttons)
        return

    balance = balance_res.get("balance", 0)

    # 3. Get pricing list
    pricing_res = api_call("GET", "/pricing")
    prices = pricing_res.get("prices", [])
    
    price_dict = {}
    for p in prices:
        price_dict[p.get("protocol")] = p.get("price", 0)

    # Default fallbacks if not set in DB
    ssh_price = price_dict.get("ssh", 10000)
    vmess_price = price_dict.get("vmess", 15000)
    vless_price = price_dict.get("vless", 15000)
    trojan_price = price_dict.get("trojan", 15000)
    ss_price = price_dict.get("shadowsocks", 15000)

    inline = [
        [Button.inline(f"👤 SSH (Rp {ssh_price:,} / 30 Hari)", "buy-proto:ssh")],
        [Button.inline(f"🛰️ VMESS (Rp {vmess_price:,} / 30 Hari)", "buy-proto:vmess")],
        [Button.inline(f"🧩 VLESS (Rp {vless_price:,} / 30 Hari)", "buy-proto:vless")],
        [Button.inline(f"🛡️ TROJAN (Rp {trojan_price:,} / 30 Hari)", "buy-proto:trojan")],
        [Button.inline(f"🌘 SHADOWSOCKS (Rp {ss_price:,} / 30 Hari)", "buy-proto:shadowsocks")],
    ]

    # Check if trial is enabled
    if config.get("bot_trial_enabled", False):
        trial_days = config.get("bot_trial_days", 1)
        inline.append([Button.inline(f"✨ Coba Gratis (Trial {trial_days} Hari)", "buy-proto:trial")])

    inline.append([Button.inline("⬅️ Kembali ke Menu", "menu")])

    msg = (
        f"{manager_banner('Shop Menu', 'Beli VPN Self-Service')}\n\n"
        f"💰 **Saldo Anda:** `Rp {balance:,}`\n"
        "Silakan pilih protokol VPN yang ingin Anda beli:"
    )

    await event.edit(msg, buttons=inline)


@bot.on(events.CallbackQuery(data=re.compile(b'buy-proto:(.*)')))
async def buy_proto(event):
    sender = await event.get_sender()
    chat = event.chat_id
    proto = event.pattern_match.group(1).decode('utf-8')

    # Get pricing list and config
    config = api_call("GET", "/bot/config")
    pricing_res = api_call("GET", "/pricing")
    prices = pricing_res.get("prices", [])
    
    price_dict = {}
    for p in prices:
        price_dict[p.get("protocol")] = p.get("price", 0)

    # Durations selection
    if proto == "trial":
        trial_days = config.get("bot_trial_days", 1)
        # Directly go to create trial
        return await start_purchase_flow(event, "trial", trial_days, 0)

    price = price_dict.get(proto, 15000)

    inline = [
        [Button.inline(f"📅 30 Hari — Rp {price:,}", f"buy-pkg:{proto}:30:{price}")],
        [Button.inline(f"📅 60 Hari — Rp {price*2:,}", f"buy-pkg:{proto}:60:{price*2}")],
        [Button.inline(f"📅 90 Hari — Rp {price*3:,}", f"buy-pkg:{proto}:90:{price*3}")],
        [Button.inline("⬅️ Kembali ke Katalog", "shop-menu")]
    ]

    msg = (
        f"🛒 **Pembelian Akun {proto.upper()}**\n\n"
        "Silakan pilih masa aktif paket Anda:"
    )
    await event.edit(msg, buttons=inline)


@bot.on(events.CallbackQuery(data=re.compile(b'buy-pkg:(.*?):(.*?):(.*)')))
async def buy_pkg(event):
    proto = event.pattern_match.group(1).decode('utf-8')
    days = int(event.pattern_match.group(2).decode('utf-8'))
    price = int(event.pattern_match.group(3).decode('utf-8'))

    await start_purchase_flow(event, proto, days, price)


async def start_purchase_flow(event, proto, days, price):
    sender = await event.get_sender()
    chat = event.chat_id

    # Double check balance
    if price > 0:
        balance_res = api_call("GET", f"/wallet/balance/{sender.id}")
        balance = balance_res.get("balance", 0)
        if balance < price:
            await event.answer(f"❌ Saldo tidak cukup! Saldo Anda: Rp {balance:,}", alert=True)
            return

    msgs_to_del = []
    
    # Input Username
    prompt_text = "👤 **Masukkan Username Akun VPN Anda:**\n*(Gunakan huruf & angka saja, min 3 karakter)*"
    user, msgs = await ask_text_clean(event, chat, sender.id, prompt_text)
    msgs_to_del.extend(msgs)
    
    user = sanitize_panel_username(user)
    if not user or len(user) < 3:
        await delete_messages(chat, msgs_to_del)
        await event.reply("❌ Username tidak valid atau terlalu pendek. Gunakan huruf/angka, minimal 3 karakter.")
        return

    # Check if username contains invalid characters
    if not re.match("^[a-zA-Z0-9]+$", user):
        await delete_messages(chat, msgs_to_del)
        await event.reply("❌ Username hanya boleh mengandung huruf dan angka (tanpa simbol/spasi).")
        return

    # Proceed to confirmation
    await delete_messages(chat, msgs_to_del)

    confirm_msg = (
        "🛒 **Konfirmasi Pembelian**\n\n"
        f"▪ Layanan: `{proto.upper() if proto != 'trial' else 'TRIAL'}`\n"
        f"▪ Username: `{user}`\n"
        f"▪ Masa Aktif: `{days} Hari`\n"
        f"▪ Total Pembayaran: `Rp {price:,}`\n\n"
        "Apakah Anda yakin ingin melanjutkan pembelian?"
    )

    inline = [
        [Button.inline("✅ Konfirmasi & Bayar", f"confirm-buy:{proto}:{days}:{price}:{user}"),
         Button.inline("❌ Batal", "shop-menu")]
    ]

    await event.edit(confirm_msg, buttons=inline)


@bot.on(events.CallbackQuery(data=re.compile(b'confirm-buy:(.*?):(.*?):(.*?):(.*)')))
async def confirm_buy(event):
    sender = await event.get_sender()
    chat = event.chat_id

    proto = event.pattern_match.group(1).decode('utf-8')
    days = int(event.pattern_match.group(2).decode('utf-8'))
    price = int(event.pattern_match.group(3).decode('utf-8'))
    user = event.pattern_match.group(4).decode('utf-8')

    # Debit balance
    if price > 0:
        desc = f"Pembelian akun {proto.upper()} username {user} ({days} hari) via Bot Telegram"
        debit_res = api_call("POST", "/wallet/debit", {
            "tg_id": str(sender.id),
            "amount": price,
            "description": desc
        })
        if "error" in debit_res:
            await event.answer(f"❌ Transaksi gagal: {debit_res['error']}", alert=True)
            return

    await event.edit("⏳ **Memproses pembuatan akun VPN Anda...**\nMohon tunggu beberapa detik.")

    # Execute creation command
    try:
        # Default SNI profile or empty
        domain = globals().get("DOMAIN", "localhost")
        
        if proto == "ssh" or (proto == "trial" and days <= 3): # Assume SSH trial or custom routing
            # SSH script args: username, password, expiry_days
            # Let's generate a random password for SSH
            password = "".join(random.choices("0123456789", k=6))
            code, out = run_command("addssh", [user, password, str(days)])
            is_ssh = True
        else:
            # Xray protocols (vmess, vless, trojan, shadowsocks)
            # Standard creation tools require: user, exp, quota, iplimit
            # Let's call the script directly
            script_map = {
                "vmess": "addws",
                "vless": "addvless",
                "trojan": "addtr",
                "shadowsocks": "addss"
            }
            cmd = script_map.get(proto, "addws")
            # Default parameters: username, expiry, quota(100GB), iplimit(2)
            code, out = run_command(cmd, [domain, user, str(days), "100", "2"])
            is_ssh = False

        if code != 0:
            # Refund balance if failed
            if price > 0:
                api_call("POST", "/wallet/debit", {
                    "tg_id": str(sender.id),
                    "amount": -price, # Negative is topup/refund
                    "description": f"Refund: Gagal pembuatan akun {proto.upper()} {user}"
                })
            await event.edit(f"❌ **Gagal membuat akun VPN.**\nSystem log:\n`{out[:200]}`\n\nSaldo Anda telah dikembalikan.")
            return

        # Register creation
        is_trial = (proto == "trial")
        service_name = "ssh" if (proto == "ssh" or proto == "trial") else proto
        import datetime
        expiry_date = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
        register_account_creation(str(sender.id), service_name, user, expiry_date, is_trial=is_trial)

        success_msg = (
            "✅ **Pembelian Berhasil!**\n\n"
            f"Akun VPN Anda telah sukses dibuat.\n"
            f"Username: `{user}`\n"
            f"Masa Aktif: `{days} Hari`\n"
            f"Kedaluwarsa: `{expiry_date}`\n\n"
            "Detail akun koneksi:\n"
            f"```\n{out}\n```"
        )
        
        await event.edit(success_msg, buttons=[[Button.inline("⬅️ Beli Lagi", "shop-menu"), Button.inline("🏠 Main Menu", "menu")]])

    except Exception as e:
        logging.exception("Purchase execution failed: %s", e)
        await event.edit(f"❌ Terjadi kesalahan internal: {e}")
