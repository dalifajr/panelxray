from kyt import *
from kyt.modules.ui import (
    ask_text_clean, build_result, delete_messages, manager_banner, 
    send_account_with_qr, short_progress, run_command,
    ask_expiry, upsert_message, notify_then_back
)

@bot.on(events.CallbackQuery(data=b'create-shadowsocks'))
async def create_shadowsocks(event):
    async def create_shadowsocks_(event):
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
        await event.respond(f"""

{z}

**Shows Logged In Users Shadowsocks**
**» 🤖@AutoFTbot**
""",buttons=[[Button.inline("‹ Main Menu ›","menu")]])
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await cek_shadowsocks_(event)
    else:
        await event.answer("Access Denied",alert=True)

@bot.on(events.CallbackQuery(data=b'delete-shadowsocks'))
async def delete_shadowsocks(event):
    async def delete_shadowsocks_(event):
        msgs_to_del = []
        user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username yang akan dihapus:**")
        msgs_to_del.extend(msgs)
        
        if not user:
            await delete_messages(chat, msgs_to_del)
            await upsert_message(event, "❌ Proses dibatalkan.")
            return
        
        await delete_messages(chat, msgs_to_del)
        
        cmd = f'printf "%s\n" "{user}" | del-ss'
        try:
            a = subprocess.check_output(cmd, shell=True).decode("utf-8")
        except:
            await upsert_message(event, "**User Not Found**")
        else:
            await notify_then_back(event, f"✅ **User `{user}` berhasil dihapus.**", shadowsocks, delay=3)
    
    chat = event.chat_id
    sender = await event.get_sender()
    a = valid(str(sender.id))
    if a == "true":
        await delete_shadowsocks_(event)
    else:
        await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'trial-shadowsocks'))
async def trial_shadowsocks(event):
    async def trial_shadowsocks_(event):
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
        inline = [
            [Button.inline("🧪 Trial", "trial-shadowsocks"), Button.inline("➕ Create", "create-shadowsocks")],
            [Button.inline("👀 Check Login", "cek-shadowsocks"), Button.inline("🗑️ Delete", "delete-shadowsocks")],
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
