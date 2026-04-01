from kyt import *
from kyt.modules.ui import (
    ask_text_clean, build_result, delete_messages, manager_banner, 
    run_command, sanitize_panel_username, sanitize_username, 
    send_account_with_qr, short_progress, upsert_message,
    ask_expiry, ask_config_mode, ask_sni_profile, notify_then_back, back_button,
    ensure_creation_quota, is_admin
)

@bot.on(events.CallbackQuery(data=b'create-vless'))
async def create_vless(event):
    async def create_vless_(event):
        if not await ensure_creation_quota(event, str(sender.id), "xray"):
            return

        msgs_to_del = []
        
        # Username
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Masukkan Username VLESS:**")
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
        
        await upsert_message(event, "⏳ Membuat akun VLESS...")
        code, a = run_command("addvless", [sni_profile, user, exp, pw, iplimit])
        
        if code != 0:
            if code == 124:
                await upsert_message(event, "❌ Proses create VLESS timeout. Cek script `addvless` atau format input username.")
            else:
                await upsert_message(event, f"❌ Gagal create VLESS.\n```\n{a or 'Tidak ada output'}\n```")
        else:
            today = DT.date.today()
            later = today + DT.timedelta(days=int(exp))
            register_account_creation(str(sender.id), "vless", user, str(later), is_trial=False)
            x = [x.group() for x in re.finditer("vless://(.*)",a)]
            if len(x) < 3:
                await upsert_message(event, "❌ **Gagal membaca link VLESS dari panel.**")
                return
            uuid = re.search("vless://(.*?)@",x[0]).group(1)
            links = {
                "TLS": x[0].replace(" ", ""),
                "NTLS": x[1].replace(" ", ""),
                "GRPC": x[2].replace(" ", ""),
            }
            selected_links = []
            qr_link = ""
            if cfg_mode == "ALL":
                selected_links = [("TLS", links["TLS"]), ("NTLS", links["NTLS"]), ("gRPC", links["GRPC"])]
                qr_link = links["TLS"]
            elif cfg_mode == "GRPC":
                selected_links = [("gRPC", links["GRPC"])]
                qr_link = links["GRPC"]
            elif cfg_mode == "NTLS":
                selected_links = [(cfg_mode, links[cfg_mode])]
                qr_link = links["NTLS"]
            else:
                selected_links = [(cfg_mode, links[cfg_mode])]
                qr_link = links["TLS"]
            
            msg = build_result(
                "VLESS Account Created",
                [
                    ("Username", user),
                    ("Host", DOMAIN),
                    ("XRAY DNS", HOST),
                    ("Quota", f"{pw} GB"),
                    ("Limit IP", iplimit),
                    ("Config", cfg_mode),
                    ("UUID", uuid),
                    ("Aktif sampai dengan", str(later)),
                ],
                selected_links + [("OpenClash", f"https://{DOMAIN}:81/vless-{user}.txt")],
            )
            await send_account_with_qr(event, msg, qr_link, f"QR {cfg_mode} VLESS")
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await create_vless_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'cek-vless'))
async def cek_vless(event):
    async def cek_vless_(event):
        cmd = 'bot-cek-vless'.strip()
        _, z = run_command(cmd)
        z = z or "Tidak ada sesi login VLESS aktif."
        await upsert_message(event, f"""

    📋 **VLESS • Check Login**

{z}

    """, buttons=back_button("vless"))
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await cek_vless_(event)
    else:
        await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'list-vless'))
async def list_vless(event):
    async def list_vless_(event):
        if is_admin(sender.id):
            cmd = "grep -E '^### ' /etc/vless/.vless.db 2>/dev/null | awk '{printf \"%-20s %s\\n\",$2,$3}'"
            _, out = run_command(cmd)
            if not out:
                out = "Tidak ada user VLESS."
            await upsert_message(event, f"📋 **Daftar User VLESS**\n```\n{out}\n```", buttons=back_button("vless"))
            return

        accounts = get_user_accounts(str(sender.id), service="vless", active_only=True, limit=120)
        if not accounts:
            await upsert_message(event, "📭 Anda belum memiliki akun VLESS yang tercatat.", buttons=back_button("vless"))
            return

        lines = ["📋 **Akun VLESS Anda**", ""]
        for idx, account in enumerate(accounts, start=1):
            trial = " (TRIAL)" if int(account.get("is_trial", 0) or 0) == 1 else ""
            expires = str(account.get("expires_at") or "-")
            lines.append(f"{idx}. `{account.get('username', '-')}`{trial} - expired `{expires}`")
        text = "\n".join(lines)
        if len(text) > 3900:
            text = text[:3800] + "\n\n..."
        await upsert_message(event, text, buttons=back_button("vless"))

    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await list_vless_(event)
    else:
        await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'renew-vless'))
async def renew_vless(event):
    async def renew_vless_(event):
        msgs_to_del = []
        
        # Username
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Masukkan Username VLESS:**")
        msgs_to_del.extend(msgs)
        user = sanitize_username(user)
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Username tidak valid. Gunakan huruf/angka/._-")
            return

        if not is_admin(sender.id) and not user_owns_account(str(sender.id), "vless", user, active_only=True):
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "⛔ Anda hanya bisa renew akun VLESS milik Anda sendiri.")
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
        
        await upsert_message(event, "⏳ Memperpanjang akun VLESS...")
        _, out = run_command("renewvless", [user, days, quota, iplim])
        _, exp = run_command(f"grep -wE '^#& {user} ' /etc/xray/config.json | awk '{{print $3}}' | head -n1")
        
        if exp:
            refresh_account_expiry("vless", user, exp)
            msg = build_result(
                "VLESS Account Renewed",
                [
                    ("Username", user),
                    ("Added Days", days),
                    ("Quota", f"{quota} GB"),
                    ("Limit IP", iplim),
                    ("Aktif sampai dengan", exp),
                ],
                [("OpenClash", f"https://{DOMAIN}:81/vless-{user}.txt")],
            )
            await upsert_message(event, msg, buttons=back_button("vless"))
        else:
            await upsert_message(event, f"⚠️ Perpanjangan diproses, cek output:\n```\n{out or 'Tidak ada output'}\n```", buttons=back_button("vless"))

    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await renew_vless_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'delete-vless'))
async def delete_vless(event):
    async def delete_vless_(event):
        msgs_to_del = []
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username yang akan dihapus:**")
        msgs_to_del.extend(msgs)
        user = sanitize_username(user)
        
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return

        if not is_admin(sender.id) and not user_owns_account(str(sender.id), "vless", user, active_only=True):
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "⛔ Anda hanya bisa menghapus akun VLESS milik Anda sendiri.")
            return
        
        await delete_messages(chat, msgs_to_del)
        
        cmd = f'printf "%s\n" "{user}" | delvless'
        try:
            a = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
            await upsert_message(event, "**User Not Found**")
        else:
            mark_account_inactive("vless", user)
            await notify_then_back(event, f"✅ **User `{user}` berhasil dihapus.**", vless, delay=3)
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await delete_vless_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'suspend-vless'))
async def suspend_vless(event):
    async def suspend_vless_(event):
        msgs_to_del = []
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username yang akan disuspend:**")
        msgs_to_del.extend(msgs)
        user = sanitize_username(user)
        
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return

        if not is_admin(sender.id) and not user_owns_account(str(sender.id), "vless", user, active_only=True):
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "⛔ Anda hanya bisa suspend akun VLESS milik Anda sendiri.")
            return
        
        await delete_messages(chat, msgs_to_del)
        
        cmd = f'printf "%s\n" "{user}" | suspvless'
        try:
            a = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
            await upsert_message(event, "**Failed to suspend user**", buttons=back_button("vless"))
        else:
            await upsert_message(event, f"⛔ **{a.strip()}**", buttons=back_button("vless"))
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await suspend_vless_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'unsuspend-vless'))
async def unsuspend_vless(event):
    async def unsuspend_vless_(event):
        msgs_to_del = []
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username yang akan di-unsuspend:**")
        msgs_to_del.extend(msgs)
        user = sanitize_username(user)
        
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return

        if not is_admin(sender.id) and not user_owns_account(str(sender.id), "vless", user, active_only=True):
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "⛔ Anda hanya bisa unsuspend akun VLESS milik Anda sendiri.")
            return
        
        await delete_messages(chat, msgs_to_del)
        
        cmd = f'printf "%s\n" "{user}" | unsuspvless'
        try:
            a = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
            await upsert_message(event, "**Failed to unsuspend user**", buttons=back_button("vless"))
        else:
            await upsert_message(event, f"✅ **{a.strip()}**", buttons=back_button("vless"))
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await unsuspend_vless_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'trial-vless'))
async def trial_vless(event):
    async def trial_vless_(event):
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
        
        await upsert_message(event, "⏳ Membuat trial VLESS...")
        code, a = run_command("trialvless", [cfg_mode, exp])
        
        if code != 0:
            await upsert_message(event, "❌ **Gagal membuat trial VLESS.**")
        else:
            x = [x.group() for x in re.finditer("vless://(.*)",a)]
            if len(x) < 3:
                await upsert_message(event, "❌ **Gagal membaca link trial VLESS dari panel.**")
                return
            remarks = re.search("#(.*)",x[0]).group(1)
            uuid = re.search("vless://(.*?)@",x[0]).group(1)
            register_account_creation(str(sender.id), "vless", remarks, f"{exp} menit", is_trial=True)
            links = {
                "TLS": x[0].replace(" ", ""),
                "NTLS": x[1].replace(" ", ""),
                "GRPC": x[2].replace(" ", ""),
            }
            selected_links = []
            qr_link = ""
            if cfg_mode == "ALL":
                selected_links = [("TLS", links["TLS"]), ("NTLS", links["NTLS"]), ("gRPC", links["GRPC"])]
                qr_link = links["TLS"]
            elif cfg_mode == "GRPC":
                selected_links = [("gRPC", links["GRPC"])]
                qr_link = links["GRPC"]
            elif cfg_mode == "NTLS":
                selected_links = [(cfg_mode, links[cfg_mode])]
                qr_link = links["NTLS"]
            else:
                selected_links = [(cfg_mode, links[cfg_mode])]
                qr_link = links["TLS"]
            
            msg = build_result(
                "VLESS Trial Created",
                [
                    ("Username", remarks),
                    ("Host", DOMAIN),
                    ("UUID", uuid),
                    ("Mode", "Trial"),
                    ("Config", cfg_mode),
                    ("Aktif sampai dengan", f"{exp} menit"),
                ],
                selected_links,
            )
            await send_account_with_qr(event, msg, qr_link, f"QR {cfg_mode} VLESS Trial")
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await trial_vless_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'vless'))
async def vless(event):
    async def vless_(event):
        if is_admin(sender.id):
            inline = [
                [Button.inline("🧪 Trial", "trial-vless"), Button.inline("➕ Create", "create-vless")],
                [Button.inline("👀 Check Login", "cek-vless"), Button.inline("📋 List User", "list-vless")],
                [Button.inline("🗓️ Renew", "renew-vless"), Button.inline("🗑️ Delete", "delete-vless")],
                [Button.inline("⛔ Suspend", "suspend-vless"), Button.inline("✅ Unsuspend", "unsuspend-vless")],
                [Button.inline("⬅️ Main Menu", "menu")],
            ]
        else:
            inline = [
                [Button.inline("🧪 Trial", "trial-vless"), Button.inline("➕ Create", "create-vless")],
                [Button.inline("📋 Akun Saya", "list-vless")],
                [Button.inline("🗓️ Renew", "renew-vless"), Button.inline("🗑️ Delete", "delete-vless")],
                [Button.inline("⛔ Suspend", "suspend-vless"), Button.inline("✅ Unsuspend", "unsuspend-vless")],
                [Button.inline("📨 Request Kuota", "quota-request")],
                [Button.inline("⬅️ Main Menu", "menu")],
            ]
        msg = manager_banner("VLESS Manager", "VLESS")
        await event.edit(msg,buttons=inline)
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await vless_(event)
    else:
        await event.answer("Access Denied",alert=True)
