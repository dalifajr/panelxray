from kyt import *
from kyt.modules.ui import require_access, menu_credit

@bot.on(events.NewMessage(pattern=r"(?i)^(?:[./](?:start|mulai)(?:@\w+)?)(?:\s+(login_[a-zA-Z0-9_]+))?\s*$"))
@bot.on(events.CallbackQuery(data=b'start'))
async def start(event):
	match = event.pattern_match
	if match and match.lastindex and match.group(1):
		token_str = match.group(1).strip()
		if token_str.startswith("login_"):
			return await handle_login_token(event, token_str)
            
	inline = [
		[Button.inline("🚀 Open Panel Menu", "menu")],
		[Button.url("💬 WhatsApp", "https://wa.me/6282269245660")],
	]

	if not await require_access(event):
		return

	sdss = "cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/PRETTY_NAME//g'"
	namaos = subprocess.check_output(sdss, shell=True).decode("ascii").strip().replace('"', '')
	ipsaya = subprocess.check_output("curl -s ipv4.icanhazip.com", shell=True).decode("ascii").strip()
	city = subprocess.check_output("cat /etc/xray/city", shell=True).decode("ascii").strip()

	msg = (
		"👋 **Welcome to PanelXray Bot**\n"
		f"🖥️ **OS:** `{namaos}`\n"
		f"🏙️ **City:** `{city}`\n"
		f"🌐 **Domain:** `{DOMAIN}`\n"
		f"📡 **IP VPS:** `{ipsaya}`\n\n"
		"🧭 Gunakan tombol `Open Panel Menu` untuk mulai kelola akun.\n"
		"🏠 Anda juga bisa ketik `/mulai` kapan saja untuk kembali ke halaman ini.\n"
		f"{menu_credit()}"
	)

	x = await event.edit(msg, buttons=inline)
	if not x:
		await event.reply(msg, buttons=inline)

async def handle_login_token(event, token):
    if not is_admin_user(str(event.sender_id)):
        await event.reply("⛔ Hanya admin yang dapat login ke Web Panel.")
        return
        
    try:
        domain = globals().get("DOMAIN", "localhost")
        # Call Laravel API to approve token
        import urllib.request
        import json
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/internal/approve-token",
            data=json.dumps({"token": token.replace('login_', ''), "tg_id": str(event.sender_id)}).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'X-Internal-Secret': 'secret123'},
            method='POST'
        )
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
            
        await event.reply(
            f"✅ **Login Berhasil!**\n\n"
            f"Token `{token}` telah diotorisasi untuk sesi admin Anda.\n"
            f"Silakan kembali ke browser Anda atau klik link di bawah ini:",
            buttons=[[Button.url("Buka Web Panel", f"https://{domain}/login/verify?token={token.replace('login_', '')}")]]
        )
    except Exception as e:
        await event.reply(f"❌ Gagal memproses token login: {e}")


