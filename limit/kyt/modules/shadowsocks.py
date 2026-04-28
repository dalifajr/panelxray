from kyt import *
from kyt.modules.ui import (
    ask_text_clean, build_result, delete_messages, manager_banner, 
    send_account_with_qr, short_progress, run_command,
    ask_expiry, upsert_message, notify_then_back, back_button,
    ensure_creation_quota, is_admin, sanitize_username, ask_renew_account
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

        # IP Limit
        iplimit, msgs = await ask_text_clean(event, chat, sender.id, "🌐 **Limit IP (kosong=1):**", [])
        msgs_to_del.extend(msgs)
        iplimit = iplimit if iplimit else "1"
        
        # Expiry (dengan tombol + custom)
        exp, msgs = await ask_expiry(event, chat, sender.id, is_trial=False)
        msgs_to_del.extend(msgs)
        if not exp:
            await delete_messages(chat, msgs_to_del)
            await event.respond("❌ Proses dibatalkan.")
            return
        
        # Hapus semua pesan input
        await delete_messages(chat, msgs_to_del)
        
        await upsert_message(event, "⏳ Membuat akun Shadowsocks...")
        code, a = run_command("addss", [user, exp, pw, iplimit])
        
        if code != 0:
            if code == 124:
                await upsert_message(event, "❌ Proses create SHADOWSOCKS timeout. Cek script `addss` atau format input username.")
            else:
                await upsert_message(event, f"❌ Gagal create SHADOWSOCKS.\n```\n{a or 'Tidak ada output'}\n```")
        else:
            today = DT.date.today()
            later = today + DT.timedelta(days=int(exp))
            register_account_creation(str(sender.id), "shadowsocks", user, str(later), is_trial=False)
            x = [x.group() for x in re.finditer("ss://(.*)",a)]
            if len(x) < 2:
                await upsert_message(event, "❌ **Gagal membaca link Shadowsocks dari panel.**")
                return
            uuid = re.search("ss://(.*?)@",x[0]).group(1)
            msg = build_result(
                "Shadowsocks Account Created",
                [
                    ("Username", user),
                    ("Host", DOMAIN),
                    ("XRAY DNS", HOST),
                    ("Quota", f"{pw} GB"),
                    ("Limit IP", iplimit),
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
            rows = list_xray_system_accounts("shadowsocks")
            out = "\n".join(f"{row['username']:<20} {row['expires_at']}" for row in rows)
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
        
        result = delete_xray_account("shadowsocks", user)
        if result.get("ok"):
            mark_account_inactive("shadowsocks", user)
            await notify_then_back(event, f"✅ **User `{user}` berhasil dihapus.**", shadowsocks, delay=3)
        else:
            await upsert_message(event, f"❌ {result.get('message') or 'User Not Found'}", buttons=back_button("shadowsocks"))
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await delete_shadowsocks_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)


@bot.on(events.CallbackQuery(pattern=b"^renew-shadowsocks(?::.+)?$"))
async def renew_shadowsocks(event):
    async def renew_shadowsocks_(event):
        msgs_to_del = []

        user, msgs = await ask_renew_account(event, chat, sender.id, "shadowsocks", "SHADOWSOCKS", "shadowsocks")
        msgs_to_del.extend(msgs)
        if not user and not msgs_to_del:
            return
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

        iplim, msgs = await ask_text_clean(event, chat, sender.id, "🌐 **Limit IP baru (kosong=1):**", [])
        msgs_to_del.extend(msgs)
        iplim = iplim if iplim else "1"

        await delete_messages(chat, msgs_to_del)
        await upsert_message(event, "⏳ Memperpanjang akun SHADOWSOCKS...")
        result = renew_xray_account("shadowsocks", user, days, 0, iplim)
        exp = str(result.get("expires_at") or "")

        if result.get("ok") and exp:
            refresh_account_expiry("shadowsocks", user, exp)
            msg = build_result(
                "Shadowsocks Account Renewed",
                [
                    ("Username", user),
                    ("Added Days", days),
                    ("Limit IP", iplim),
                    ("Aktif sampai dengan", exp),
                ],
                [("JSON", f"https://{DOMAIN}:81/ss-{user}.txt")],
            )
            warning = str(result.get("message") or "").strip()
            if warning:
                msg += f"\n\n⚠️ `{warning}`"
            await upsert_message(event, msg, buttons=back_button("shadowsocks"))
        else:
            await upsert_message(
                event,
                f"❌ Gagal renew SHADOWSOCKS.\n```\n{result.get('message') or 'Tidak ada output'}\n```",
                buttons=back_button("shadowsocks"),
            )

    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await renew_shadowsocks_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)


@bot.on(events.CallbackQuery(data=b'suspend-shadowsocks'))
async def suspend_shadowsocks(event):
    async def suspend_shadowsocks_(event):
        msgs_to_del = []
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username yang akan disuspend:**")
        msgs_to_del.extend(msgs)
        user = sanitize_username(user)

        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.", buttons=back_button("shadowsocks"))
            return

        if not is_admin(sender.id) and not user_owns_account(str(sender.id), "shadowsocks", user, active_only=True):
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "⛔ Anda hanya bisa suspend akun SHADOWSOCKS milik Anda sendiri.", buttons=back_button("shadowsocks"))
            return

        await delete_messages(chat, msgs_to_del)
        code, out = run_command("suspss", [user])
        if code != 0:
            await upsert_message(event, f"❌ Gagal suspend akun SHADOWSOCKS.\n```\n{out or 'Tidak ada output'}\n```", buttons=back_button("shadowsocks"))
            return

        await upsert_message(event, f"⛔ **{(out or 'Akun berhasil disuspend').strip()}**", buttons=back_button("shadowsocks"))

    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await suspend_shadowsocks_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)


@bot.on(events.CallbackQuery(data=b'unsuspend-shadowsocks'))
async def unsuspend_shadowsocks(event):
    async def unsuspend_shadowsocks_(event):
        msgs_to_del = []
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username yang akan di-unsuspend:**")
        msgs_to_del.extend(msgs)
        user = sanitize_username(user)

        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.", buttons=back_button("shadowsocks"))
            return

        if not is_admin(sender.id) and not user_owns_account(str(sender.id), "shadowsocks", user, active_only=True):
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "⛔ Anda hanya bisa unsuspend akun SHADOWSOCKS milik Anda sendiri.", buttons=back_button("shadowsocks"))
            return

        await delete_messages(chat, msgs_to_del)
        code, out = run_command("unsuspss", [user])
        if code != 0:
            await upsert_message(event, f"❌ Gagal unsuspend akun SHADOWSOCKS.\n```\n{out or 'Tidak ada output'}\n```", buttons=back_button("shadowsocks"))
            return

        await upsert_message(event, f"✅ **{(out or 'Akun berhasil di-unsuspend').strip()}**", buttons=back_button("shadowsocks"))

    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await unsuspend_shadowsocks_(event)
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
                [Button.inline("⛔ Suspend", "suspend-shadowsocks"), Button.inline("✅ Unsuspend", "unsuspend-shadowsocks")],
                [Button.inline("⬅️ Main Menu", "menu")],
            ]
        else:
            inline = [
                [Button.inline("🧪 Trial", "trial-shadowsocks"), Button.inline("➕ Create", "create-shadowsocks")],
                [Button.inline("📋 Akun Saya", "list-shadowsocks")],
                [Button.inline("🗓️ Renew", "renew-shadowsocks"), Button.inline("🗑️ Delete", "delete-shadowsocks")],
                [Button.inline("⛔ Suspend", "suspend-shadowsocks"), Button.inline("✅ Unsuspend", "unsuspend-shadowsocks")],
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
