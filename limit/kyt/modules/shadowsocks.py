from kyt import *
from kyt.modules.ui import (
    ask_text_clean, build_result, delete_messages, manager_banner, 
    send_account_with_qr, short_progress, run_command,
    ask_expiry, upsert_message, notify_then_back, back_button,
    ensure_creation_quota, is_admin, sanitize_username
)

@bot.on(events.CallbackQuery(data=b'create-shadowsocks'))
async def create_shadowsocks(event):
    async def create_shadowsocks_(event):
        if not await ensure_creation_quota(event, str(sender.id), "xray"):
            return

        msgs_to_del = []
        
        # Username
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Masukkan Username Shadowsocks:**")
        msgs_to_del.extend(msgs)
        if not user:
            await delete_messages(chat, msgs_to_del)
            await event.respond("❌ Username kosong. Proses dibatalkan.")
            return
        
        # Quota
        pw, msgs = await ask_text_clean(event, chat, sender.id, "📦 **Masukkan Quota (GB):**", [])
        msgs_to_del.extend(msgs)
        if not pw:
            await delete_messages(chat, msgs_to_del)
            await event.respond("❌ Quota kosong. Proses dibatalkan.")
            return
        
        # Expiry (dengan tombol + custom)
        exp, msgs = await ask_expiry(event, chat, sender.id, is_trial=False)
        msgs_to_del.extend(msgs)
        if not exp:
            await delete_messages(chat, msgs_to_del)
            await event.respond("❌ Proses dibatalkan.")
            return
        
        # Hapus semua pesan input
        await delete_messages(chat, msgs_to_del)
        
        progress_msg = await event.respond("⏳ Membuat akun Shadowsocks...")
        cmd = f'printf "%s\n" "{user}" "{exp}" "{pw}" | addss'
        try:
            a = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
            await progress_msg.delete()
            await event.respond("❌ **Username sudah terdaftar.**")
        else:
            await progress_msg.delete()
            today = DT.date.today()
            later = today + DT.timedelta(days=int(exp))
            register_account_creation(str(sender.id), "shadowsocks", user, str(later), is_trial=False)
            x = [x.group() for x in re.finditer("ss://(.*)",a)]
            if len(x) < 2:
                await event.respond("❌ **Gagal membaca link Shadowsocks dari panel.**")
                return
            uuid = re.search("ss://(.*?)@",x[0]).group(1)
            msg = build_result(
                "Shadowsocks Account Created",
                [
                    ("Username", user),
                    ("Host", DOMAIN),
                    ("XRAY DNS", HOST),
                    ("Quota", f"{pw} GB"),
                    ("Password", uuid),
                    ("Cipher", "aes-128-gcm"),
                    ("Aktif sampai dengan", str(later)),
                ],
                [
                    ("TLS", x[0]),
                    ("gRPC", x[1].replace(" ", "")),
                    ("JSON", f"https://{DOMAIN}:81/ss-{user}.txt"),
                ],
            )
            await send_account_with_qr(event, msg, x[0], "QR TLS SHADOWSOCKS")
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await create_shadowsocks_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'cek-shadowsocks'))
async def cek_shadowsocks(event):
    async def cek_shadowsocks_(event):
        cmd = 'bot-cek-ss'.strip()
        _, z = run_command(cmd)
        z = z or "Tidak ada sesi login Shadowsocks aktif."
        await upsert_message(event, f"""

    📋 **SHADOWSOCKS • Check Login**

{z}

    """,buttons=back_button("shadowsocks"))
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await cek_shadowsocks_(event)
    else:
        await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'list-shadowsocks'))
async def list_shadowsocks(event):
    async def list_shadowsocks_(event):
        if is_admin(sender.id):
            cmd = "grep -E '^### ' /etc/shadowsocks/.shadowsocks.db 2>/dev/null | awk '{printf \"%-20s %s\\n\",$2,$3}'"
            _, out = run_command(cmd)
            if not out:
                out = "Tidak ada user SHADOWSOCKS."
            await upsert_message(event, f"📋 **Daftar User SHADOWSOCKS**\n```\n{out}\n```", buttons=back_button("shadowsocks"))
            return

        accounts = get_user_accounts(str(sender.id), service="shadowsocks", active_only=True, limit=120)
        if not accounts:
            await upsert_message(event, "📭 Anda belum memiliki akun SHADOWSOCKS yang tercatat.", buttons=back_button("shadowsocks"))
            return

        lines = ["📋 **Akun SHADOWSOCKS Anda**", ""]
        for idx, account in enumerate(accounts, start=1):
            trial = " (TRIAL)" if int(account.get("is_trial", 0) or 0) == 1 else ""
            expires = str(account.get("expires_at") or "-")
            lines.append(f"{idx}. `{account.get('username', '-')}`{trial} - expired `{expires}`")
        text = "\n".join(lines)
        if len(text) > 3900:
            text = text[:3800] + "\n\n..."
        await upsert_message(event, text, buttons=back_button("shadowsocks"))

    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await list_shadowsocks_(event)
    else:
        await event.answer("Access Denied",alert=True)

@bot.on(events.CallbackQuery(data=b'delete-shadowsocks'))
async def delete_shadowsocks(event):
    async def delete_shadowsocks_(event):
        msgs_to_del = []
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username yang akan dihapus:**")
        msgs_to_del.extend(msgs)
        user = sanitize_username(user)
        
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.", buttons=back_button("shadowsocks"))
            return

        if not is_admin(sender.id) and not user_owns_account(str(sender.id), "shadowsocks", user, active_only=True):
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "⛔ Anda hanya bisa menghapus akun SHADOWSOCKS milik Anda sendiri.", buttons=back_button("shadowsocks"))
            return
        
        await delete_messages(chat, msgs_to_del)
        
        cmd = f'printf "%s\n" "{user}" | del-ss'
        try:
            a = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
            await upsert_message(event, "**User Not Found**", buttons=back_button("shadowsocks"))
        else:
            mark_account_inactive("shadowsocks", user)
            await notify_then_back(event, f"✅ **User `{user}` berhasil dihapus.**", shadowsocks, delay=3)
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await delete_shadowsocks_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)


@bot.on(events.CallbackQuery(data=b'renew-shadowsocks'))
async def renew_shadowsocks(event):
    async def renew_shadowsocks_(event):
        msgs_to_del = []

        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Masukkan Username SHADOWSOCKS:**")
        msgs_to_del.extend(msgs)
        user = sanitize_username(user)
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Username tidak valid. Gunakan huruf/angka/._-", buttons=back_button("shadowsocks"))
            return

        if not is_admin(sender.id) and not user_owns_account(str(sender.id), "shadowsocks", user, active_only=True):
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "⛔ Anda hanya bisa renew akun SHADOWSOCKS milik Anda sendiri.", buttons=back_button("shadowsocks"))
            return

        days, msgs = await ask_expiry(event, chat, sender.id, is_trial=False)
        msgs_to_del.extend(msgs)
        if not days:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.", buttons=back_button("shadowsocks"))
            return

        await delete_messages(chat, msgs_to_del)
        await upsert_message(event, "⏳ Memperpanjang akun SHADOWSOCKS...")
        _, out = run_command("renewss", [user, days])
        _, exp = run_command(f"grep -wE '^#!# {user} ' /etc/xray/config.json | awk '{{print $3}}' | head -n1")

        if exp:
            refresh_account_expiry("shadowsocks", user, exp)
            msg = build_result(
                "Shadowsocks Account Renewed",
                [
                    ("Username", user),
                    ("Added Days", days),
                    ("Aktif sampai dengan", exp),
                ],
                [("JSON", f"https://{DOMAIN}:81/ss-{user}.txt")],
            )
            await upsert_message(event, msg, buttons=back_button("shadowsocks"))
        else:
            await upsert_message(
                event,
                f"⚠️ Perpanjangan diproses, cek output:\n```\n{out or 'Tidak ada output'}\n```",
                buttons=back_button("shadowsocks"),
            )

    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await renew_shadowsocks_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'trial-shadowsocks'))
async def trial_shadowsocks(event):
    async def trial_shadowsocks_(event):
        if not await ensure_creation_quota(event, str(sender.id), "xray"):
            return

        msgs_to_del = []
        
        # Trial duration (dengan tombol)
        exp, msgs = await ask_expiry(event, chat, sender.id, is_trial=True)
        msgs_to_del.extend(msgs)
        if not exp:
            await delete_messages(chat, msgs_to_del)
            await event.respond("❌ Proses dibatalkan.")
            return
        
        # Hapus semua pesan input
        await delete_messages(chat, msgs_to_del)
        
        progress_msg = await event.respond("⏳ Membuat trial Shadowsocks...")
        cmd = f'printf "%s\n" "{exp}" | trialss'
        try:
            a = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
            await progress_msg.delete()
            await event.respond("❌ **Gagal membuat trial SHADOWSOCKS.**")
        else:
            await progress_msg.delete()
            x = [x.group() for x in re.finditer("ss://(.*)",a)]
            if len(x) < 2:
                await event.respond("❌ **Gagal membaca link trial Shadowsocks dari panel.**")
                return
            remarks = re.search("#(.*)",x[0]).group(1)
            uuid = re.search("ss://(.*?)@",x[0]).group(1)
            register_account_creation(str(sender.id), "shadowsocks", remarks, f"{exp} menit", is_trial=True)
            msg = build_result(
                "Shadowsocks Trial Created",
                [
                    ("Username", remarks),
                    ("Host", DOMAIN),
                    ("Password", uuid),
                    ("Mode", "Trial"),
                    ("Aktif sampai dengan", f"{exp} menit"),
                ],
                [
                    ("TLS", x[0]),
                    ("gRPC", x[1].replace(" ", "")),
                    ("JSON", f"https://{DOMAIN}:81/ss-{remarks}.txt"),
                ],
            )
            await send_account_with_qr(event, msg, x[0], "QR TLS SHADOWSOCKS Trial")
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await trial_shadowsocks_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'shadowsocks'))
async def shadowsocks(event):
    async def shadowsocks_(event):
        if is_admin(sender.id):
            inline = [
                [Button.inline("🧪 Trial", "trial-shadowsocks"), Button.inline("➕ Create", "create-shadowsocks")],
                [Button.inline("👀 Check Login", "cek-shadowsocks"), Button.inline("📋 List User", "list-shadowsocks")],
                [Button.inline("🗓️ Renew", "renew-shadowsocks"), Button.inline("🗑️ Delete", "delete-shadowsocks")],
                [Button.inline("⬅️ Main Menu", "menu")],
            ]
        else:
            inline = [
                [Button.inline("🧪 Trial", "trial-shadowsocks"), Button.inline("➕ Create", "create-shadowsocks")],
                [Button.inline("📋 Akun Saya", "list-shadowsocks")],
                [Button.inline("🗓️ Renew", "renew-shadowsocks"), Button.inline("🗑️ Delete", "delete-shadowsocks")],
                [Button.inline("📨 Request Kuota", "quota-request")],
                [Button.inline("⬅️ Main Menu", "menu")],
            ]
        msg = manager_banner("Shadowsocks Manager", "SHADOWSOCKS")
        await event.edit(msg,buttons=inline)
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await shadowsocks_(event)
    else:
        await event.answer("Access Denied",alert=True)
