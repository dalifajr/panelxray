from kyt import *
from kyt.modules.ui import manager_banner, delete_messages, upsert_message, run_command

@bot.on(events.CallbackQuery(data=b'my-accounts'))
async def my_accounts(event):
    sender = await event.get_sender()
    
    # Call Laravel API to list accounts
    res = api_call("GET", f"/bot/accounts/{sender.id}")
    raw_accounts = res.get("accounts", [])

    # Filter out accounts that have been deleted via VPS or Website
    accounts = []
    for acc in raw_accounts:
        service = acc.get("service")
        username = acc.get("username")
        if _account_exists_in_system(service, username):
            accounts.append(acc)
        else:
            # Sync back to Laravel API to mark as inactive
            api_call("POST", "/bot/account/deactivate", {
                "tg_id": str(sender.id),
                "service": service,
                "username": username
            })

    if not accounts:
        msg = (
            f"{manager_banner('Akun Saya', 'VPN Aktif Anda')}\n\n"
            "⚠️ Anda belum memiliki akun VPN aktif yang dibuat dari bot ini.\n"
            "Gunakan menu **Beli VPN** untuk membuat akun pertama Anda!"
        )
        buttons = [[Button.inline("🛒 Beli VPN", "shop-menu")], [Button.inline("🏠 Menu Utama", "start")]]
        await event.edit(msg, buttons=buttons)
        return

    # List first 8 accounts with detail buttons
    inline = []
    text_list = []
    
    for idx, acc in enumerate(accounts[:8]):
        username = acc.get("username")
        service = acc.get("service", "").upper()
        expiry = acc.get("expires_at", "-")
        
        text_list.append(f"{idx+1}. **{username}** [{service}] — Exp: `{expiry}`")
        inline.append([Button.inline(f"🗑️ Hapus {username} ({service})", f"del-acc:{acc.get('id')}:{username}:{acc.get('service')}")])

    inline.append([Button.inline("🏠 Menu Utama", "start")])

    msg = (
        f"{manager_banner('Akun Saya', 'VPN Aktif Anda')}\n\n"
        "Daftar akun VPN aktif Anda:\n" + "\n".join(text_list) + "\n\n"
        "Gunakan tombol di bawah untuk menghapus akun jika sudah tidak digunakan:"
    )

    await event.edit(msg, buttons=inline)


@bot.on(events.CallbackQuery(data=re.compile(b'del-acc:(.*?):(.*?):(.*)')))
async def delete_my_account(event):
    sender = await event.get_sender()
    
    acc_id = event.pattern_match.group(1).decode('utf-8')
    username = event.pattern_match.group(2).decode('utf-8')
    service = event.pattern_match.group(3).decode('utf-8')

    # Confirm delete
    confirm_msg = (
        "⚠️ **Konfirmasi Penghapusan**\n\n"
        f"Apakah Anda yakin ingin menghapus akun berikut?\n"
        f"▪ Username: `{username}`\n"
        f"▪ Layanan: `{service.upper()}`\n\n"
        "Tindakan ini permanen dan tidak dapat dibatalkan!"
    )

    inline = [
        [Button.inline("🗑️ Ya, Hapus Akun", f"confirm-del-acc:{username}:{service}"),
         Button.inline("❌ Batal", "my-accounts")]
    ]

    await event.edit(confirm_msg, buttons=inline)


@bot.on(events.CallbackQuery(data=re.compile(b'confirm-del-acc:(.*?):(.*)')))
async def confirm_delete_my_account(event):
    sender = await event.get_sender()
    chat = event.chat_id

    username = event.pattern_match.group(1).decode('utf-8')
    service = event.pattern_match.group(2).decode('utf-8')

    await event.edit("⏳ **Menghapus akun VPN Anda dari server...**")

    try:
        # Call termination script
        if service == "ssh":
            code, out = run_command(f'printf "%s\\n" "{username}" | delssh')
        else:
            from kyt import delete_xray_account
            delete_xray_account(service, username)

        # Mark inactive in Laravel registry via API
        deact_res = api_call("POST", "/bot/account/deactivate", {
            "tg_id": str(sender.id),
            "service": service,
            "username": username
        })

        await event.edit(f"✅ **Akun {username} ({service.upper()}) berhasil dihapus!**", 
                         buttons=[[Button.inline("⬅️ Akun Saya", "my-accounts"), Button.inline("🏠 Menu Utama", "start")]])

    except Exception as e:
        logging.exception("Delete account execution failed: %s", e)
        await event.edit(f"❌ Gagal menghapus akun: {e}")
