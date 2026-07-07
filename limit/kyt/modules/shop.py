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
        buttons = [[Button.inline("⬅️ Kembali ke Menu", "start")]]
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

    inline.append([Button.inline("⬅️ Kembali ke Menu", "start")])

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

    price = price_dict.get(proto, 15000)

    inline = [
        [Button.inline(f"📅 30 Hari — Rp {price:,}", f"buy-pkg:{proto}:30:{price}")],
        [Button.inline(f"📅 60 Hari — Rp {price*2:,}", f"buy-pkg:{proto}:60:{price*2}")],
        [Button.inline(f"📅 90 Hari — Rp {price*3:,}", f"buy-pkg:{proto}:90:{price*3}")],
    ]

    # Check if trial is enabled for individual protocol
    if config.get("bot_trial_enabled", False):
        trial_days = config.get("bot_trial_days", 1)
        inline.append([Button.inline(f"✨ Coba Gratis (Trial {trial_days} Hari)", f"buy-trial:{proto}:{trial_days}")])

    inline.append([Button.inline("⬅️ Kembali ke Katalog", "shop-menu")])

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

    await start_purchase_flow(event, proto, days, price, is_trial=False)


@bot.on(events.CallbackQuery(data=re.compile(b'buy-trial:(.*?):(.*)')))
async def buy_trial(event):
    proto = event.pattern_match.group(1).decode('utf-8')
    days = int(event.pattern_match.group(2).decode('utf-8'))
    await start_purchase_flow(event, proto, days, price=0, is_trial=True)


async def start_purchase_flow(event, proto, days, price, is_trial=False):
    sender = await event.get_sender()
    chat = event.chat_id

    # Double check balance
    if not is_trial and price > 0:
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

    # Proceed to confirmation / setup
    await delete_messages(chat, msgs_to_del)

    if is_trial:
        confirm_msg = (
            "🛒 **Konfirmasi Akun Trial**\n\n"
            f"▪ Layanan: `{proto.upper()} (TRIAL)`\n"
            f"▪ Username: `{user}`\n"
            f"▪ Masa Aktif: `{days} Hari`\n"
            f"▪ Total Pembayaran: `Gratis (Rp 0)`\n\n"
            "Apakah Anda yakin ingin mengaktifkan akun trial ini?"
        )
        inline = [
            [Button.inline("✅ Konfirmasi", f"conf-trial:{proto}:{days}:{user}"),
             Button.inline("❌ Batal", "shop-menu")]
        ]
        await event.edit(confirm_msg, buttons=inline)
    else:
        await render_purchase_config(event, proto, days, limit_ip=2, pay_method='s', username=user)


async def render_purchase_config(event, proto, days, limit_ip, pay_method, username):
    sender = await event.get_sender()
    
    # 1. Fetch balance
    balance_res = api_call("GET", f"/wallet/balance/{sender.id}")
    balance = balance_res.get("balance", 0)
    
    # 2. Fetch pricing
    pricing_res = api_call("GET", "/pricing")
    prices = pricing_res.get("prices", [])
    
    price_dict = {}
    for p in prices:
        price_dict[p.get("protocol")] = p.get("price", 0)
        
    base_price = price_dict.get(proto, 15000)
    ip_price = price_dict.get("add_ip", 5000)
    
    # 3. Fetch bot config
    config = api_call("GET", "/bot/config")
    max_ip_limit = config.get("max_ip_limit", 5)
    if max_ip_limit <= 0:
        max_ip_limit = 5
        
    # 4. Calculate prices
    vpn_cost = round((base_price / 30) * days)
    extra_ip_cost = (limit_ip - 1) * ip_price if limit_ip > 1 else 0
    total_price = vpn_cost + extra_ip_cost
    
    # Text
    pay_method_text = "💰 Saldo Website" if pay_method == 's' else "💳 QRIS (Bayar Langsung)"
    
    msg = (
        "⚙️ **Pengaturan Akun VPN Anda**\n\n"
        f"▪ **Layanan:** `{proto.upper()}`\n"
        f"▪ **Username:** `{username}`\n"
        f"▪ **Masa Aktif:** `{days} Hari`\n"
        f"▪ **Limit IP:** `{limit_ip} IP`\n"
        f"▪ **Metode Bayar:** `{pay_method_text}`\n\n"
        f"💵 **Harga VPN:** `Rp {vpn_cost:,}`\n"
        f"➕ **Biaya IP Ekstra:** `Rp {extra_ip_cost:,}`\n"
        f"⚠️ **TOTAL PEMBAYARAN:** `Rp {total_price:,}`\n"
    )
    if pay_method == 's':
        msg += f"💰 **Saldo Anda:** `Rp {balance:,}`\n"
        
    # Buttons
    buttons = []
    
    # Limit IP buttons
    ip_row = []
    if limit_ip > 1:
        ip_row.append(Button.inline("➖ IP", f"b-c:{proto}:{days}:{limit_ip - 1}:{pay_method}:{username}"))
    else:
        ip_row.append(Button.inline("➖ IP (Min)", "noop"))
        
    ip_row.append(Button.inline(f"{limit_ip} IP", "noop"))
    
    if limit_ip < max_ip_limit:
        ip_row.append(Button.inline("➕ IP", f"b-c:{proto}:{days}:{limit_ip + 1}:{pay_method}:{username}"))
    else:
        ip_row.append(Button.inline("➕ IP (Max)", "noop"))
        
    buttons.append(ip_row)
    
    # Payment method toggle button
    if pay_method == 's':
        buttons.append([Button.inline("➡️ Ubah ke QRIS (Bayar Langsung)", f"b-c:{proto}:{days}:{limit_ip}:q:{username}")])
    else:
        buttons.append([Button.inline("➡️ Ubah ke Saldo Website", f"b-c:{proto}:{days}:{limit_ip}:s:{username}")])
        
    # Lanjutkan & Batal buttons
    buttons.append([
        Button.inline("✅ Lanjutkan Pembayaran", f"b-pay:{proto}:{days}:{limit_ip}:{pay_method}:{username}"),
        Button.inline("❌ Batal", "shop-menu")
    ])
    
    await event.edit(msg, buttons=buttons)


@bot.on(events.CallbackQuery(data=re.compile(b'b-c:(.*?):(.*?):(.*?):(.*?):(.*)')))
async def handle_buy_config(event):
    proto = event.pattern_match.group(1).decode('utf-8')
    days = int(event.pattern_match.group(2).decode('utf-8'))
    limit_ip = int(event.pattern_match.group(3).decode('utf-8'))
    pay_method = event.pattern_match.group(4).decode('utf-8')
    username = event.pattern_match.group(5).decode('utf-8')
    
    await render_purchase_config(event, proto, days, limit_ip, pay_method, username)


@bot.on(events.CallbackQuery(data=b'noop'))
async def handle_noop(event):
    await event.answer()


@bot.on(events.CallbackQuery(data=re.compile(b'b-pay:(.*?):(.*?):(.*?):(.*?):(.*)')))
async def handle_buy_pay(event):
    sender = await event.get_sender()
    chat = event.chat_id
    
    proto = event.pattern_match.group(1).decode('utf-8')
    days = int(event.pattern_match.group(2).decode('utf-8'))
    limit_ip = int(event.pattern_match.group(3).decode('utf-8'))
    pay_method = event.pattern_match.group(4).decode('utf-8')
    username = event.pattern_match.group(5).decode('utf-8')

    # Fetch pricing again to verify price and calculate it
    pricing_res = api_call("GET", "/pricing")
    prices = pricing_res.get("prices", [])
    
    price_dict = {}
    for p in prices:
        price_dict[p.get("protocol")] = p.get("price", 0)
        
    base_price = price_dict.get(proto, 15000)
    ip_price = price_dict.get("add_ip", 5000)
    
    vpn_cost = round((base_price / 30) * days)
    extra_ip_cost = (limit_ip - 1) * ip_price if limit_ip > 1 else 0
    total_price = vpn_cost + extra_ip_cost

    if pay_method == 's':
        # Double check balance
        balance_res = api_call("GET", f"/wallet/balance/{sender.id}")
        balance = balance_res.get("balance", 0)
        if balance < total_price:
            await event.answer(f"❌ Saldo tidak cukup! Saldo Anda: Rp {balance:,}", alert=True)
            return

        # Debit balance
        desc = f"Pembelian akun {proto.upper()} username {username} ({days} hari) via Bot Telegram"
        debit_res = api_call("POST", "/wallet/debit", {
            "tg_id": str(sender.id),
            "amount": total_price,
            "description": desc
        })
        if "error" in debit_res:
            await event.answer(f"❌ Transaksi gagal: {debit_res['error']}", alert=True)
            return

        await event.edit("⏳ **Memproses pembuatan akun VPN Anda...**\nMohon tunggu beberapa detik.")

        # Execute creation command
        try:
            domain = globals().get("DOMAIN", "localhost")
            if proto == "ssh":
                password = "".join(random.choices("0123456789", k=6))
                code, out = run_command("addssh", [username, password, str(days)])
            else:
                script_map = {
                    "vmess": "addws",
                    "vless": "addvless",
                    "trojan": "addtr",
                    "shadowsocks": "addss"
                }
                cmd = script_map.get(proto, "addws")
                # Parameter: username, expiry, quota(100GB), iplimit
                code, out = run_command(cmd, ["3", username, str(days), "100", str(limit_ip)])

            if code != 0:
                # Refund balance if failed
                api_call("POST", "/wallet/debit", {
                    "tg_id": str(sender.id),
                    "amount": -total_price,
                    "description": f"Refund: Gagal pembuatan akun {proto.upper()} {username}"
                })
                await event.edit(f"❌ **Gagal membuat akun VPN.**\nSystem log:\n`{out[:200]}`\n\nSaldo Anda telah dikembalikan.")
                return

            # Register creation
            service_name = proto
            import datetime
            expiry_date = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
            register_account_creation(str(sender.id), service_name, username, expiry_date, is_trial=False)

            success_msg = (
                "✅ **Pembelian Berhasil!**\n\n"
                f"Akun VPN Anda telah sukses dibuat.\n"
                f"Username: `{username}`\n"
                f"Masa Aktif: `{days} Hari`\n"
                f"Kedaluwarsa: `{expiry_date}`\n\n"
                "Detail akun koneksi:\n"
                f"```\n{out}\n```"
            )
            await event.edit(success_msg, buttons=[[Button.inline("⬅️ Beli Lagi", "shop-menu"), Button.inline("🏠 Main Menu", "start")]])

        except Exception as e:
            logging.exception("Purchase execution failed: %s", e)
            await event.edit(f"❌ Terjadi kesalahan internal: {e}")
            
    elif pay_method == 'q':
        # Direct QRIS purchase
        await event.edit("⏳ **Menyiapkan pembayaran QRIS Anda...**")
        
        res = api_call("POST", "/bot/purchase/qris", {
            "tg_id": str(sender.id),
            "protocol": proto,
            "username": username,
            "days": days,
            "limit_ip": limit_ip,
            "quota": 100,
            "sni_config": "3"
        })

        if "error" in res:
            await event.edit(f"❌ **Gagal menyiapkan QRIS:**\n`{res['error']}`", buttons=[[Button.inline("⬅️ Kembali", "shop-menu")]])
            return

        qr_url = res.get("qr_code_url")
        total_amount = res.get("total_amount")
        unique_code = res.get("unique_code")
        ref = res.get("reference")

        payment_instructions = (
            "💳 **PEMBAYARAN QRIS OTOMATIS**\n\n"
            f"▪ ID Referensi: `{ref}`\n"
            f"▪ Pembelian: `VPN {proto.upper()} ({username})`\n"
            f"▪ Nominal: `Rp {total_price:,}`\n"
            f"▪ Kode Unik: `Rp {unique_code}`\n"
            f"⚠️ **TOTAL PEMBAYARAN:** `Rp {total_amount:,}`\n\n"
            "**PENTING:** Silakan scan kode QR di atas menggunakan aplikasi e-wallet Anda atau Mobile Banking.\n"
            "Pastikan membayar **EXACTLY / SAMA PERSIS** dengan total pembayaran di atas agar otomatis masuk dalam hitungan detik!\n"
            "Setelah terverifikasi, akun VPN akan otomatis terbuat dan dikirim ke Telegram Anda."
        )

        buttons = [
            [Button.inline("❌ Batalkan Pesanan", "cancel-topup")],
            [Button.inline("🏠 Main Menu", "start")]
        ]

        try:
            await bot.send_file(chat, qr_url, caption=payment_instructions, buttons=buttons)
        except Exception as e:
            fallback_msg = (
                f"{payment_instructions}\n\n"
                f"🔗 [Klik di sini untuk melihat Kode QR Anda]({qr_url})"
            )
            await bot.send_message(chat, fallback_msg, buttons=buttons)


@bot.on(events.CallbackQuery(data=re.compile(b'conf-trial:(.*?):(.*?):(.*)')))
async def handle_confirm_trial(event):
    sender = await event.get_sender()
    chat = event.chat_id
    
    proto = event.pattern_match.group(1).decode('utf-8')
    days = int(event.pattern_match.group(2).decode('utf-8'))
    username = event.pattern_match.group(3).decode('utf-8')
    
    await event.edit("⏳ **Memproses pembuatan akun Trial Anda...**\nMohon tunggu beberapa detik.")

    try:
        domain = globals().get("DOMAIN", "localhost")
        if proto == "ssh":
            password = "".join(random.choices("0123456789", k=6))
            code, out = run_command("addssh", [username, password, str(days)])
        else:
            script_map = {
                "vmess": "addws",
                "vless": "addvless",
                "trojan": "addtr",
                "shadowsocks": "addss"
            }
            cmd = script_map.get(proto, "addws")
            code, out = run_command(cmd, ["3", username, str(days), "100", "2"])

        if code != 0:
            await event.edit(f"❌ **Gagal membuat akun Trial.**\nSystem log:\n`{out[:200]}`")
            return

        # Register creation as trial
        service_name = proto
        import datetime
        expiry_date = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
        register_account_creation(str(sender.id), service_name, username, expiry_date, is_trial=True)

        success_msg = (
            "🎉 **Akun Trial Berhasil Dibuat!**\n\n"
            f"Akun trial VPN Anda telah aktif.\n"
            f"Username: `{username}`\n"
            f"Masa Aktif: `{days} Hari`\n"
            f"Kedaluwarsa: `{expiry_date}`\n\n"
            "Detail akun koneksi:\n"
            f"```\n{out}\n```"
        )
        await event.edit(success_msg, buttons=[[Button.inline("🏠 Main Menu", "start")]])

    except Exception as e:
        logging.exception("Trial execution failed: %s", e)
        await event.edit(f"❌ Terjadi kesalahan internal: {e}")
