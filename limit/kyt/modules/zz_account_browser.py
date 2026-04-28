from kyt import *
from kyt.modules.ui import (
    account_confirm_callback,
    account_page_callback,
    decode_account_action,
    decode_account_service,
    delete_messages,
    get_account_browser_state,
    show_account_browser,
    upsert_message,
    ask_text_clean,
)


def _decode(event) -> str:
    try:
        return (event.data or b"").decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def _parse_page_callback(data: str):
    parts = data.split(":", 4)
    if len(parts) < 4:
        return "", "", 0, ""
    action = decode_account_action(parts[1])
    service = decode_account_service(parts[2])
    try:
        page = max(0, int(parts[3]))
    except Exception:
        page = 0
    query = parts[4] if len(parts) > 4 else ""
    return action, service, page, query


def _parse_item_callback(data: str):
    parts = data.split(":", 4)
    if len(parts) != 5:
        return "", "", 0, ""
    action = decode_account_action(parts[1])
    service = decode_account_service(parts[2])
    try:
        page = max(0, int(parts[3]))
    except Exception:
        page = 0
    username = parts[4].strip()
    return action, service, page, username


def _parse_confirm_callback(data: str):
    parts = data.split(":", 3)
    if len(parts) != 4:
        return "", "", ""
    return decode_account_action(parts[1]), decode_account_service(parts[2]), parts[3].strip()


def _action_label(action: str) -> str:
    return {
        "delete": "hapus",
        "suspend": "suspend",
        "unsuspend": "unsuspend",
    }.get(action, action)


def _can_operate(sender_id: str, service: str, username: str, action: str) -> bool:
    if is_admin_user(sender_id):
        return True
    active_only = action not in {"delete", "unsuspend"}
    return user_owns_account(sender_id, service, username, active_only=active_only)


@bot.on(events.CallbackQuery(pattern=b"^a:"))
async def account_browser_page(event):
    sender = await event.get_sender()
    if valid(str(sender.id)) != "true":
        await event.answer("Akses Ditolak", alert=True)
        return

    action, service, page, query = _parse_page_callback(_decode(event))
    if not action or not service:
        await event.answer("Callback tidak valid", alert=True)
        return

    await show_account_browser(event, service, action, page=page, query=query)


@bot.on(events.CallbackQuery(pattern=b"^as:"))
async def account_browser_search(event):
    sender = await event.get_sender()
    if valid(str(sender.id)) != "true":
        await event.answer("Akses Ditolak", alert=True)
        return

    parts = _decode(event).split(":", 2)
    if len(parts) != 3:
        await event.answer("Callback tidak valid", alert=True)
        return

    action = decode_account_action(parts[1])
    service = decode_account_service(parts[2])
    if not action or not service:
        await event.answer("Callback tidak valid", alert=True)
        return

    query, msgs = await ask_text_clean(
        event,
        event.chat_id,
        sender.id,
        "🔎 **Ketik query username akun:**",
        [],
    )
    await delete_messages(event.chat_id, msgs)
    query = re.sub(r"[^A-Za-z0-9_.-]", "", str(query or "").strip())[:24]
    await show_account_browser(event, service, action, page=0, query=query)


@bot.on(events.CallbackQuery(pattern=b"^b:"))
async def account_browser_item(event):
    sender = await event.get_sender()
    sender_id = str(sender.id)
    if valid(sender_id) != "true":
        await event.answer("Akses Ditolak", alert=True)
        return

    action, service, page, username = _parse_item_callback(_decode(event))
    username = re.sub(r"[^A-Za-z0-9_.-]", "", username)[:32]
    if not action or not service or not username:
        await event.answer("Callback tidak valid", alert=True)
        return

    if not _can_operate(sender_id, service, username, action):
        await event.answer("Akun bukan milik Anda", alert=True)
        return

    state = get_account_browser_state(event.chat_id, sender.id, action, service)
    query = str(state.get("query") or "")
    back = [[Button.inline("⬅️ Kembali", account_page_callback(action, service, page, query))]]

    if action == "list":
        await upsert_message(event, account_detail_text(service, username), buttons=back)
        return

    label = SERVICE_LABELS.get(service, service.upper())
    text = (
        f"⚠️ **Konfirmasi {_action_label(action).upper()} {label}**\n\n"
        f"• Username: `{username}`\n"
        f"• Service: `{label}`\n\n"
        "Klik konfirmasi untuk mengeksekusi tindakan."
    )
    buttons = [
        [Button.inline("Konfirmasi", account_confirm_callback(action, service, username))],
        [Button.inline("⬅️ Kembali", account_page_callback(action, service, page, query))],
    ]
    await upsert_message(event, text, buttons=buttons)


@bot.on(events.CallbackQuery(pattern=b"^c:"))
async def account_browser_confirm(event):
    sender = await event.get_sender()
    sender_id = str(sender.id)
    if valid(sender_id) != "true":
        await event.answer("Akses Ditolak", alert=True)
        return

    action, service, username = _parse_confirm_callback(_decode(event))
    username = re.sub(r"[^A-Za-z0-9_.-]", "", username)[:32]
    if action not in {"delete", "suspend", "unsuspend"} or not service or not username:
        await event.answer("Callback tidak valid", alert=True)
        return

    if not _can_operate(sender_id, service, username, action):
        await event.answer("Akun bukan milik Anda", alert=True)
        return

    await upsert_message(event, f"⏳ Mengeksekusi `{_action_label(action)}` untuk `{username}`...")
    result = execute_account_action(service, action, username)
    if result.get("ok"):
        if action == "delete":
            mark_account_inactive(service, username)
        await upsert_message(
            event,
            f"✅ Aksi `{_action_label(action)}` berhasil untuk `{username}`.\n\n```\n{result.get('message') or 'Berhasil.'}\n```",
            buttons=[[Button.inline("⬅️ Kembali", account_page_callback(action, service, 0, ""))]],
        )
        return

    await upsert_message(
        event,
        f"❌ Aksi `{_action_label(action)}` gagal untuk `{username}`.\n\n```\n{result.get('message') or 'Tidak ada output'}\n```",
        buttons=[[Button.inline("⬅️ Kembali", account_page_callback(action, service, 0, ""))]],
    )
