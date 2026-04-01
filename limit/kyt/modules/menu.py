from kyt import *
from kyt.modules.ui import manager_banner, require_access, menu_credit, is_admin


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
	if not await require_access(event):
		return

	sender = await event.get_sender()
	admin_mode = is_admin(sender.id)

	if admin_mode:
		inline = [
			[Button.inline("👤 SSH", "ssh"), Button.inline("🛰️ VMESS", "vmess")],
			[Button.inline("🧩 VLESS", "vless"), Button.inline("🛡️ TROJAN", "trojan")],
			[Button.inline("🌘 SHADOWSOCKS", "shadowsocks"), Button.inline("📊 VPS Info", "info")],
			[Button.inline("👥 Kelola User", "admin-users"), Button.inline("⚙️ Settings", "setting")],
			[Button.inline("⬅️ Back", "start")],
		]
	else:
		inline = [
			[Button.inline("👤 SSH", "ssh"), Button.inline("🛰️ VMESS", "vmess")],
			[Button.inline("🧩 VLESS", "vless"), Button.inline("🛡️ TROJAN", "trojan")],
			[Button.inline("🌘 SHADOWSOCKS", "shadowsocks")],
			[Button.inline("📈 Kuota Saya", "quota-my"), Button.inline("📨 Request Kuota", "quota-request")],
			[Button.inline("⬅️ Back", "start")],
		]

	# Keep source in sync with shell panel counters.
	ssh = _run_count("awk -F: '$3>=1000 && $1!=\"nobody\" {c++} END{print c+0}' /etc/passwd 2>/dev/null")
	vms = _run_count("grep -c -E '^### ' /etc/xray/config.json 2>/dev/null", divisor=2)
	vls = _run_count("grep -c -E '^#& ' /etc/xray/config.json 2>/dev/null", divisor=2)
	trj = _run_count("grep -c -E '^#! ' /etc/xray/config.json 2>/dev/null", divisor=2)
	ssn = _run_count("grep -c -E '^#!# ' /etc/xray/config.json 2>/dev/null", divisor=2)

	if admin_mode:
		msg = (
			f"{manager_banner('PanelXray Telegram Bot', 'All Services')}\n\n"
			f"📦 **Total Account**\n"
			f"▪ SSH: `{ssh}`\n"
			f"▪ VMESS: `{vms}`\n"
			f"▪ VLESS: `{vls}`\n"
			f"▪ TROJAN: `{trj}`\n"
			f"▪ SHADOWSOCKS: `{ssn}`"
		)
	else:
		stats = get_user_stats(str(sender.id))
		limits = get_user_limits(str(sender.id))
		ssh_limit_text = "unlimited" if int(limits.get("ssh_limit", 0)) <= 0 else str(limits.get("ssh_limit", 0))
		xray_limit_text = "unlimited" if int(limits.get("xray_limit", 0)) <= 0 else str(limits.get("xray_limit", 0))
		msg = (
			f"{manager_banner('PanelXray Telegram Bot', 'User Access')}\n\n"
			f"📊 **Stat Akun Anda**\n"
			f"▪ SSH dibuat: `{stats.get('ssh_total', 0)}` / `{ssh_limit_text}`\n"
			f"▪ XRAY dibuat: `{stats.get('xray_total', 0)}` / `{xray_limit_text}`\n"
			f"\nGunakan menu di bawah untuk membuat akun atau request kuota tambahan."
		)

	x = await event.edit(msg, buttons=inline)
	if not x:
		await event.reply(msg, buttons=inline)


@bot.on(events.CallbackQuery(data=b'create-menu'))
async def create_menu(event):
	if not await require_access(event):
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
		"✨ Alur input sudah dirapikan agar lebih intuitif.\n"
		f"{menu_credit()}"
	)
	await event.edit(msg, buttons=inline)


