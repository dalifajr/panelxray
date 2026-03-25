from kyt import *
import asyncio
from urllib.parse import quote


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


async def ask_text(event, chat_id: int, sender_id: int, prompt: str) -> str:
    async with bot.conversation(chat_id) as conv:
        await event.respond(prompt)
        reply = await conv.get_response()
        if str(reply.sender_id) != str(sender_id):
            return ""
        reply = reply.raw_text.strip()
    return reply


async def ask_choice(event, chat_id: int, sender_id: int, prompt: str, options):
    options = [str(x).strip() for x in options]
    option_label = ", ".join(options)
    async with bot.conversation(chat_id) as conv:
        await event.respond(f"{prompt}\nKetik salah satu: {option_label}")
        reply = await conv.get_response()
        if str(reply.sender_id) != str(sender_id):
            return options[0]
        picked = reply.raw_text.strip()
        if picked not in options:
            return options[0]
    return picked


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


def manager_banner(title: str, service: str) -> str:
    isp, country = get_geo()
    server = globals().get("DOMAIN", "-")
    return (
        f"📋 **{title}**\n"
        f"📍 **Server:** `{server}`\n"
        f"🛠️ **Service:** `{service}`\n"
        f"🌐 **ISP:** `{isp}`\n"
        f"🌏 **Country:** `{country}`"
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

    qr_url = (
        "https://api.qrserver.com/v1/create-qr-code/"
        f"?size=600x600&format=png&data={quote(tls_link, safe='')}"
    )

    caption = f"🧾 **{title}**\n🔐 Scan QR ini untuk koneksi TLS."
    try:
        await event.respond(caption, file=qr_url)
    except Exception:
        await event.respond(f"{caption}\n{qr_url}")
