from kyt import *
from kyt.modules.ui import (
    ask_text_clean, build_result, delete_messages, manager_banner, 
    run_command, sanitize_panel_username, sanitize_username, 
    send_account_with_qr, short_progress, upsert_message,
    ask_expiry, ask_config_mode, ask_sni_profile, notify_then_back, back_button,
    ensure_creation_quota, is_admin, ask_renew_account
)

BOT_DOMAIN = str(globals().get("DOMAIN", globals().get("domain", "-")))
BOT_HOST = str(globals().get("HOST", globals().get("NS", BOT_DOMAIN)))

#CREATE VMESS
@bot.on(events.CallbackQuery(data=b'create-vmess'))
async def create_vmess(event):
    async def create_vmess_(event):
        if not await ensure_creation_quota(event, str(sender.id), "xray"):
            return

        msgs_to_del = []
        
        # Username
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Masukkan Username VMESS:**")
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
        
        # Hapus semua pesan input sebelum proses
        await delete_messages(chat, msgs_to_del)
        
        await upsert_message(event, "⏳ Membuat akun VMESS...")
        code, a = run_command("addws", [sni_profile, user, exp, pw, iplimit])
        
        if code != 0:
            if code == 124:
                await upsert_message(event, "❌ Proses create VMESS timeout. Cek script `addws` atau format input username.")
            else:
                await upsert_message(event, f"❌ Gagal create VMESS.\n```\n{a or 'Tidak ada output'}\n```")
        else:
            today = DT.date.today()
            later = today + DT.timedelta(days=int(exp))
            register_account_creation(str(sender.id), "vmess", user, str(later), is_trial=False)
            b = [x.group() for x in re.finditer("vmess://(.*)",a)]
            if len(b) < 3:
                await upsert_message(event, "❌ **Gagal membaca link VMESS dari panel.**")
                return
            z = base64.b64decode(b[0].replace("vmess://","")).decode("ascii")
            z = json.loads(z)
            links = {
                "TLS": b[0].strip("'").replace(" ", ""),
                "NTLS": b[1].strip("'").replace(" ", ""),
                "GRPC": b[2].strip("'"),
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
                "VMESS Account Created",
                [
                    ("Username", z["ps"]),
                    ("Domain", z["add"]),
                    ("XRAY DNS", BOT_HOST),
                    ("Quota", f"{pw} GB"),
                    ("Limit IP", iplimit),
                    ("Config", cfg_mode),
                    ("User ID", z["id"]),
                    ("Aktif sampai dengan", str(later)),
                ],
                selected_links + [("OpenClash", f"https://{BOT_DOMAIN}:81/vmess-{user}.txt")],
            )
            await send_account_with_qr(event, msg, qr_link, f"QR {cfg_mode} VMESS")
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await create_vmess_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

# TRIAL VMESS
@bot.on(events.CallbackQuery(data=b'trial-vmess'))
async def trial_vmess(event):
    async def trial_vmess_(event):
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
        
        await upsert_message(event, "⏳ Membuat trial VMESS...")
        code, a = run_command("trialws", [cfg_mode, exp])
        
        if code != 0:
            await upsert_message(event, "❌ **Gagal membuat trial VMESS.**")
        else:
            b = [x.group() for x in re.finditer("vmess://(.*)",a)]
            if len(b) < 3:
                await upsert_message(event, "❌ **Gagal membaca link trial VMESS dari panel.**")
                return
            z = base64.b64decode(b[0].replace("vmess://","")).decode("ascii")
            z = json.loads(z)
            register_account_creation(str(sender.id), "vmess", z.get("ps", "trial-vmess"), f"{exp} menit", is_trial=True)
            links = {
                "TLS": b[0].strip("'").replace(" ", ""),
                "NTLS": b[1].strip("'").replace(" ", ""),
                "GRPC": b[2].strip("'"),
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
                "VMESS Trial Created",
                [
                    ("Username", z["ps"]),
                    ("Domain", BOT_DOMAIN),
                    ("Mode", "Trial"),
                    ("Config", cfg_mode),
                    ("Aktif sampai dengan", f"{exp} menit"),
                ],
                selected_links + [("OpenClash", f"https://{BOT_DOMAIN}:81/vmess-{z['ps']}.txt")],
            )
            await send_account_with_qr(event, msg, qr_link, f"QR {cfg_mode} VMESS Trial")
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await trial_vmess_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

#CEK VMESS
@bot.on(events.CallbackQuery(data=b'cek-vmess'))
async def cek_vmess(event):
    async def cek_vmess_(event):
        cmd = 'bot-cek-ws'.strip()
        _, z = run_command(cmd)
        z = z or "Tidak ada sesi login VMESS aktif."
        await upsert_message(event, f"""

    📋 **VMESS • Check Login**

{z}
    """, buttons=back_button("vmess"))
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await cek_vmess_(event)
    else:
        await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'list-vmess'))
async def list_vmess(event):
    async def list_vmess_(event):
        if is_admin(sender.id):
            rows = list_xray_system_accounts("vmess")
            out = "\n".join(f"{row['username']:<20} {row['expires_at']}" for row in rows)
            if not out:
                out = "Tidak ada user VMESS."
            await upsert_message(event, f"📋 **Daftar User VMESS**\n```\n{out}\n```", buttons=back_button("vmess"))
            return

        accounts = get_user_accounts(str(sender.id), service="vmess", active_only=True, limit=120)
        if not accounts:
            await upsert_message(event, "📭 Anda belum memiliki akun VMESS yang tercatat.", buttons=back_button("vmess"))
            return

        lines = ["📋 **Akun VMESS Anda**", ""]
        for idx, account in enumerate(accounts, start=1):
            trial = " (TRIAL)" if int(account.get("is_trial", 0) or 0) == 1 else ""
            expires = str(account.get("expires_at") or "-")
            lines.append(f"{idx}. `{account.get('username', '-')}`{trial} - expired `{expires}`")
        text = "\n".join(lines)
        if len(text) > 3900:
            text = text[:3800] + "\n\n..."
        await upsert_message(event, text, buttons=back_button("vmess"))

    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await list_vmess_(event)
    else:
        await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(pattern=b"^renew-vmess(?::.+)?$"))
async def renew_vmess(event):
    async def renew_vmess_(event):
        msgs_to_del = []
        
        # Username
        user, msgs = await ask_renew_account(event, chat, sender.id, "vmess", "VMESS", "vmess")
        msgs_to_del.extend(msgs)
        if not user and not msgs_to_del:
            return
        user = sanitize_username(user)
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Username tidak valid. Gunakan huruf/angka/._-", buttons=back_button("vmess"))
            return

        if not is_admin(sender.id) and not user_owns_account(str(sender.id), "vmess", user, active_only=True):
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "⛔ Anda hanya bisa renew akun VMESS milik Anda sendiri.", buttons=back_button("vmess"))
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
        
        await upsert_message(event, "⏳ Memperpanjang akun VMESS...")
        result = renew_xray_account("vmess", user, days, quota, iplim)
        exp = str(result.get("expires_at") or "")
        
        if result.get("ok") and exp:
            refresh_account_expiry("vmess", user, exp)
            msg = build_result(
                "VMESS Account Renewed",
                [
                    ("Username", user),
                    ("Added Days", days),
                    ("Quota", f"{quota} GB"),
                    ("Limit IP", iplim),
                    ("Aktif sampai dengan", exp),
                ],
                [("OpenClash", f"https://{BOT_DOMAIN}:81/vmess-{user}.txt")],
            )
            warning = str(result.get("message") or "").strip()
            if warning:
                msg += f"\n\n⚠️ `{warning}`"
            await upsert_message(event, msg, buttons=back_button("vmess"))
        else:
            await upsert_message(event, f"❌ Gagal renew VMESS.\n```\n{result.get('message') or 'Tidak ada output'}\n```", buttons=back_button("vmess"))

    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await renew_vmess_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'delete-vmess'))
async def delete_vmess(event):
    async def delete_vmess_(event):
        msgs_to_del = []
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username yang akan dihapus:**")
        msgs_to_del.extend(msgs)
        user = sanitize_username(user)
        
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return

        if not is_admin(sender.id) and not user_owns_account(str(sender.id), "vmess", user, active_only=True):
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "⛔ Anda hanya bisa menghapus akun VMESS milik Anda sendiri.")
            return
        
        await delete_messages(chat, msgs_to_del)
        
        result = delete_xray_account("vmess", user)
        if result.get("ok"):
            mark_account_inactive("vmess", user)
            await notify_then_back(event, f"✅ **User `{user}` berhasil dihapus.**", vmess, delay=3)
        else:
            await upsert_message(event, f"❌ {result.get('message') or 'User Not Found'}", buttons=back_button("vmess"))
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await delete_vmess_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'suspend-vmess'))
async def suspend_vmess(event):
    async def suspend_vmess_(event):
        msgs_to_del = []
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username yang akan disuspend:**")
        msgs_to_del.extend(msgs)
        user = sanitize_username(user)
        
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return

        if not is_admin(sender.id) and not user_owns_account(str(sender.id), "vmess", user, active_only=True):
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "⛔ Anda hanya bisa suspend akun VMESS milik Anda sendiri.")
            return
        
        await delete_messages(chat, msgs_to_del)
        
        cmd = f'printf "%s\n" "{user}" | suspws'
        try:
            a = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
            await upsert_message(event, "**Failed to suspend user**", buttons=back_button("vmess"))
        else:
            await upsert_message(event, f"⛔ **{a.strip()}**", buttons=back_button("vmess"))
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await suspend_vmess_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'unsuspend-vmess'))
async def unsuspend_vmess(event):
    async def unsuspend_vmess_(event):
        msgs_to_del = []
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username yang akan di-unsuspend:**")
        msgs_to_del.extend(msgs)
        user = sanitize_username(user)
        
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return

        if not is_admin(sender.id) and not user_owns_account(str(sender.id), "vmess", user, active_only=True):
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "⛔ Anda hanya bisa unsuspend akun VMESS milik Anda sendiri.")
            return
        
        await delete_messages(chat, msgs_to_del)
        
        cmd = f'printf "%s\n" "{user}" | unsuspws'
        try:
            a = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
            await upsert_message(event, "**Failed to unsuspend user**", buttons=back_button("vmess"))
        else:
            await upsert_message(event, f"✅ **{a.strip()}**", buttons=back_button("vmess"))
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await unsuspend_vmess_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'vmess'))
async def vmess(event):
    async def vmess_(event):
        if is_admin(sender.id):
            inline = [
                [Button.inline("🧪 Trial", "trial-vmess"), Button.inline("➕ Create", "create-vmess")],
                [Button.inline("👀 Check Login", "cek-vmess"), Button.inline("📋 List User", "list-vmess")],
                [Button.inline("🗓️ Renew", "renew-vmess"), Button.inline("🗑️ Delete", "delete-vmess")],
                [Button.inline("⛔ Suspend", "suspend-vmess"), Button.inline("✅ Unsuspend", "unsuspend-vmess")],
                [Button.inline("⬅️ Main Menu", "menu")],
            ]
        else:
            inline = [
                [Button.inline("🧪 Trial", "trial-vmess"), Button.inline("➕ Create", "create-vmess")],
                [Button.inline("📋 Akun Saya", "list-vmess")],
                [Button.inline("🗓️ Renew", "renew-vmess"), Button.inline("🗑️ Delete", "delete-vmess")],
                [Button.inline("⛔ Suspend", "suspend-vmess"), Button.inline("✅ Unsuspend", "unsuspend-vmess")],
                [Button.inline("📨 Request Kuota", "quota-request")],
                [Button.inline("⬅️ Main Menu", "menu")],
            ]
        msg = manager_banner("VMESS Manager", "VMESS")
        await event.edit(msg,buttons=inline)
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await vmess_(event)
    else:
        await event.answer("Access Denied",alert=True)
