from kyt import *
from kyt.modules.ui import require_access, menu_credit, is_admin

@bot.on(events.NewMessage(pattern=r"(?i)^(?:[./](?:start|mulai)(?:@\w+)?)(?:\s+(login_[a-zA-Z0-9_]+))?\s*$"))
@bot.on(events.CallbackQuery(data=b'start'))
async def start(event):
	logging.info("Received /start command! Sender: %s, Text: %s", event.sender_id, getattr(event, 'text', 'Callback'))
	match = event.pattern_match if hasattr(event, 'pattern_match') else None
	if match and match.lastindex and match.group(1):
		token_str = match.group(1).strip()
		logging.info("Matched token_str: %s", token_str)
		if token_str.startswith("login_"):
			logging.info("Delegating to handle_login_token for %s", token_str)
			return await handle_login_token(event, token_str)
            
	# Determine mode and role
	admin_mode = is_admin(event.sender_id)

	# Load bot mode from .env/var.txt
	bot_mode = globals().get("BOT_MODE", "admin_only")

	# Access control check
	if not await require_access(event):
		return

	if bot_mode == "sales":
		if admin_mode:
			inline = [
				[Button.inline("🚀 Open Panel Menu (Admin)", "menu")],
				[Button.inline("🛒 Beli VPN (Shop)", "shop-menu"), Button.inline("📋 Akun Saya", "my-accounts")],
				[Button.inline("💰 Saldo & Wallet", "wallet-bot")],
				[Button.url("💬 WhatsApp", "https://wa.me/6282269245660")]
			]
		else:
			inline = [
				[Button.inline("🛒 Beli VPN (Shop)", "shop-menu"), Button.inline("📋 Akun Saya", "my-accounts")],
				[Button.inline("💰 Saldo & Wallet", "wallet-bot")],
				[Button.url("💬 WhatsApp", "https://wa.me/6282269245660")]
			]
	else:
		# Default: Admin Only mode
		inline = [
			[Button.inline("🚀 Open Panel Menu", "menu")],
			[Button.url("💬 WhatsApp", "https://wa.me/6282269245660")],
		]

	try:
		sdss = "cat /etc/os-release | grep -w PRETTY_NAME | head -n1 | sed 's/=//g' | sed 's/PRETTY_NAME//g'"
		namaos = subprocess.check_output(sdss, shell=True, timeout=2).decode("ascii").strip().replace('"', '')
	except Exception:
		namaos = "Ubuntu/Debian"

	try:
		ipsaya = subprocess.check_output("curl -s --connect-timeout 2 -m 3 ipv4.icanhazip.com", shell=True, timeout=3).decode("ascii").strip()
	except Exception:
		ipsaya = "unknown"

	try:
		city = subprocess.check_output("cat /etc/xray/city", shell=True, timeout=2).decode("ascii").strip()
	except Exception:
		city = "unknown"

	if bot_mode == "sales" and not admin_mode:
		msg = (
			"👋 **Selamat datang di Bot Jualan VPN**\n"
			f"🌐 **Domain:** `{DOMAIN}`\n\n"
			"🧭 Pilih menu di bawah ini untuk memulai pembelian akun VPN self-service atau mengelola saldo/akun Anda.\n"
			f"{menu_credit()}"
		)
	else:
		msg = (
			"👋 **Welcome to PanelXray Bot**\n"
			f"🖥️ **OS:** `{namaos}`\n"
			f"🏙️ **City:** `{city}`\n"
			f"🌐 **Domain:** `{DOMAIN}`\n"
			f"📡 **IP VPS:** `{ipsaya}`\n\n"
			"🧭 Gunakan tombol menu untuk mulai mengelola VPN.\n"
			"🏠 Anda juga bisa ketik `/mulai` kapan saja untuk kembali ke halaman ini.\n"
			f"{menu_credit()}"
		)

	try:
		await event.edit(msg, buttons=inline)
	except Exception:
		await event.reply(msg, buttons=inline)

async def handle_login_token(event, token):
    logging.info("Entering handle_login_token with token: %s for sender_id: %s", token, event.sender_id)
        
    try:
        domain = globals().get("DOMAIN", "localhost")
        logging.info("Using domain: %s", domain)
        # Call Laravel API to approve token
        import urllib.request
        import urllib.error
        import json
        import ssl
        req = urllib.request.Request(
            "https://127.0.0.1:81/api/internal/approve-token",
            data=json.dumps({"token": token.replace('login_', ''), "tg_id": str(event.sender_id)}).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'X-Internal-Secret': 'secret123'},
            method='POST'
        )
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
                res_data = json.loads(response.read().decode())
                logging.info("API response: %s", res_data)
                
            await event.reply(
                f"✅ **Berhasil!**\n\n"
                f"Token `{token}` telah diotorisasi.\n"
                f"Silakan kembali ke browser Anda atau klik link di bawah ini:",
                buttons=[[Button.url("Buka Web Panel", f"https://{domain}/login/verify?token={token.replace('login_', '')}")]]
            )
        except urllib.error.HTTPError as e:
            try:
                err_data = json.loads(e.read().decode())
                err_msg = err_data.get('message', err_data.get('error', str(e)))
                await event.reply(f"❌ **Gagal:**\n{err_msg}")
            except Exception:
                await event.reply(f"❌ Gagal memproses token login (HTTP {e.code})")
    except Exception as e:
        logging.error("Exception in handle_login_token: %s", e)
        await event.reply(f"❌ Terjadi kesalahan internal: {e}")


