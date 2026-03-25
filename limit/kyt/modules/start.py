from kyt import *
from kyt.modules.ui import require_admin

@bot.on(events.NewMessage(pattern=r"(?:.start|/start)$"))
@bot.on(events.CallbackQuery(data=b'start'))
async def start(event):
	inline = [
		[Button.inline("🚀 Open Panel Menu", "menu")],
		[Button.inline("🧰 Create VPN Cepat", "create-menu")],
		[Button.url("💬 WhatsApp", "https://wa.me/6282269245660")],
	]

	if not await require_admin(event):
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
		f"📡 **IP VPS:** `{ipsaya}`"
	)

	x = await event.edit(msg, buttons=inline)
	if not x:
		await event.reply(msg, buttons=inline)





