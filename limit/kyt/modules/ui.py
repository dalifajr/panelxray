from kyt import *
import asyncio
from urllib.parse import quote
import io

# Global storage untuk callback data sementara
_callback_data = {}


def is_admin(sender_id: int) -> bool:
    return valid(str(sender_id)) == "true"


async def require_admin(event) -> bool:
    sender = await event.get_sender()
    if not is_admin(sender.id):
        try:
            await event.answer("Akses ditolak", alert=True)
        except Exception:
            await event.respond("Akses ditolak")
        return False
    return True


async def delete_messages(chat_id: int, msg_ids: list):
    """Delete multiple messages silently"""
    try:
        if msg_ids:
            await bot.delete_messages(chat_id, msg_ids)
    except Exception:
        pass


async def upsert_message(event, text: str, buttons=None, file=None, force_document: bool = False):
    """Edit current callback message when possible; fallback to new message."""
    try:
        if file is None:
            return await event.edit(text, buttons=buttons)

        if not force_document:
            return await event.edit(text, file=file, buttons=buttons)
    except Exception:
        pass

    if file is None:
        return await event.respond(text, buttons=buttons)

    return await bot.send_file(
        event.chat_id,
        file=file,
        caption=text,
        force_document=force_document,
        buttons=buttons,
    )


async def ask_text_clean(event, chat_id: int, sender_id: int, prompt: str, msg_to_delete: list = None) -> tuple:
    """Ask for text input and return (value, messages_to_delete)"""
    msgs_to_del = msg_to_delete or []
    async with bot.conversation(chat_id, timeout=180) as conv:
        await upsert_message(event, prompt)
        try:
            reply = await conv.wait_event(
                events.NewMessage(incoming=True, from_users=sender_id),
                timeout=180,
            )
            msgs_to_del.append(reply.id)
        except asyncio.TimeoutError:
            await event.respond("⏱️ Waktu input habis. Silakan ulangi dari menu.")
            return "", msgs_to_del

        return (reply.raw_text or "").strip(), msgs_to_del


async def ask_text(event, chat_id: int, sender_id: int, prompt: str) -> str:
    async with bot.conversation(chat_id, timeout=180) as conv:
        await event.respond(prompt)
        try:
            reply = await conv.wait_event(
                events.NewMessage(incoming=True, from_users=sender_id),
                timeout=180,
            )
        except asyncio.TimeoutError:
            await event.respond("⏱️ Waktu input habis. Silakan ulangi dari menu.")
            return ""

        return (reply.raw_text or "").strip()


async def ask_choice(event, chat_id: int, sender_id: int, prompt: str, options):
    options = [str(x).strip() for x in options]
    option_label = ", ".join(options)
    async with bot.conversation(chat_id, timeout=180) as conv:
        await event.respond(f"{prompt}\nKetik salah satu: {option_label}")
        try:
            reply = await conv.wait_event(
                events.NewMessage(incoming=True, from_users=sender_id),
                timeout=180,
            )
        except asyncio.TimeoutError:
            await event.respond("⏱️ Waktu input habis. Dipilih default.")
            return options[0]

        picked = (reply.raw_text or "").strip()
        if picked not in options:
            return options[0]
    return picked


async def ask_choice_buttons(event, chat_id: int, sender_id: int, prompt: str, options: list, callback_prefix: str) -> str:
    """
    Ask user to select from inline buttons instead of typing.
    Returns the selected option value.
    """
    # Build inline keyboard
    buttons = []
    row = []
    for opt in options:
        callback_data = f"{callback_prefix}_{opt}".encode()
        row.append(Button.inline(opt, callback_data))
        if len(row) >= 3:  # Max 3 buttons per row
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([Button.inline("❌ Batal", f"{callback_prefix}_CANCEL".encode())])
    
    # Store expected sender
    key = f"{callback_prefix}_{chat_id}_{sender_id}"
    _callback_data[key] = {"waiting": True, "value": None}
    
    prompt_msg = await event.respond(prompt, buttons=buttons)
    
    # Wait for callback
    try:
        start_time = asyncio.get_event_loop().time()
        while _callback_data.get(key, {}).get("waiting", False):
            await asyncio.sleep(0.3)
            if asyncio.get_event_loop().time() - start_time > 60:  # 60 sec timeout
                break
        
        result = _callback_data.get(key, {}).get("value", options[0])
        if result == "CANCEL":
            await prompt_msg.delete()
            return ""
        await prompt_msg.delete()
        return result if result else options[0]
    finally:
        _callback_data.pop(key, None)


def register_choice_callback(callback_prefix: str):
    """
    Register callback handler for choice buttons.
    Call this once per prefix in the module.
    """
    @bot.on(events.CallbackQuery(pattern=f"^{callback_prefix}_(.+)$"))
    async def handle_choice(event):
        sender = await event.get_sender()
        chat_id = event.chat_id
        match = re.match(f"^{callback_prefix}_(.+)$", event.data.decode())
        if match:
            value = match.group(1)
            key = f"{callback_prefix}_{chat_id}_{sender.id}"
            if key in _callback_data:
                _callback_data[key]["value"] = value
                _callback_data[key]["waiting"] = False
                await event.answer()


async def ask_expiry(event, chat_id: int, sender_id: int, is_trial: bool = False) -> tuple:
    """
    Ask for expiry with buttons for common options + custom input option.
    Returns (value, messages_to_delete)
    """
    msgs_to_del = []
    
    if is_trial:
        # Trial: minutes
        buttons = [
            [Button.inline("10 Menit", b"exp_10"), Button.inline("15 Menit", b"exp_15")],
            [Button.inline("30 Menit", b"exp_30"), Button.inline("60 Menit", b"exp_60")],
            [Button.inline("Custom", b"exp_custom")],
            [Button.inline("❌ Batal", b"exp_cancel")],
        ]
        prompt = "⏱️ **Pilih durasi trial:**"
    else:
        # Regular: days
        buttons = [
            [Button.inline("1 Hari", b"exp_1"), Button.inline("3 Hari", b"exp_3"), Button.inline("7 Hari", b"exp_7")],
            [Button.inline("14 Hari", b"exp_14"), Button.inline("30 Hari", b"exp_30"), Button.inline("60 Hari", b"exp_60")],
            [Button.inline("90 Hari", b"exp_90"), Button.inline("Custom", b"exp_custom")],
            [Button.inline("❌ Batal", b"exp_cancel")],
        ]
        prompt = "📅 **Pilih masa aktif:**"
    
    key = f"exp_{chat_id}_{sender_id}"
    _callback_data[key] = {"waiting": True, "value": None}
    
    await upsert_message(event, prompt, buttons=buttons)
    
    try:
        start_time = asyncio.get_event_loop().time()
        while _callback_data.get(key, {}).get("waiting", False):
            await asyncio.sleep(0.3)
            if asyncio.get_event_loop().time() - start_time > 60:
                break
        
        result = _callback_data.get(key, {}).get("value", "")
        
        if result == "cancel":
            return "", msgs_to_del
        
        if result == "custom":
            msgs_to_del = []
            unit = "menit" if is_trial else "hari"
            custom_prompt = f"📝 **Masukkan jumlah {unit} (angka saja):**"
            async with bot.conversation(chat_id, timeout=180) as conv:
                await upsert_message(event, custom_prompt)
                try:
                    reply = await conv.wait_event(
                        events.NewMessage(incoming=True, from_users=sender_id),
                        timeout=180,
                    )
                    msgs_to_del.append(reply.id)
                    val = (reply.raw_text or "").strip()
                    if val.isdigit() and int(val) > 0:
                        return val, msgs_to_del
                    return "7" if not is_trial else "30", msgs_to_del
                except asyncio.TimeoutError:
                    return "7" if not is_trial else "30", msgs_to_del
        
        msgs_to_del = []
        return result if result else ("7" if not is_trial else "30"), msgs_to_del
    finally:
        _callback_data.pop(key, None)


async def ask_config_mode(event, chat_id: int, sender_id: int) -> tuple:
    """Ask for config mode with buttons. Returns (value, messages_to_delete)"""
    msgs_to_del = []
    
    buttons = [
        [Button.inline("TLS", b"cfg_TLS"), Button.inline("N-TLS", b"cfg_NTLS")],
        [Button.inline("gRPC", b"cfg_GRPC"), Button.inline("ALL", b"cfg_ALL")],
        [Button.inline("❌ Batal", b"cfg_cancel")],
    ]
    prompt = "⚙️ **Pilih konfigurasi:**"
    
    key = f"cfg_{chat_id}_{sender_id}"
    _callback_data[key] = {"waiting": True, "value": None}
    
    await upsert_message(event, prompt, buttons=buttons)
    
    try:
        start_time = asyncio.get_event_loop().time()
        while _callback_data.get(key, {}).get("waiting", False):
            await asyncio.sleep(0.3)
            if asyncio.get_event_loop().time() - start_time > 60:
                break
        
        result = _callback_data.get(key, {}).get("value", "TLS")
        
        if result == "cancel":
            return "", msgs_to_del
        
        msgs_to_del = []
        return result if result else "TLS", msgs_to_del
    finally:
        _callback_data.pop(key, None)


async def ask_sni_profile(event, chat_id: int, sender_id: int) -> tuple:
    """Ask for SNI profile with buttons. Returns (value, messages_to_delete)"""
    msgs_to_del = []
    
    buttons = [
        [Button.inline("support.zoom.us", b"sni_1")],
        [Button.inline("live.iflix.com", b"sni_2")],
        [Button.inline("Tanpa SNI", b"sni_3")],
        [Button.inline("❌ Batal", b"sni_cancel")],
    ]
    prompt = "🌐 **Pilih profil SNI:**"
    
    key = f"sni_{chat_id}_{sender_id}"
    _callback_data[key] = {"waiting": True, "value": None}
    
    await upsert_message(event, prompt, buttons=buttons)
    
    try:
        start_time = asyncio.get_event_loop().time()
        while _callback_data.get(key, {}).get("waiting", False):
            await asyncio.sleep(0.3)
            if asyncio.get_event_loop().time() - start_time > 60:
                break
        
        result = _callback_data.get(key, {}).get("value", "1")
        
        if result == "cancel":
            return "", msgs_to_del
        
        msgs_to_del = []
        return result if result else "1", msgs_to_del
    finally:
        _callback_data.pop(key, None)


# Register callback handlers for buttons
@bot.on(events.CallbackQuery(pattern=b"^exp_(.+)$"))
async def handle_exp_callback(event):
    sender = await event.get_sender()
    chat_id = event.chat_id
    match = re.match(b"^exp_(.+)$", event.data)
    if match:
        value = match.group(1).decode()
        key = f"exp_{chat_id}_{sender.id}"
        if key in _callback_data:
            _callback_data[key]["value"] = value
            _callback_data[key]["waiting"] = False
            await event.answer()


@bot.on(events.CallbackQuery(pattern=b"^cfg_(.+)$"))
async def handle_cfg_callback(event):
    sender = await event.get_sender()
    chat_id = event.chat_id
    match = re.match(b"^cfg_(.+)$", event.data)
    if match:
        value = match.group(1).decode()
        key = f"cfg_{chat_id}_{sender.id}"
        if key in _callback_data:
            _callback_data[key]["value"] = value
            _callback_data[key]["waiting"] = False
            await event.answer()


@bot.on(events.CallbackQuery(pattern=b"^sni_(.+)$"))
async def handle_sni_callback(event):
    sender = await event.get_sender()
    chat_id = event.chat_id
    match = re.match(b"^sni_(.+)$", event.data)
    if match:
        value = match.group(1).decode()
        key = f"sni_{chat_id}_{sender.id}"
        if key in _callback_data:
            _callback_data[key]["value"] = value
            _callback_data[key]["waiting"] = False
            await event.answer()


async def short_progress(event, text: str = "Menyiapkan akun"):
    steps = [
        "⏳ Memproses permintaan...",
        "🛠️ Menjalankan modul panel...",
        f"✅ {text}",
    ]
    for item in steps:
        await event.edit(item)
        await asyncio.sleep(0.5)


def get_geo():
    try:
        data = requests.get(
            "http://ip-api.com/json/?fields=country,isp", timeout=5
        ).json()
        return data.get("isp", "Unknown"), data.get("country", "Unknown")
    except Exception:
        return "Unknown", "Unknown"


def menu_credit() -> str:
    # Use Unicode italic glyphs so style stays consistent even if markdown parsing varies.
    return "𝘤𝘳𝘦𝘢𝘵𝘦𝘥 𝘣𝘺: 𝘥𝘻𝘶𝘭𝘧𝘪𝘬𝘳𝘪𝘢𝘭𝘪𝘧𝘢𝘫𝘳𝘪 𝘴𝘵𝘰𝘳𝘦𝘴"


def back_button(target: str):
    return [[Button.inline("⬅️ Kembali", target)]]


def manager_banner(title: str, service: str) -> str:
    isp, country = get_geo()
    server = globals().get("DOMAIN", "-")
    return (
        f"📋 **{title}**\n"
        f"� **Server:** `{server}`\n"
        f"🛠️ **Service:** `{service}`\n"
        f"� **ISP:** `{isp}`\n"
        f"� **Country:** `{country}`\n"
        f"✨ Gunakan tombol di bawah untuk navigasi cepat.\n"
        f"{menu_credit()}"
    )


def build_result(title: str, fields, links):
    lines = [f"✅ **{title}**", ""]
    for label, value in fields:
        lines.append(f"▸ **{label}:** `{value}`")
    if links:
        lines.append("")
        lines.append("🔗 **Connection Links**")
        for label, value in links:
            if value:
                lines.append(f"▪ **{label}:** `{value}`")
    return "\n".join(lines)


async def send_tls_qr(event, tls_link: str, title: str = "TLS QR"):
    if not tls_link:
        return

    caption = f"🧾 **{title}**\n🔐 Scan QR ini untuk koneksi TLS."
    qr_url = get_qr_url(tls_link, 512)
    try:
        photo = fetch_qr_photo(tls_link, 512)
        if photo is None:
            raise RuntimeError("QR generation failed")
        photo.name = "create-qr-code.png"
        await upsert_message(event, caption, file=photo, force_document=True)
    except Exception:
        if qr_url:
            try:
                await upsert_message(event, caption, file=qr_url, force_document=True)
                return
            except Exception:
                pass
        await upsert_message(event, f"{caption}\n⚠️ QR code gagal dibuat saat ini.")


def get_qr_url(link: str, size: int = 200) -> str:
    """Generate QR code URL for a link"""
    if not link:
        return ""
    return (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size={size}x{size}&format=png&qzone=2&ecc=H&data={quote(link, safe='')}"
    )


def fetch_qr_photo(link: str, size: int = 512):
    """Fetch QR image bytes with resilient fallbacks, avoiding long GET URLs when possible."""
    if not link:
        return None

    endpoints = [
        (
            "POST",
            "https://api.qrserver.com/v1/create-qr-code/",
            {
                "size": f"{size}x{size}",
                "format": "png",
                "qzone": "2",
                "ecc": "H",
                "data": link,
            },
        ),
        (
            "GET",
            "https://quickchart.io/qr",
            {
                "size": str(size),
                "ecLevel": "H",
                "margin": "2",
                "text": link,
            },
        ),
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (PanelXrayBot QR Fetcher)",
    }

    for method, url, payload in endpoints:
        try:
            if method == "POST":
                resp = requests.post(url, data=payload, headers=headers, timeout=25)
            else:
                resp = requests.get(url, params=payload, headers=headers, timeout=25)
            resp.raise_for_status()
            if not resp.content:
                continue
            photo = io.BytesIO(resp.content)
            photo.seek(0)
            photo.name = "create-qr-code.png"
            return photo
        except Exception:
            continue

    return None


async def send_account_with_qr(event, msg: str, qr_link: str, qr_title: str = "QR Code", buttons=None):
    """
    Send account details with QR code in a single message (as photo with caption).
    """
    if not qr_link:
        await upsert_message(event, msg, buttons=buttons)
        return

    home_hint = "🏠 Ketik /menu untuk kembali ke menu utama."
    full_caption = f"{msg}\n\n🧾 **{qr_title}**\n🔐 Scan QR untuk koneksi.\n\n{home_hint}"
    if len(full_caption) > 1020:
        available = 1020 - len(home_hint) - 8
        full_caption = f"{full_caption[:max(200, available)]}\n\n...\n\n{home_hint}"
    
    try:
        photo = fetch_qr_photo(qr_link, 512)
        if photo is None:
            raise RuntimeError("QR generation failed")
        await upsert_message(event, full_caption, file=photo, buttons=buttons, force_document=True)
    except Exception:
        fallback_url = get_qr_url(qr_link, 512)
        if fallback_url:
            try:
                await upsert_message(
                    event,
                    full_caption,
                    file=fallback_url,
                    buttons=buttons,
                    force_document=True,
                )
                return
            except Exception:
                pass
        await upsert_message(
            event,
            f"{msg}\n\n⚠️ QR code gagal dibuat saat ini. Silakan coba lagi.\n\n{home_hint}",
            buttons=buttons,
        )


async def notify_then_back(event, text: str, back_handler, delay: int = 3):
    """Show a short notification then return to previous menu."""
    await upsert_message(event, f"{text}\n\n↩️ Kembali ke menu sebelumnya dalam {delay} detik...")
    await asyncio.sleep(max(1, int(delay)))
    await back_handler(event)


def sanitize_username(value: str) -> str:
    value = (value or "").strip()
    if re.fullmatch(r"[A-Za-z0-9_.-]{1,32}", value):
        return value
    return ""


def sanitize_panel_username(value: str) -> str:
    # addws/addvless/addtr historically expect alnum+underscore usernames.
    value = (value or "").strip()
    if re.fullmatch(r"[A-Za-z0-9_]{1,32}", value):
        return value
    return ""


def run_command(command: str, inputs=None):
    if inputs is None:
        try:
            proc = subprocess.run(
                command,
                shell=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            return 124, "Perintah timeout (>180 detik)."
    else:
        payload = "".join(f"{str(v).strip()}\n" for v in inputs)
        try:
            proc = subprocess.run(
                command,
                shell=True,
                text=True,
                input=payload,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            return 124, "Perintah timeout (>180 detik)."

    return proc.returncode, (proc.stdout or "").strip()
