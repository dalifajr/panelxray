from kyt import *
from kyt.modules.ui import manager_banner, require_admin

@bot.on(events.NewMessage(pattern=r"(?:.menu|/menu)$"))
@bot.on(events.CallbackQuery(data=b'menu'))
async def menu(event):
	inline = [
		[Button.inline("🧰 Create VPN", "create-menu")],
		[Button.inline("👤 SSH", "ssh"), Button.inline("🛰️ VMESS", "vmess")],
		[Button.inline("🧩 VLESS", "vless"), Button.inline("🛡️ TROJAN", "trojan")],
		[Button.inline("🌘 SHADOWSOCKS", "shadowsocks"), Button.inline("📊 VPS Info", "info")],
		[Button.inline("⚙️ Settings", "setting")],
		[Button.inline("⬅️ Back", "start")],
	]

	if not await require_admin(event):
		return

	sh = 'cat /etc/ssh/.ssh.db | grep "###" | wc -l'
	ssh = subprocess.check_output(sh, shell=True).decode("ascii").strip()
	vm = 'cat /etc/vmess/.vmess.db | grep "###" | wc -l'
	vms = subprocess.check_output(vm, shell=True).decode("ascii").strip()
	vl = 'cat /etc/vless/.vless.db | grep "###" | wc -l'
	vls = subprocess.check_output(vl, shell=True).decode("ascii").strip()
	tr = 'cat /etc/trojan/.trojan.db | grep "###" | wc -l'
	trj = subprocess.check_output(tr, shell=True).decode("ascii").strip()
	ss = 'cat /etc/shadowsocks/.shadowsocks.db 2>/dev/null | grep "###" | wc -l'
	try:
		ssn = subprocess.check_output(ss, shell=True).decode("ascii").strip()
	except Exception:
		ssn = "0"

	msg = (
		f"{manager_banner('PanelXray Telegram Bot', 'All Services')}\n\n"
		f"📦 **Total Account**\n"
		f"▪ SSH: `{ssh}`\n"
		f"▪ VMESS: `{vms}`\n"
		f"▪ VLESS: `{vls}`\n"
		f"▪ TROJAN: `{trj}`\n"
		f"▪ SHADOWSOCKS: `{ssn}`"
	)

	x = await event.edit(msg, buttons=inline)
	if not x:
		await event.reply(msg, buttons=inline)


@bot.on(events.CallbackQuery(data=b'create-menu'))
async def create_menu(event):
	if not await require_admin(event):
		return

	inline = [
		[Button.inline("➕ SSH", "create-ssh"), Button.inline("➕ VMESS", "create-vmess")],
		[Button.inline("➕ VLESS", "create-vless"), Button.inline("➕ TROJAN", "create-trojan")],
		[Button.inline("➕ SHADOWSOCKS", "create-shadowsocks")],
		[Button.inline("⬅️ Back to Main Menu", "menu")],
	]

	msg = (
		"🧰 **Create VPN Menu**\n"
		"Pilih protokol yang ingin dibuat.\n"
		"Semua create account sekarang memakai layout hasil yang ringkas."
	)
	await event.edit(msg, buttons=inline)


