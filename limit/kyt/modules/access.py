from kyt import *
from kyt.modules.ui import (
    ask_text,
    ask_text_clean,
    delete_messages,
    upsert_message,
    require_access,
    require_admin,
    access_request_buttons,
    quota_request_buttons,
    menu_credit,
)

_ADMIN_ONLY_EXACT = {
    "setting",
    "info",
    "backer",
    "backup",
    "restore",
    "reboot",
    "resx",
    "speedtest",
    "login-ssh",
    "regis",
    "ssh-auth-status",
    "root-passwd",
}

_ADMIN_ONLY_PREFIXES = (
    "admin-",
    "acc-appr:",
    "acc-rej:",
    "q-appr:",
    "q-rej:",
    "cek-",
)


def _decode_callback_data(event) -> str:
    try:
        return (event.data or b"").decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def _optional_reason(text: str) -> str:
    value = str(text or "").strip()
    if value in {"-", ".", "skip", "kosong", "none", "tidak"}:
        return ""
    return value


def _status_label(status: str) -> str:
    s = str(status or "").lower()
    if s == "approved":
        return "APPROVED"
    if s == "pending":
        return "PENDING"
    if s == "rejected":
        return "REJECTED"
    if s == "suspended":
        return "SUSPENDED"
    if s == "kicked":
        return "KICKED"
    return s.upper() if s else "UNKNOWN"


def _display_user_name(user_row: dict) -> str:
    username = str(user_row.get("username") or "").strip()
    full_name = str(user_row.get("full_name") or "").strip()
    if username:
        return f"@{username}"
    if full_name:
        return full_name
    return str(user_row.get("tg_id") or "-")


def _is_admin_only_callback(data: str) -> bool:
    if data in _ADMIN_ONLY_EXACT:
        return True
    for prefix in _ADMIN_ONLY_PREFIXES:
        if data.startswith(prefix):
            return True
    return False


async def _notify_user(target_id: str, text: str, buttons=None):
    target = str(target_id or "").strip()
    if not target:
        return
    try:
        if buttons is None:
            await bot.send_message(int(target), text)
        else:
            await bot.send_message(int(target), text, buttons=buttons)
    except Exception:
        logging.warning("Tidak bisa kirim notifikasi ke user %s", target)


async def _notify_admins(text: str, buttons=None):
    for admin_id in get_all_admin_ids():
        await _notify_user(admin_id, text, buttons=buttons)


async def _show_admin_user_detail(event, target_id: str, notice: str = ""):
    row = get_user_record(target_id)
    if not row:
        await upsert_message(event, "❌ Data user tidak ditemukan.", buttons=[[Button.inline("⬅️ List User", b"admin-users")]])
        return

    stats = get_user_stats(target_id)
    limits = get_user_limits(target_id)
    status = _status_label(row.get("status", ""))
    role = str(row.get("role") or "user").upper()
    ssh_limit = "unlimited" if int(limits.get("ssh_limit", 0)) <= 0 else str(limits.get("ssh_limit", 0))
    xray_limit = "unlimited" if int(limits.get("xray_limit", 0)) <= 0 else str(limits.get("xray_limit", 0))

    lines = [
        "👤 **Detail User Telegram**",
        f"• Nama: `{_display_user_name(row)}`",
        f"• ID: `{row.get('tg_id', '-')}`",
        f"• Role: `{role}`",
        f"• Status: `{status}`",
        f"• Total create SSH: `{stats.get('ssh_total', 0)}`",
        f"• Total create XRAY: `{stats.get('xray_total', 0)}`",
        f"• Limit create SSH: `{ssh_limit}`",
        f"• Limit create XRAY: `{xray_limit}`",
    ]
    note = str(row.get("note") or "").strip()
    if note:
        lines.append(f"• Catatan status: `{note}`")
    if notice:
        lines.append("")
        lines.append(notice)
    lines.append("")
    lines.append(menu_credit())

    buttons = [
        [
            Button.inline("📋 List Akun XRAY", f"admin-user-xray:{target_id}".encode()),
            Button.inline("📋 List Akun SSH", f"admin-user-ssh:{target_id}".encode()),
        ],
        [Button.inline("⚖️ Set Limit Kuota", f"admin-user-limit:{target_id}".encode())],
        [
            Button.inline("👢 Kick", f"admin-user-kick:{target_id}".encode()),
            Button.inline("⛔ Suspend", f"admin-user-suspend:{target_id}".encode()),
        ],
        [Button.inline("✅ Unsuspend", f"admin-user-unsuspend:{target_id}".encode())],
        [Button.inline("⬅️ List User", b"admin-users")],
    ]
    await upsert_message(event, "\n".join(lines), buttons=buttons)


@bot.on(events.CallbackQuery(pattern=b".+"))
async def callback_permission_guard(event):
    sender = await event.get_sender()
    sender_id = str(sender.id)
    touch_user(
        sender_id,
        getattr(sender, "username", "") or "",
        f"{getattr(sender, 'first_name', '') or ''} {getattr(sender, 'last_name', '') or ''}".strip(),
    )

    callback_data = _decode_callback_data(event)

    if not is_user_approved(sender_id):
        if callback_data == "request-access":
            return
        try:
            await event.answer("Akses belum aktif", alert=True)
        except Exception:
            pass
        await upsert_message(
            event,
            "🔒 Anda belum punya akses bot. Kirim request akses ke admin dulu.",
            buttons=access_request_buttons(),
        )
        raise events.StopPropagation

    if is_admin_user(sender_id):
        return

    if _is_admin_only_callback(callback_data):
        try:
            await event.answer("Menu khusus admin", alert=True)
        except Exception:
            pass
        raise events.StopPropagation


@bot.on(events.CallbackQuery(data=b"request-access"))
async def request_access_handler(event):
    sender = await event.get_sender()
    sender_id = str(sender.id)

    if is_user_approved(sender_id):
        await upsert_message(event, "✅ Akses Anda sudah aktif.", buttons=[[Button.inline("⬅️ Menu", b"menu")]])
        return

    chat = event.chat_id
    reason, msgs = await ask_text_clean(
        event,
        chat,
        sender.id,
        "📝 **Alasan request akses (opsional, ketik `-` jika kosong):**",
        [],
    )
    await delete_messages(chat, msgs)
    reason = _optional_reason(reason)

    full_name = f"{getattr(sender, 'first_name', '') or ''} {getattr(sender, 'last_name', '') or ''}".strip()
    result = create_access_request(
        sender_id,
        getattr(sender, "username", "") or "",
        full_name,
        reason,
    )

    status = result.get("status")
    if status == "already-approved":
        await upsert_message(event, "✅ Akses Anda sudah disetujui.", buttons=[[Button.inline("⬅️ Menu", b"menu")]])
        return

    if status == "pending":
        req = result.get("request") or {}
        rid = req.get("id", "-")
        await upsert_message(event, f"⏳ Anda sudah punya request pending (ID: `{rid}`).")
        return

    if not result.get("ok"):
        await upsert_message(event, "❌ Gagal membuat request akses. Coba lagi.")
        return

    req = result.get("request") or {}
    request_id = req.get("id")
    admin_buttons = [
        [
            Button.inline("✅ Approve", f"acc-appr:{request_id}".encode()),
            Button.inline("❌ Reject", f"acc-rej:{request_id}".encode()),
        ]
    ]
    notif = (
        "📥 **Request Akses Baru**\n"
        f"• Request ID: `{request_id}`\n"
        f"• User: `{_display_user_name(req)}`\n"
        f"• Telegram ID: `{req.get('tg_id', '-')}`\n"
    )
    if reason:
        notif += f"• Alasan: `{reason}`\n"

    await _notify_admins(notif, buttons=admin_buttons)
    await upsert_message(
        event,
        "✅ Request akses dikirim ke admin. Tunggu approve/reject.",
        buttons=[[Button.inline("⬅️ Kembali", b"start")]],
    )


@bot.on(events.CallbackQuery(pattern=b"^acc-appr:(\\d+)$"))
async def access_approve_handler(event):
    if not await require_admin(event):
        return

    sender = await event.get_sender()
    request_id = int(event.pattern_match.group(1).decode("ascii"))
    note = await ask_text(
        event,
        event.chat_id,
        sender.id,
        "📝 Catatan approve (opsional, ketik `-` jika kosong):",
    )
    note = _optional_reason(note)

    result = process_access_request(request_id, str(sender.id), True, note)
    if result is None:
        await upsert_message(event, "⚠️ Request sudah diproses atau tidak ditemukan.")
        return

    target_id = str(result.get("tg_id") or "")
    approve_msg = "✅ Request akses Anda sudah di-approve admin."
    if note:
        approve_msg += f"\n\nCatatan admin: `{note}`"
    approve_msg += "\n\nSilakan buka /menu."
    await _notify_user(target_id, approve_msg)

    await upsert_message(
        event,
        f"✅ Request akses #{request_id} di-approve untuk user `{target_id}`.",
        buttons=[[Button.inline("⬅️ Pending Akses", b"admin-pending-access")], [Button.inline("⬅️ Kelola User", b"admin-users")]],
    )


@bot.on(events.CallbackQuery(pattern=b"^acc-rej:(\\d+)$"))
async def access_reject_handler(event):
    if not await require_admin(event):
        return

    sender = await event.get_sender()
    request_id = int(event.pattern_match.group(1).decode("ascii"))
    note = await ask_text(
        event,
        event.chat_id,
        sender.id,
        "📝 Alasan reject (opsional, ketik `-` jika kosong):",
    )
    note = _optional_reason(note)

    result = process_access_request(request_id, str(sender.id), False, note)
    if result is None:
        await upsert_message(event, "⚠️ Request sudah diproses atau tidak ditemukan.")
        return

    target_id = str(result.get("tg_id") or "")
    reject_msg = "❌ Request akses Anda ditolak admin."
    if note:
        reject_msg += f"\n\nAlasan: `{note}`"
    reject_msg += "\n\nAnda dapat request ulang dari menu start."
    await _notify_user(target_id, reject_msg, buttons=access_request_buttons())

    await upsert_message(
        event,
        f"✅ Request akses #{request_id} ditolak untuk user `{target_id}`.",
        buttons=[[Button.inline("⬅️ Pending Akses", b"admin-pending-access")], [Button.inline("⬅️ Kelola User", b"admin-users")]],
    )


@bot.on(events.CallbackQuery(data=b"admin-pending-access"))
async def pending_access_list(event):
    if not await require_admin(event):
        return

    pending = list_pending_access_requests(20)
    if not pending:
        await upsert_message(
            event,
            "📭 Tidak ada request akses pending.",
            buttons=[[Button.inline("⬅️ Kelola User", b"admin-users")]],
        )
        return

    lines = ["📥 **Pending Request Akses**", ""]
    buttons = []
    for req in pending:
        rid = req.get("id")
        label = _display_user_name(req)
        lines.append(f"• #{rid} `{label}` (`{req.get('tg_id', '-')}`)")
        reason = str(req.get("reason") or "").strip()
        if reason:
            lines.append(f"  alasan: `{reason}`")
        buttons.append([
            Button.inline(f"✅ #{rid}", f"acc-appr:{rid}".encode()),
            Button.inline(f"❌ #{rid}", f"acc-rej:{rid}".encode()),
        ])
    lines.append("")
    lines.append(menu_credit())

    buttons.append([Button.inline("⬅️ Kelola User", b"admin-users")])
    await upsert_message(event, "\n".join(lines), buttons=buttons)


@bot.on(events.CallbackQuery(data=b"quota-my"))
async def quota_my_handler(event):
    if not await require_access(event):
        return

    sender = await event.get_sender()
    sender_id = str(sender.id)
    stats = get_user_stats(sender_id)
    limits = get_user_limits(sender_id)

    ssh_limit = "unlimited" if int(limits.get("ssh_limit", 0)) <= 0 else str(limits.get("ssh_limit", 0))
    xray_limit = "unlimited" if int(limits.get("xray_limit", 0)) <= 0 else str(limits.get("xray_limit", 0))

    msg = (
        "📈 **Kuota Pembuatan Akun Anda**\n"
        f"• SSH: `{stats.get('ssh_total', 0)}` / `{ssh_limit}`\n"
        f"• XRAY: `{stats.get('xray_total', 0)}` / `{xray_limit}`\n\n"
        "Jika limit tercapai, kirim request tambahan kuota ke admin."
    )
    await upsert_message(event, msg, buttons=quota_request_buttons())


@bot.on(events.CallbackQuery(data=b"quota-request"))
async def quota_request_handler(event):
    if not await require_access(event):
        return

    sender = await event.get_sender()
    sender_id = str(sender.id)
    if is_admin_user(sender_id):
        await upsert_message(event, "ℹ️ Admin tidak membutuhkan request kuota.")
        return

    chat = event.chat_id
    reason, msgs = await ask_text_clean(
        event,
        chat,
        sender.id,
        "📝 **Alasan request tambahan kuota (opsional, ketik `-` jika kosong):**",
        [],
    )
    await delete_messages(chat, msgs)
    reason = _optional_reason(reason)

    result = create_quota_request(sender_id, reason)
    status = result.get("status")
    if status == "pending":
        req = result.get("request") or {}
        await upsert_message(event, f"⏳ Anda sudah punya request kuota pending (ID: `{req.get('id', '-')}`).")
        return

    if not result.get("ok"):
        await upsert_message(event, "❌ Gagal membuat request kuota.")
        return

    req = result.get("request") or {}
    request_id = req.get("id")
    stats = get_user_stats(sender_id)
    limits = get_user_limits(sender_id)
    ssh_limit = "unlimited" if int(limits.get("ssh_limit", 0)) <= 0 else str(limits.get("ssh_limit", 0))
    xray_limit = "unlimited" if int(limits.get("xray_limit", 0)) <= 0 else str(limits.get("xray_limit", 0))

    notif = (
        "📨 **Request Tambahan Kuota**\n"
        f"• Request ID: `{request_id}`\n"
        f"• User ID: `{sender_id}`\n"
        f"• Username: `{getattr(sender, 'username', '') or '-'} `\n"
        f"• Usage SSH: `{stats.get('ssh_total', 0)}` / `{ssh_limit}`\n"
        f"• Usage XRAY: `{stats.get('xray_total', 0)}` / `{xray_limit}`\n"
    )
    if reason:
        notif += f"• Alasan: `{reason}`\n"

    buttons = [
        [
            Button.inline("✅ Approve", f"q-appr:{request_id}".encode()),
            Button.inline("❌ Reject", f"q-rej:{request_id}".encode()),
        ]
    ]
    await _notify_admins(notif, buttons=buttons)

    await upsert_message(
        event,
        "✅ Request tambahan kuota dikirim ke admin.",
        buttons=[[Button.inline("⬅️ Menu", b"menu")]],
    )


@bot.on(events.CallbackQuery(pattern=b"^q-appr:(\\d+)$"))
async def quota_approve_handler(event):
    if not await require_admin(event):
        return

    sender = await event.get_sender()
    request_id = int(event.pattern_match.group(1).decode("ascii"))
    req = get_quota_request(request_id)
    if not req or str(req.get("status")) != "pending":
        await upsert_message(event, "⚠️ Request kuota sudah diproses atau tidak ditemukan.")
        return

    target_id = str(req.get("tg_id") or "")
    current = get_user_limits(target_id)

    note = await ask_text(
        event,
        event.chat_id,
        sender.id,
        "📝 Catatan approve (opsional, ketik `-` jika kosong):",
    )
    note = _optional_reason(note)

    ssh_in = await ask_text(
        event,
        event.chat_id,
        sender.id,
        f"🔢 Limit SSH baru untuk user `{target_id}` (angka, 0=unlimited, kosong={current.get('ssh_limit', 0)}):",
    )
    xray_in = await ask_text(
        event,
        event.chat_id,
        sender.id,
        f"🔢 Limit XRAY baru untuk user `{target_id}` (angka, 0=unlimited, kosong={current.get('xray_limit', 0)}):",
    )

    ssh_limit = ssh_in.strip() if str(ssh_in or "").strip().isdigit() else current.get("ssh_limit", 0)
    xray_limit = xray_in.strip() if str(xray_in or "").strip().isdigit() else current.get("xray_limit", 0)

    result = process_quota_request(
        request_id,
        str(sender.id),
        True,
        note,
        new_ssh_limit=ssh_limit,
        new_xray_limit=xray_limit,
    )
    if result is None:
        await upsert_message(event, "⚠️ Request kuota gagal diproses.")
        return

    final_limits = result.get("limits") or get_user_limits(target_id)
    target_msg = (
        "✅ Request tambahan kuota Anda di-approve admin.\n"
        f"• Limit SSH baru: `{final_limits.get('ssh_limit', 0)}` (0=unlimited)\n"
        f"• Limit XRAY baru: `{final_limits.get('xray_limit', 0)}` (0=unlimited)"
    )
    if note:
        target_msg += f"\n\nCatatan admin: `{note}`"
    await _notify_user(target_id, target_msg)

    await upsert_message(
        event,
        f"✅ Request kuota #{request_id} di-approve untuk user `{target_id}`.",
        buttons=[[Button.inline("⬅️ Pending Kuota", b"admin-pending-quota")], [Button.inline("⬅️ Kelola User", b"admin-users")]],
    )


@bot.on(events.CallbackQuery(pattern=b"^q-rej:(\\d+)$"))
async def quota_reject_handler(event):
    if not await require_admin(event):
        return

    sender = await event.get_sender()
    request_id = int(event.pattern_match.group(1).decode("ascii"))
    req = get_quota_request(request_id)
    if not req or str(req.get("status")) != "pending":
        await upsert_message(event, "⚠️ Request kuota sudah diproses atau tidak ditemukan.")
        return

    note = await ask_text(
        event,
        event.chat_id,
        sender.id,
        "📝 Alasan reject (opsional, ketik `-` jika kosong):",
    )
    note = _optional_reason(note)

    result = process_quota_request(request_id, str(sender.id), False, note)
    if result is None:
        await upsert_message(event, "⚠️ Request kuota gagal diproses.")
        return

    target_id = str(result.get("tg_id") or "")
    target_msg = "❌ Request tambahan kuota Anda ditolak admin."
    if note:
        target_msg += f"\n\nAlasan: `{note}`"
    await _notify_user(target_id, target_msg)

    await upsert_message(
        event,
        f"✅ Request kuota #{request_id} ditolak untuk user `{target_id}`.",
        buttons=[[Button.inline("⬅️ Pending Kuota", b"admin-pending-quota")], [Button.inline("⬅️ Kelola User", b"admin-users")]],
    )


@bot.on(events.CallbackQuery(data=b"admin-pending-quota"))
async def pending_quota_list(event):
    if not await require_admin(event):
        return

    pending = list_pending_quota_requests(20)
    if not pending:
        await upsert_message(
            event,
            "📭 Tidak ada request kuota pending.",
            buttons=[[Button.inline("⬅️ Kelola User", b"admin-users")]],
        )
        return

    lines = ["📥 **Pending Request Kuota**", ""]
    buttons = []
    for req in pending:
        rid = req.get("id")
        uid = str(req.get("tg_id") or "-")
        lines.append(f"• #{rid} user `{uid}`")
        reason = str(req.get("reason") or "").strip()
        if reason:
            lines.append(f"  alasan: `{reason}`")
        buttons.append([
            Button.inline(f"✅ #{rid}", f"q-appr:{rid}".encode()),
            Button.inline(f"❌ #{rid}", f"q-rej:{rid}".encode()),
        ])
    lines.append("")
    lines.append(menu_credit())

    buttons.append([Button.inline("⬅️ Kelola User", b"admin-users")])
    await upsert_message(event, "\n".join(lines), buttons=buttons)


@bot.on(events.CallbackQuery(data=b"admin-users"))
async def admin_users_menu(event):
    if not await require_admin(event):
        return

    users = list_managed_users(include_admin=False)
    if not users:
        await upsert_message(
            event,
            "👥 Belum ada user Telegram yang terdaftar.",
            buttons=[[Button.inline("📥 Pending Akses", b"admin-pending-access"), Button.inline("📥 Pending Kuota", b"admin-pending-quota")], [Button.inline("⬅️ Menu", b"menu")]],
        )
        return

    lines = ["👥 **Kelola User Telegram**", "Pilih user untuk lihat statistik, daftar akun, dan aksi admin.", ""]
    buttons = []
    for row in users[:40]:
        uid = str(row.get("tg_id") or "")
        label = _display_user_name(row)
        status = _status_label(row.get("status", ""))
        lines.append(f"• `{uid}` - `{label}` ({status})")

        short_label = label if len(label) <= 18 else label[:15] + "..."
        buttons.append([Button.inline(f"{status[:1]} {short_label}", f"admin-user:{uid}".encode())])

    lines.append("")
    lines.append(menu_credit())

    buttons.append([Button.inline("📥 Pending Akses", b"admin-pending-access"), Button.inline("📥 Pending Kuota", b"admin-pending-quota")])
    buttons.append([Button.inline("⬅️ Menu", b"menu")])
    await upsert_message(event, "\n".join(lines), buttons=buttons)


@bot.on(events.CallbackQuery(pattern=b"^admin-user:(.+)$"))
async def admin_user_detail(event):
    if not await require_admin(event):
        return

    target_id = event.pattern_match.group(1).decode("utf-8", errors="ignore").strip()
    await _show_admin_user_detail(event, target_id)


@bot.on(events.CallbackQuery(pattern=b"^admin-user-(xray|ssh):(.+)$"))
async def admin_user_account_list(event):
    if not await require_admin(event):
        return

    category = event.pattern_match.group(1).decode("ascii").strip().lower()
    target_id = event.pattern_match.group(2).decode("utf-8", errors="ignore").strip()
    row = get_user_record(target_id)
    if not row:
        await upsert_message(event, "❌ User tidak ditemukan.", buttons=[[Button.inline("⬅️ List User", b"admin-users")]])
        return

    accounts = get_user_accounts(target_id, category=category, active_only=True, limit=120)
    if not accounts:
        await upsert_message(
            event,
            f"📭 Tidak ada akun `{category.upper()}` aktif untuk user ini.",
            buttons=[[Button.inline("⬅️ Detail User", f"admin-user:{target_id}".encode())]],
        )
        return

    lines = [f"📋 **List Akun {category.upper()}**", f"User: `{_display_user_name(row)}`", ""]
    for idx, acc in enumerate(accounts, start=1):
        expires = str(acc.get("expires_at") or "-")
        service = str(acc.get("service") or "-").upper()
        trial = " (TRIAL)" if int(acc.get("is_trial", 0) or 0) == 1 else ""
        lines.append(f"{idx}. `{acc.get('username', '-')}` | `{service}`{trial}")
        lines.append(f"   expired: `{expires}`")

    text = "\n".join(lines)
    if len(text) > 3900:
        text = text[:3800] + "\n\n..."

    await upsert_message(
        event,
        text,
        buttons=[[Button.inline("⬅️ Detail User", f"admin-user:{target_id}".encode())]],
    )


@bot.on(events.CallbackQuery(pattern=b"^admin-user-limit:(.+)$"))
async def admin_user_set_limit(event):
    if not await require_admin(event):
        return

    sender = await event.get_sender()
    target_id = event.pattern_match.group(1).decode("utf-8", errors="ignore").strip()
    row = get_user_record(target_id)
    if not row:
        await upsert_message(event, "❌ User tidak ditemukan.")
        return

    current = get_user_limits(target_id)

    ssh_text = await ask_text(
        event,
        event.chat_id,
        sender.id,
        f"🔢 Masukkan limit SSH baru untuk user `{target_id}` (angka, 0=unlimited, kosong={current.get('ssh_limit', 0)}):",
    )
    xray_text = await ask_text(
        event,
        event.chat_id,
        sender.id,
        f"🔢 Masukkan limit XRAY baru untuk user `{target_id}` (angka, 0=unlimited, kosong={current.get('xray_limit', 0)}):",
    )

    next_ssh = ssh_text.strip() if str(ssh_text or "").strip().isdigit() else current.get("ssh_limit", 0)
    next_xray = xray_text.strip() if str(xray_text or "").strip().isdigit() else current.get("xray_limit", 0)

    set_res = set_user_limits(target_id, next_ssh, next_xray, updated_by=str(sender.id))
    new_limits = set_res.get("limits") or get_user_limits(target_id)

    await _notify_user(
        target_id,
        (
            "⚖️ Limit kuota pembuatan akun Anda diperbarui admin.\n"
            f"• SSH: `{new_limits.get('ssh_limit', 0)}` (0=unlimited)\n"
            f"• XRAY: `{new_limits.get('xray_limit', 0)}` (0=unlimited)"
        ),
    )

    await _show_admin_user_detail(
        event,
        target_id,
        notice=(
            "✅ Limit berhasil diperbarui.\n"
            f"SSH: `{new_limits.get('ssh_limit', 0)}` | XRAY: `{new_limits.get('xray_limit', 0)}`"
        ),
    )


@bot.on(events.CallbackQuery(pattern=b"^admin-user-(kick|suspend|unsuspend):(.+)$"))
async def admin_user_status_action(event):
    if not await require_admin(event):
        return

    sender = await event.get_sender()
    action = event.pattern_match.group(1).decode("ascii").strip().lower()
    target_id = event.pattern_match.group(2).decode("utf-8", errors="ignore").strip()

    if is_admin_user(target_id):
        await upsert_message(event, "⛔ Aksi ini tidak berlaku untuk akun admin.")
        return

    row = get_user_record(target_id)
    if not row:
        await upsert_message(event, "❌ User tidak ditemukan.")
        return

    reason = await ask_text(
        event,
        event.chat_id,
        sender.id,
        f"📝 Alasan untuk aksi `{action}` (opsional, ketik `-` jika kosong):",
    )
    reason = _optional_reason(reason)

    status_map = {
        "kick": "kicked",
        "suspend": "suspended",
        "unsuspend": "approved",
    }
    target_status = status_map.get(action, "pending")

    if not set_user_status(target_id, target_status, reason):
        await upsert_message(event, "❌ Gagal memperbarui status user.")
        return

    action_label = action.upper()
    outbound = f"⚠️ Status akses bot Anda diubah admin: `{action_label}`."
    if reason:
        outbound += f"\n\nAlasan: `{reason}`"
    if target_status in {"approved", "pending"}:
        outbound += "\n\nAkses bot Anda sekarang aktif."
    await _notify_user(target_id, outbound)

    await _show_admin_user_detail(
        event,
        target_id,
        notice=f"✅ Aksi `{action_label}` berhasil disimpan untuk user `{target_id}`.",
    )
