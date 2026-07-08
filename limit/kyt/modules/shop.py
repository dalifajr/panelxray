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
        buttons = [[Button.inline("🏠 Menu Utama", "start")]]
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



    inline.append([Button.inline("🏠 Menu Utama", "start")])

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
        [Button.inline(f"📅 90 Hari — Rp {price*3:,}", f"buy-pkg:{proto}:90:{price*3}")]
    ]

    if str(config.get("bot_trial_enabled", "false")).lower() == "true":
        trial_days = config.get("bot_trial_days", 1)
        inline.append([Button.inline(f"✨ Coba Gratis (Trial {trial_days} Hari)", f"buy-pkg:{proto}:{trial_days}:0:trial")])

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

    await start_purchase_flow(event, proto, days, price)


async def start_purchase_flow(event, proto, days, price):
    sender = await event.get_sender()
    chat = event.chat_id

    # Removed early balance check to allow QRIS direct checkout

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

    if proto in ["ssh", "trial"]:
        # No IP limit for SSH
        await _show_payment_methods(event, chat, proto, days, price, user, 1, price)
    else:
        # Show IP Limit Selector
        await _show_ip_limit_selector(event, chat, proto, days, price, user, 1)


async def _show_ip_limit_selector(event, chat, proto, days, base_price, user, iplimit):
    pricing_res = api_call("GET", "/pricing")
    prices = pricing_res.get("prices", [])
    extra_ip_price = 0
    for p in prices:
        if p.get("protocol") == "add_ip":
            extra_ip_price = p.get("price", 0)

    # Calculate total
    extra_ips = max(0, iplimit - 1)
    total_price = base_price + (extra_ips * extra_ip_price)

    msg = (
        f"⚙️ **Atur Limit IP Device**\n\n"
        f"▪ Layanan: `{proto.upper()}`\n"
        f"▪ Username: `{user}`\n"
        f"▪ Harga Dasar: `Rp {base_price:,}`\n"
        f"▪ Limit IP Saat Ini: `{iplimit} IP`\n"
        f"▪ Tambahan Harga: `Rp {(extra_ips * extra_ip_price):,}`\n"
        f"▪ **Total Harga:** `Rp {total_price:,}`\n\n"
        "Silakan atur limit IP yang Anda inginkan:"
    )

    prev_ip = max(1, iplimit - 1)
    next_ip = iplimit + 1

    inline = [
        [
            Button.inline("➖", f"ip-lim:{proto}:{days}:{base_price}:{user}:{prev_ip}"),
            Button.inline(f"{iplimit} IP", "ignore"),
            Button.inline("➕", f"ip-lim:{proto}:{days}:{base_price}:{user}:{next_ip}")
        ],
        [Button.inline("✅ Konfirmasi & Pilih Pembayaran", f"pay-meth:{proto}:{days}:{base_price}:{user}:{iplimit}")],
        [Button.inline("❌ Batal", "shop-menu")]
    ]
    
    await upsert_message(event, msg, buttons=inline)

@bot.on(events.CallbackQuery(data=re.compile(b'ip-lim:(.*?):(.*?):(.*?):(.*?):(.*)')))
async def handle_ip_lim(event):
    proto = event.pattern_match.group(1).decode('utf-8')
    days = int(event.pattern_match.group(2).decode('utf-8'))
    base_price = int(event.pattern_match.group(3).decode('utf-8'))
    user = event.pattern_match.group(4).decode('utf-8')
    iplimit = int(event.pattern_match.group(5).decode('utf-8'))
    await _show_ip_limit_selector(event, event.chat_id, proto, days, base_price, user, iplimit)


@bot.on(events.CallbackQuery(data=re.compile(b'pay-meth:(.*?):(.*?):(.*?):(.*?):(.*)')))
async def handle_pay_meth(event):
    proto = event.pattern_match.group(1).decode('utf-8')
    days = int(event.pattern_match.group(2).decode('utf-8'))
    base_price = int(event.pattern_match.group(3).decode('utf-8'))
    user = event.pattern_match.group(4).decode('utf-8')
    iplimit = int(event.pattern_match.group(5).decode('utf-8'))

    if proto not in ["ssh", "trial"]:
        msg = "🌐 **Pilih Profil SNI (Bug):**"
        inline = [
            [Button.inline("support.zoom.us", f"conf-sni:{proto}:{days}:{base_price}:{user}:{iplimit}:1")],
            [Button.inline("live.iflix.com", f"conf-sni:{proto}:{days}:{base_price}:{user}:{iplimit}:2")],
            [Button.inline("Tanpa SNI", f"conf-sni:{proto}:{days}:{base_price}:{user}:{iplimit}:3")],
            [Button.inline("❌ Batal", "shop-menu")]
        ]
        await upsert_message(event, msg, buttons=inline)
    else:
        pricing_res = api_call("GET", "/pricing")
        extra_ip_price = next((p.get("price", 0) for p in pricing_res.get("prices", []) if p.get("protocol") == "add_ip"), 0)
        total_price = base_price + (max(0, iplimit - 1) * extra_ip_price)
        await _show_payment_methods(event, event.chat_id, proto, days, base_price, user, iplimit, total_price, sni_profile="3")

@bot.on(events.CallbackQuery(data=re.compile(b'conf-sni:(.*?):(.*?):(.*?):(.*?):(.*?):(.*)')))
async def handle_conf_sni(event):
    proto = event.pattern_match.group(1).decode('utf-8')
    days = int(event.pattern_match.group(2).decode('utf-8'))
    base_price = int(event.pattern_match.group(3).decode('utf-8'))
    user = event.pattern_match.group(4).decode('utf-8')
    iplimit = int(event.pattern_match.group(5).decode('utf-8'))
    sni_profile = event.pattern_match.group(6).decode('utf-8')

    pricing_res = api_call("GET", "/pricing")
    extra_ip_price = next((p.get("price", 0) for p in pricing_res.get("prices", []) if p.get("protocol") == "add_ip"), 0)
    total_price = base_price + (max(0, iplimit - 1) * extra_ip_price)

    await _show_payment_methods(event, event.chat_id, proto, days, base_price, user, iplimit, total_price, sni_profile)

async def _show_payment_methods(event, chat, proto, days, base_price, user, iplimit, total_price, sni_profile="3"):
    sni_name = "support.zoom.us" if sni_profile == "1" else ("live.iflix.com" if sni_profile == "2" else "Tanpa SNI")
    confirm_msg = (
        "🛒 **Konfirmasi Pembelian & Pembayaran**\n\n"
        f"▪ Layanan: `{proto.upper() if proto != 'trial' else 'TRIAL'}`\n"
        f"▪ Username: `{user}`\n"
        f"▪ Masa Aktif: `{days} Hari`\n"
        f"▪ Limit IP: `{iplimit} IP`\n"
        f"▪ SNI/Bug: `{sni_name}`\n"
        f"▪ **Total Pembayaran:** `Rp {total_price:,}`\n\n"
        "Silakan pilih metode pembayaran:"
    )

    inline = []
    if total_price > 0:
        inline.append([Button.inline(f"💳 Bayar via Saldo (Rp {total_price:,})", f"confirm-buy:{proto}:{days}:{total_price}:{user}:{iplimit}:{sni_profile}:saldo")])
        inline.append([Button.inline(f"📱 Bayar via QRIS (Rp {total_price:,})", f"confirm-buy:{proto}:{days}:{total_price}:{user}:{iplimit}:{sni_profile}:qris")])
    else:
        inline.append([Button.inline("✅ Konfirmasi Gratis", f"confirm-buy:{proto}:{days}:0:{user}:{iplimit}:{sni_profile}:saldo")])
        
    inline.append([Button.inline("❌ Batal", "shop-menu")])

    if isinstance(event, events.CallbackQuery):
        await upsert_message(event, confirm_msg, buttons=inline)
    else:
        await bot.send_message(chat, confirm_msg, buttons=inline)


@bot.on(events.CallbackQuery(data=re.compile(b'confirm-buy:(.*?):(.*?):(.*?):(.*?):(.*?):(.*?):(.*)')))
async def confirm_buy(event):
    sender = await event.get_sender()
    chat = event.chat_id

    proto = event.pattern_match.group(1).decode('utf-8')
    days = int(event.pattern_match.group(2).decode('utf-8'))
    price = int(event.pattern_match.group(3).decode('utf-8'))
    user = event.pattern_match.group(4).decode('utf-8')
    iplimit = event.pattern_match.group(5).decode('utf-8')
    sni_profile = event.pattern_match.group(6).decode('utf-8')
    method = event.pattern_match.group(7).decode('utf-8')

    async def execute_vpn_creation(msg_ref=None):
        try:
            if msg_ref is None:
                msg_ref = event
                await msg_ref.edit("⏳ **Memproses pembuatan akun VPN Anda...**\nMohon tunggu beberapa detik.")
            else:
                try:
                    await msg_ref.edit("⏳ **Pembayaran Berhasil! Memproses pembuatan akun VPN Anda...**\nMohon tunggu beberapa detik.")
                except: pass

            import asyncio
            domain = globals().get("DOMAIN", "localhost")
            is_trial = (proto == "trial")
            real_proto = proto if proto != "trial" else "ssh"
            
            if real_proto == "ssh":
                password = "".join(random.choices("0123456789", k=6))
                code, out = await asyncio.to_thread(run_command, "addssh", [user, password, str(days)])
            else:
                script_map = {"vmess": "addws", "vless": "addvless", "trojan": "addtr", "shadowsocks": "addss"}
                cmd = script_map.get(real_proto, "addws")
                code, out = await asyncio.to_thread(run_command, cmd, [sni_profile, user, str(days), "0", str(iplimit)])

            if code != 0:
                if price > 0:
                    api_call("POST", "/wallet/debit", {
                        "tg_id": str(event.sender_id),
                        "amount": -price,
                        "description": f"Refund: Gagal pembuatan akun {real_proto.upper()} {user}"
                    })
                err_msg = f"❌ **Gagal membuat akun VPN.**\nSystem log:\n`{out[:200]}`"
                if price > 0: err_msg += "\n\nSaldo Anda telah dikembalikan."
                try:
                    await msg_ref.edit(err_msg)
                except Exception:
                    await bot.send_message(chat, err_msg)
                return

            import datetime
            import re
            
            expiry_date = (datetime.date.today() + datetime.timedelta(days=days)).isoformat()
            register_account_creation(str(event.sender_id), real_proto, user, expiry_date, is_trial=is_trial)

            # Strip ANSI escape codes
            clean_out = re.sub(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', out).strip()
            
            if real_proto == "ssh":
                import html
                def esc(text): return html.escape(str(text))
                def extract_ssh_val(key_regex):
                    m = re.search(fr"\b(?:{key_regex})\b\s*:\s*(.+)", clean_out, re.IGNORECASE)
                    return m.group(1).strip() if m else "-"

                ssh_user = extract_ssh_val("Username")
                if ssh_user == "-": ssh_user = user
                ssh_pass = extract_ssh_val("Password")
                ssh_domain = extract_ssh_val("Host")
                ssh_ip = extract_ssh_val("Limit Ip").replace(" User", "").strip()
                ssh_exp = extract_ssh_val("Berakhir Pada")

                success_msg = (
                    f"✅ <b>SSH Account Created</b>\n\n"
                    f"▸ <b>Username:</b> <code>{esc(ssh_user)}</code>\n"
                    f"▸ <b>Password:</b> <code>{esc(ssh_pass)}</code>\n"
                    f"▸ <b>Domain:</b> <code>{esc(ssh_domain)}</code>\n"
                    f"▸ <b>port:</b> 80,443\n"
                    f"▸ <b>Quota:</b> unlimited\n"
                    f"▸ <b>Limit IP:</b> {esc(ssh_ip)}\n"
                    f"▸ <b>Aktif sampai dengan:</b> {esc(ssh_exp)}\n\n"
                    f"🏠 Ketik /start untuk kembali ke menu utama."
                )
                parse_m = 'html'
            else:
                import html
                def esc(text): return html.escape(str(text))
                def extract_val(key_regex):
                    m = re.search(fr"\b(?:{key_regex})\b\s*:\s*(.+)", clean_out, re.IGNORECASE)
                    return m.group(1).strip() if m else "-"

                remarks = extract_val("Remarks")
                if remarks == "-": remarks = user
                domain_vpn = extract_val("Domain")
                quota = extract_val("User Quota")
                if quota == "0 GB" or quota == "0" or quota == "0GB":
                    quota = "Unlimited"
                iplim_val = extract_val("User Ip")
                if iplim_val == "-": iplim_val = extract_val("Limit IP")
                uuid_val = extract_val("id")
                if uuid_val == "-": uuid_val = extract_val("Password")
                exp_date = extract_val("Berakhir Pada")
                
                link_tls = extract_val(r"Link TLS|Link WS TLS")
                link_ntls = extract_val(r"Link none TLS|Link WS None TLS")
                link_grpc = extract_val("Link GRPC")
                openclash = extract_val("Format OpenClash")
                
                xray_dns = globals().get("NS", "-")
                sni_n = "support.zoom.us" if sni_profile == "1" else ("live.iflix.com" if sni_profile == "2" else "")
                full_domain = f"{sni_n}.{domain_vpn}" if sni_n and domain_vpn != "-" else domain_vpn

                success_msg = (
                    f"✅ <b>{real_proto.upper()} Account Created</b>\n\n"
                    f"▸ <b>Username:</b> <code>{esc(remarks)}</code>\n"
                    f"▸ <b>Domain:</b> <code>{esc(full_domain)}</code>\n"
                    f"▸ <b>XRAY DNS:</b> <code>{esc(xray_dns)}</code>\n"
                    f"▸ <b>Quota:</b> {esc(quota)}\n"
                    f"▸ <b>Limit IP:</b> {esc(iplim_val)}\n"
                    f"▸ <b>Config:</b> TLS / NTLS / GRPC\n"
                    f"▸ <b>User ID:</b> <code>{esc(uuid_val)}</code>\n"
                    f"▸ <b>Aktif sampai:</b> {esc(exp_date)}\n\n"
                    f"🔗 <b>Connection Links</b>\n"
                )
                if link_tls != "-": success_msg += f"▪ <b>TLS:</b>\n<code>{esc(link_tls)}</code>\n\n"
                if link_ntls != "-": success_msg += f"▪ <b>NTLS:</b>\n<code>{esc(link_ntls)}</code>\n\n"
                if link_grpc != "-": success_msg += f"▪ <b>GRPC:</b>\n<code>{esc(link_grpc)}</code>\n\n"
                if openclash != "-": success_msg += f"▪ <b>OpenClash:</b>\n<a href='{esc(openclash)}'>{esc(openclash)}</a>\n\n"

                photo = None
                if link_tls != "-":
                    try:
                        import subprocess
                        import os
                        import io
                        qr_path = f"/tmp/qr-{user}.png"
                        os.makedirs("/tmp", exist_ok=True)
                        proc = await asyncio.to_thread(subprocess.run, ["qrencode", "-o", qr_path, link_tls], capture_output=True, timeout=5)
                        if proc.returncode != 0:
                            if os.path.exists("/usr/bin/apt-get"):
                                await asyncio.to_thread(subprocess.run, "apt-get update && apt-get install -y qrencode", shell=True, capture_output=True, timeout=30)
                            elif os.path.exists("/usr/bin/yum"):
                                await asyncio.to_thread(subprocess.run, "yum install -y qrencode", shell=True, capture_output=True, timeout=30)
                            proc = await asyncio.to_thread(subprocess.run, ["qrencode", "-o", qr_path, link_tls], capture_output=True, timeout=5)
                        if proc.returncode == 0 and os.path.exists(qr_path):
                            with open(qr_path, "rb") as f:
                                photo = io.BytesIO(f.read())
                                photo.name = "qr-code.png"
                            os.remove(qr_path)
                    except Exception as e:
                        logging.exception("Failed to generate local QR code: %s", e)
                
                if not photo and link_tls != "-":
                    try:
                        from kyt.modules.ui import get_qr_url
                        qr_url = get_qr_url(link_tls, 512)
                        success_msg += f"🧾 <b>QR TLS/Koneksi</b>\n🔗 <a href='{esc(qr_url)}'>Klik di sini untuk Scan QR</a>\n\n"
                    except Exception:
                        success_msg += (
                            "🧾 <b>QR TLS/Koneksi</b>\n"
                            "🔐 Scan QR yang diberikan untuk koneksi, atau copy link di atas.\n\n"
                        )
                elif not photo:
                    success_msg += (
                        "🧾 <b>QR TLS/Koneksi</b>\n"
                        "🔐 Scan QR yang diberikan untuk koneksi, atau copy link di atas.\n\n"
                    )

                success_msg += "🏠 Ketik /start untuk kembali ke menu utama."
                parse_m = 'html'

            buttons = [[Button.inline("⬅️ Beli Lagi", "shop-menu"), Button.inline("🏠 Menu Utama", "start")]]
            try:
                if photo:
                    await bot.send_message(chat, success_msg, file=photo, buttons=buttons, parse_mode=parse_m)
                    try: await msg_ref.delete()
                    except: pass
                elif getattr(msg_ref, 'media', None):
                    await bot.send_message(chat, success_msg, buttons=buttons, parse_mode=parse_m)
                    try: await msg_ref.delete()
                    except: pass
                else:
                    await msg_ref.edit(success_msg, buttons=buttons, parse_mode=parse_m)
            except Exception as e:
                logging.exception("Failed to send success message with photo: %s", e)
                try:
                    await bot.send_message(chat, success_msg, buttons=buttons, parse_mode=parse_m)
                    try: await msg_ref.delete()
                    except: pass
                except Exception as e2:
                    logging.exception("Failed to send fallback success message: %s", e2)
                    raise e2
        except Exception as e:
            logging.exception("Purchase execution failed: %s", e)
            try:
                await msg_ref.edit(f"❌ Terjadi kesalahan internal: {e}")
            except:
                await bot.send_message(chat, f"❌ Terjadi kesalahan internal: {e}")

    if method == "saldo":
        if price > 0:
            desc = f"Pembelian akun {proto.upper()} username {user} ({days} hari) via Bot Telegram"
            debit_res = api_call("POST", "/wallet/debit", {
                "tg_id": str(event.sender_id),
                "amount": price,
                "description": desc
            })
            if "error" in debit_res:
                await event.answer(f"❌ Transaksi gagal: {debit_res['error']}", alert=True)
                return
        await execute_vpn_creation()

    elif method == "qris":
        await event.edit("⏳ **Menyiapkan QRIS Pembelian Anda...**")
        res = api_call("POST", "/wallet/vpn_qris", {
            "tg_id": str(event.sender_id), 
            "amount": price,
            "protocol": proto,
            "days": days,
            "ip_limit": iplimit
        })
        if "error" in res:
            await event.edit(f"❌ **Gagal menyiapkan QRIS:**\n`{res['error']}`", buttons=[[Button.inline("⬅️ Kembali", "shop-menu")]])
            return

        qr_url = res.get("qr_code_url")
        total_amount = res.get("total_amount")
        ref = res.get("reference")

        payment_instructions = (
            "💳 **PEMBAYARAN QRIS OTOMATIS**\n\n"
            f"▪ Pembelian: `{proto.upper()} ({days} Hari, {iplimit} IP)`\n"
            f"▪ ID Referensi: `{ref}`\n"
            f"⚠️ **TOTAL PEMBAYARAN:** `Rp {total_amount:,}`\n\n"
            "**PENTING:** Scan QR Code ini dan pastikan membayar **EXACTLY / SAMA PERSIS** agar otomatis masuk!"
        )

        buttons = [
            [Button.inline("🔄 Cek Status", f"check-topup:{ref}"), Button.inline("❌ Batalkan", f"cancel-topup:{ref}")],
            [Button.inline("🏠 Menu Utama", "start")]
        ]
        try:
            sent_msg = await bot.send_file(chat, qr_url, caption=payment_instructions, buttons=buttons)
        except:
            sent_msg = await bot.send_message(chat, payment_instructions + f"\n\n🔗 [Link QR]({qr_url})", buttons=buttons)

        import asyncio
        async def poll_purchase_transaction():
            for _ in range(120):
                await asyncio.sleep(5)
                status_res = api_call("GET", f"/transaction/status/{ref}")
                if "error" not in status_res:
                    if status_res.get("status") == "success":
                        await execute_vpn_creation(msg_ref=sent_msg)
                        return
                    elif status_res.get("status") == "cancelled":
                        return
            api_call("POST", "/transaction/cancel", {"reference": ref})
            try: await sent_msg.edit(f"❌ Waktu pembayaran habis untuk transaksi `{ref}`.", buttons=[[Button.inline("🏠 Menu Utama", "start")]])
            except: pass

        bot.loop.create_task(poll_purchase_transaction())
