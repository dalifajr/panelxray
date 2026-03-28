from kyt import *
from kyt.modules.ui import manager_banner, require_admin


def _run_count(cmd: str, divisor: int = 1) -> str:
	try:
		out = subprocess.check_output(cmd, shell=True).decode("ascii", errors="ignore").strip()
		val = int(out or "0")
		if divisor > 1:
			val = val // divisor
		return str(max(0, val))
	except Exception:
		return "0"

@bot.on(events.NewMessage(pattern=r"(?:.menu|/menu)$"))
@bot.on(events.CallbackQuery(data=b'menu'))
async def menu(event):
	inline = [
		[Button.inline("👤 SSH", "ssh"), Button.inline("🛰️ VMESS", "vmess")],
		[Button.inline("🧩 VLESS", "vless"), Button.inline("🛡️ TROJAN", "trojan")],
		[Button.inline("🌘 SHADOWSOCKS", "shadowsocks"), Button.inline("📊 VPS Info", "info")],
		[Button.inline("⚙️ Settings", "setting")],
		[Button.inline("⬅️ Back", "start")],
	]

	if not await require_admin(event):
		return

	# Keep source in sync with shell panel counters.
	ssh = _run_count("awk -F: '$3>=1000 && $1!=\"nobody\" {c++} END{print c+0}' /etc/passwd 2>/dev/null")
	vms = _run_count("grep -c -E '^### ' /etc/xray/config.json 2>/dev/null", divisor=2)
	vls = _run_count("grep -c -E '^#& ' /etc/xray/config.json 2>/dev/null", divisor=2)
	trj = _run_count("grep -c -E '^#! ' /etc/xray/config.json 2>/dev/null", divisor=2)
	ssn = _run_count("grep -c -E '^#!# ' /etc/xray/config.json 2>/dev/null", divisor=2)

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


