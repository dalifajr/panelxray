from kyt import *
from kyt.modules.ui import (
    ask_text_clean, build_result, delete_messages, manager_banner, 
    run_command, sanitize_panel_username, sanitize_username, 
    send_account_with_qr, short_progress, upsert_message,
    ask_expiry, ask_config_mode, ask_sni_profile, notify_then_back
)

BOT_DOMAIN = str(globals().get("DOMAIN", globals().get("domain", "-")))
BOT_HOST = str(globals().get("HOST", globals().get("NS", BOT_DOMAIN)))

#CREATE VMESS
@bot.on(events.CallbackQuery(data=b'create-vmess'))
async def create_vmess(event):
    async def create_vmess_(event):
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
        
        # Expiry (dengan tombol + custom)
        exp, msgs = await ask_expiry(event, chat, sender.id, is_trial=False)
        msgs_to_del.extend(msgs)
        if not exp:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return
        
        # SNI Profile (dengan tombol)
        sni_profile, msgs = await ask_sni_profile(event, chat, sender.id)
        msgs_to_del.extend(msgs)
        if not sni_profile:
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
        
        # IP Limit
        iplimit, msgs = await ask_text_clean(event, chat, sender.id, "🌐 **Limit IP (kosong=1):**", [])
        msgs_to_del.extend(msgs)
        iplimit = iplimit if iplimit else "1"
        
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
                    ("Expired", str(later)),
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
                    ("Expired", f"{exp} menit"),
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

{z}

**Shows Logged In Users Vmess**
**» 🤖@AutoFTbot**
""", buttons=[[Button.inline("‹ Main Menu ›","menu")]])
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await cek_vmess_(event)
    else:
        await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'list-vmess'))
async def list_vmess(event):
    async def list_vmess_(event):
        cmd = "grep -E '^### ' /etc/vmess/.vmess.db 2>/dev/null | awk '{printf \"%-20s %s\\n\",$2,$3}'"
        _, out = run_command(cmd)
        if not out:
            out = "Tidak ada user VMESS."
        await upsert_message(event, f"📋 **Daftar User VMESS**\n```\n{out}\n```")

    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await list_vmess_(event)
    else:
        await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'renew-vmess'))
async def renew_vmess(event):
    async def renew_vmess_(event):
        msgs_to_del = []
        
        # Username
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Masukkan Username VMESS:**")
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
        
        await upsert_message(event, "⏳ Memperpanjang akun VMESS...")
        _, out = run_command("renewws", [user, days, quota, iplim])
        _, exp = run_command(f"grep -wE '^### {user} ' /etc/xray/config.json | awk '{{print $3}}' | head -n1")
        
        if exp:
            msg = build_result(
                "VMESS Account Renewed",
                [
                    ("Username", user),
                    ("Added Days", days),
                    ("Quota", f"{quota} GB"),
                    ("Limit IP", iplim),
                    ("Expired", exp),
                ],
                [("OpenClash", f"https://{BOT_DOMAIN}:81/vmess-{user}.txt")],
            )
            await upsert_message(event, msg)
        else:
            await upsert_message(event, f"⚠️ Perpanjangan diproses, cek output:\n```\n{out or 'Tidak ada output'}\n```")

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
        
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return
        
        await delete_messages(chat, msgs_to_del)
        
        cmd = f'printf "%s\n" "{user}" | delws'
        try:
            a = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
            await upsert_message(event, "**User Not Found**")
        else:
            await notify_then_back(event, f"✅ **User `{user}` berhasil dihapus.**", vmess, delay=3)
    
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
        
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return
        
        await delete_messages(chat, msgs_to_del)
        
        cmd = f'printf "%s\n" "{user}" | suspws'
        try:
            a = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
            await upsert_message(event, "**Failed to suspend user**")
        else:
            await upsert_message(event, f"⛔ **{a.strip()}**")
    
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
        
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return
        
        await delete_messages(chat, msgs_to_del)
        
        cmd = f'printf "%s\n" "{user}" | unsuspws'
        try:
            a = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
            await upsert_message(event, "**Failed to unsuspend user**")
        else:
            await upsert_message(event, f"✅ **{a.strip()}**")
    
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
        inline = [
            [Button.inline("🧪 Trial", "trial-vmess"), Button.inline("➕ Create", "create-vmess")],
            [Button.inline("👀 Check Login", "cek-vmess"), Button.inline("📋 List User", "list-vmess")],
            [Button.inline("🗓️ Renew", "renew-vmess"), Button.inline("🗑️ Delete", "delete-vmess")],
            [Button.inline("⛔ Suspend", "suspend-vmess"), Button.inline("✅ Unsuspend", "unsuspend-vmess")],
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
