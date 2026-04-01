from kyt import *
from kyt.modules.ui import (
    ask_text_clean, build_result, delete_messages, manager_banner, 
    run_command, sanitize_panel_username, sanitize_username, 
    send_account_with_qr, short_progress, upsert_message,
    ask_expiry, ask_config_mode, ask_sni_profile, notify_then_back, back_button,
    ensure_creation_quota, is_admin
)

@bot.on(events.CallbackQuery(data=b'create-trojan'))
async def create_trojan(event):
    async def create_trojan_(event):
        if not await ensure_creation_quota(event, str(sender.id), "xray"):
            return

        msgs_to_del = []
        
        # Username
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Masukkan Username TROJAN:**")
        msgs_to_del.extend(msgs)
        user = sanitize_panel_username(user)
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Username tidak valid. Gunakan huruf/angka/underscore (_), maksimal 32 karakter.")
            return
        
        # Quota
        pw, msgs = await ask_text_clean(event, chat, sender.id, "📦 **Masukkan Quota (GB):**", [])
        msgs_to_del.extend(msgs)
        if not pw:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Quota kosong. Proses dibatalkan.")
            return
        
        # IP Limit
        iplimit, msgs = await ask_text_clean(event, chat, sender.id, "🌐 **Limit IP (kosong=1):**", [])
        msgs_to_del.extend(msgs)
        iplimit = iplimit if iplimit else "1"

        # Masa aktif (tombol)
        exp, msgs = await ask_expiry(event, chat, sender.id, is_trial=False)
        msgs_to_del.extend(msgs)
        if not exp:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return

        # Konfigurasi (TLS / N-TLS / gRPC)
        cfg_mode, msgs = await ask_config_mode(event, chat, sender.id)
        msgs_to_del.extend(msgs)
        if not cfg_mode:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return

        # Profil SNI (tombol)
        sni_profile, msgs = await ask_sni_profile(event, chat, sender.id)
        msgs_to_del.extend(msgs)
        if not sni_profile:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return
        
        # Hapus semua pesan input
        await delete_messages(chat, msgs_to_del)
        
        await upsert_message(event, "⏳ Membuat akun TROJAN...")
        code, a = run_command("addtr", [sni_profile, user, exp, pw, iplimit])
        
        if code != 0:
            if code == 124:
                await upsert_message(event, "❌ Proses create TROJAN timeout. Cek script `addtr` atau format input username.")
            else:
                await upsert_message(event, f"❌ Gagal create TROJAN.\n```\n{a or 'Tidak ada output'}\n```")
        else:
            today = DT.date.today()
            later = today + DT.timedelta(days=int(exp))
            register_account_creation(str(sender.id), "trojan", user, str(later), is_trial=False)
            b = [x.group() for x in re.finditer("trojan://(.*)",a)]
            if len(b) < 2:
                await upsert_message(event, "❌ **Gagal membaca link TROJAN dari panel.**")
                return
            links = {
                "TLS": next((x.replace(" ", "") for x in b if "security=tls" in x and "type=ws" in x), b[0].replace(" ", "")),
                "NTLS": next((x.replace(" ", "") for x in b if "security=none" in x), ""),
                "GRPC": next((x.replace(" ", "") for x in b if "type=grpc" in x), b[-1].replace(" ", "")),
            }
            domain = re.search("@(.*?):",links["TLS"]).group(1)
            uuid = re.search("trojan://(.*?)@",links["TLS"]).group(1)
            selected_links = []
            qr_link = ""
            if cfg_mode == "ALL":
                selected_links = [("TLS/WS", links["TLS"]), ("NTLS/WS", links["NTLS"]), ("gRPC", links["GRPC"])]
                qr_link = links["TLS"]
            elif cfg_mode == "GRPC":
                selected_links = [("gRPC", links["GRPC"])]
                qr_link = links["GRPC"]
            elif cfg_mode == "NTLS":
                selected_links = [("NTLS/WS", links["NTLS"])]
                qr_link = links["NTLS"]
            else:
                selected_links = [("TLS/WS", links["TLS"])]
                qr_link = links["TLS"]
            
            msg = build_result(
                "TROJAN Account Created",
                [
                    ("Username", user),
                    ("Host", domain),
                    ("XRAY DNS", HOST),
                    ("Quota", f"{pw} GB"),
                    ("Limit IP", iplimit),
                    ("Config", cfg_mode),
                    ("Password/UUID", uuid),
                    ("Aktif sampai dengan", str(later)),
                ],
                selected_links + [("OpenClash", f"https://{domain}:81/trojan-{user}.txt")],
            )
            await send_account_with_qr(event, msg, qr_link, f"QR {cfg_mode} TROJAN")
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await create_trojan_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'cek-trojan'))
async def cek_trojan(event):
    async def cek_trojan_(event):
        cmd = 'bot-cek-tr'.strip()
        _, z = run_command(cmd)
        z = z or "Tidak ada sesi login TROJAN aktif."
        await upsert_message(event, f"""

    📋 **TROJAN • Check Login**

{z}

    """, buttons=back_button("trojan"))
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await cek_trojan_(event)
    else:
        await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'list-trojan'))
async def list_trojan(event):
    async def list_trojan_(event):
        if is_admin(sender.id):
            cmd = "grep -E '^### ' /etc/trojan/.trojan.db 2>/dev/null | awk '{printf \"%-20s %s\\n\",$2,$3}'"
            _, out = run_command(cmd)
            if not out:
                out = "Tidak ada user TROJAN."
            await upsert_message(event, f"📋 **Daftar User TROJAN**\n```\n{out}\n```", buttons=back_button("trojan"))
            return

        accounts = get_user_accounts(str(sender.id), service="trojan", active_only=True, limit=120)
        if not accounts:
            await upsert_message(event, "📭 Anda belum memiliki akun TROJAN yang tercatat.", buttons=back_button("trojan"))
            return

        lines = ["📋 **Akun TROJAN Anda**", ""]
        for idx, account in enumerate(accounts, start=1):
            trial = " (TRIAL)" if int(account.get("is_trial", 0) or 0) == 1 else ""
            expires = str(account.get("expires_at") or "-")
            lines.append(f"{idx}. `{account.get('username', '-')}`{trial} - expired `{expires}`")
        text = "\n".join(lines)
        if len(text) > 3900:
            text = text[:3800] + "\n\n..."
        await upsert_message(event, text, buttons=back_button("trojan"))

    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await list_trojan_(event)
    else:
        await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'renew-trojan'))
async def renew_trojan(event):
    async def renew_trojan_(event):
        msgs_to_del = []
        
        # Username
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Masukkan Username TROJAN:**")
        msgs_to_del.extend(msgs)
        user = sanitize_username(user)
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Username tidak valid. Gunakan huruf/angka/._-")
            return

        # Expiry (dengan tombol + custom)
        days, msgs = await ask_expiry(event, chat, sender.id, is_trial=False)
        msgs_to_del.extend(msgs)
        if not days:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return
        
        # Quota
        quota, msgs = await ask_text_clean(event, chat, sender.id, "📦 **Quota baru (GB, kosong=0):**", [])
        msgs_to_del.extend(msgs)
        quota = quota if quota else "0"
        
        # IP Limit
        iplim, msgs = await ask_text_clean(event, chat, sender.id, "🌐 **Limit IP (kosong=1):**", [])
        msgs_to_del.extend(msgs)
        iplim = iplim if iplim else "1"

        # Hapus semua pesan input
        await delete_messages(chat, msgs_to_del)
        
        await upsert_message(event, "⏳ Memperpanjang akun TROJAN...")
        _, out = run_command("renewtr", [user, days, quota, iplim])
        _, exp = run_command(f"grep -wE '^#! {user} ' /etc/xray/config.json | awk '{{print $3}}' | head -n1")
        
        if exp:
            refresh_account_expiry("trojan", user, exp)
            msg = build_result(
                "TROJAN Account Renewed",
                [
                    ("Username", user),
                    ("Added Days", days),
                    ("Quota", f"{quota} GB"),
                    ("Limit IP", iplim),
                    ("Aktif sampai dengan", exp),
                ],
                [("OpenClash", f"https://{DOMAIN}:81/trojan-{user}.txt")],
            )
            await upsert_message(event, msg, buttons=back_button("trojan"))
        else:
            await upsert_message(event, f"⚠️ Perpanjangan diproses, cek output:\n```\n{out or 'Tidak ada output'}\n```", buttons=back_button("trojan"))

    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await renew_trojan_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'trial-trojan'))
async def trial_trojan(event):
    async def trial_trojan_(event):
        if not await ensure_creation_quota(event, str(sender.id), "xray"):
            return

        msgs_to_del = []
        
        # Trial duration (dengan tombol)
        exp, msgs = await ask_expiry(event, chat, sender.id, is_trial=True)
        msgs_to_del.extend(msgs)
        if not exp:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return
        
        # Config Mode (dengan tombol)
        cfg_mode, msgs = await ask_config_mode(event, chat, sender.id)
        msgs_to_del.extend(msgs)
        if not cfg_mode:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return
        
        # Hapus semua pesan input
        await delete_messages(chat, msgs_to_del)
        
        await upsert_message(event, "⏳ Membuat trial TROJAN...")
        code, a = run_command("trialtr", [cfg_mode, exp])
        
        if code != 0:
            await upsert_message(event, "❌ **Gagal membuat trial TROJAN.**")
        else:
            b = [x.group() for x in re.finditer("trojan://(.*)",a)]
            if len(b) < 2:
                await upsert_message(event, "❌ **Gagal membaca link trial TROJAN dari panel.**")
                return
            links = {
                "TLS": next((x.replace(" ", "") for x in b if "security=tls" in x and "type=ws" in x), b[0].replace(" ", "")),
                "NTLS": next((x.replace(" ", "") for x in b if "security=none" in x), ""),
                "GRPC": next((x.replace(" ", "") for x in b if "type=grpc" in x), b[-1].replace(" ", "")),
            }
            remarks = re.search("#(.*)",links["TLS"]).group(1)
            domain = re.search("@(.*?):",links["TLS"]).group(1)
            uuid = re.search("trojan://(.*?)@",links["TLS"]).group(1)
            register_account_creation(str(sender.id), "trojan", remarks, f"{exp} menit", is_trial=True)
            selected_links = []
            qr_link = ""
            if cfg_mode == "ALL":
                selected_links = [("TLS/WS", links["TLS"]), ("NTLS/WS", links["NTLS"]), ("gRPC", links["GRPC"])]
                qr_link = links["TLS"]
            elif cfg_mode == "GRPC":
                selected_links = [("gRPC", links["GRPC"])]
                qr_link = links["GRPC"]
            elif cfg_mode == "NTLS":
                selected_links = [("NTLS/WS", links["NTLS"])]
                qr_link = links["NTLS"]
            else:
                selected_links = [("TLS/WS", links["TLS"])]
                qr_link = links["TLS"]
            
            msg = build_result(
                "TROJAN Trial Created",
                [
                    ("Username", remarks),
                    ("Host", domain),
                    ("Password/UUID", uuid),
                    ("Mode", "Trial"),
                    ("Config", cfg_mode),
                    ("Aktif sampai dengan", f"{exp} menit"),
                ],
                selected_links,
            )
            await send_account_with_qr(event, msg, qr_link, f"QR {cfg_mode} TROJAN Trial")
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await trial_trojan_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'delete-trojan'))
async def delete_trojan(event):
    async def delete_trojan_(event):
        msgs_to_del = []
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username yang akan dihapus:**")
        msgs_to_del.extend(msgs)
        
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return
        
        await delete_messages(chat, msgs_to_del)
        
        cmd = f'printf "%s\n" "{user}" | deltr'
        try:
            a = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
            await upsert_message(event, "**User Not Found**")
        else:
            mark_account_inactive("trojan", user)
            await notify_then_back(event, f"✅ **User `{user}` berhasil dihapus.**", trojan, delay=3)
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await delete_trojan_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'suspend-trojan'))
async def suspend_trojan(event):
    async def suspend_trojan_(event):
        msgs_to_del = []
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username yang akan disuspend:**")
        msgs_to_del.extend(msgs)
        
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return
        
        await delete_messages(chat, msgs_to_del)
        
        cmd = f'printf "%s\n" "{user}" | susptr'
        try:
            a = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
            await upsert_message(event, "**Failed to suspend user**", buttons=back_button("trojan"))
        else:
            await upsert_message(event, f"⛔ **{a.strip()}**", buttons=back_button("trojan"))
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await suspend_trojan_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'unsuspend-trojan'))
async def unsuspend_trojan(event):
    async def unsuspend_trojan_(event):
        msgs_to_del = []
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username yang akan di-unsuspend:**")
        msgs_to_del.extend(msgs)
        
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return
        
        await delete_messages(chat, msgs_to_del)
        
        cmd = f'printf "%s\n" "{user}" | unsusptr'
        try:
            a = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
            await upsert_message(event, "**Failed to unsuspend user**", buttons=back_button("trojan"))
        else:
            await upsert_message(event, f"✅ **{a.strip()}**", buttons=back_button("trojan"))
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await unsuspend_trojan_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'trojan'))
async def trojan(event):
    async def trojan_(event):
        if is_admin(sender.id):
            inline = [
                [Button.inline("🧪 Trial", "trial-trojan"), Button.inline("➕ Create", "create-trojan")],
                [Button.inline("👀 Check Login", "cek-trojan"), Button.inline("📋 List User", "list-trojan")],
                [Button.inline("🗓️ Renew", "renew-trojan"), Button.inline("🗑️ Delete", "delete-trojan")],
                [Button.inline("⛔ Suspend", "suspend-trojan"), Button.inline("✅ Unsuspend", "unsuspend-trojan")],
                [Button.inline("⬅️ Main Menu", "menu")],
            ]
        else:
            inline = [
                [Button.inline("🧪 Trial", "trial-trojan"), Button.inline("➕ Create", "create-trojan")],
                [Button.inline("📋 Akun Saya", "list-trojan")],
                [Button.inline("📨 Request Kuota", "quota-request")],
                [Button.inline("⬅️ Main Menu", "menu")],
            ]
        msg = manager_banner("TROJAN Manager", "TROJAN")
        await event.edit(msg,buttons=inline)
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await trojan_(event)
    else:
        await event.answer("Access Denied",alert=True)
