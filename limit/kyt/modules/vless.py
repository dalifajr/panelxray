from kyt import *
from kyt.modules.ui import ask_choice, ask_text, build_result, manager_banner, run_command, sanitize_username, send_tls_qr, short_progress

@bot.on(events.CallbackQuery(data=b'create-vless'))
async def create_vless(event):
	async def create_vless_(event):
		user = await ask_text(event, chat, sender.id, "👤 **Masukkan Username VLESS:**")
		pw = await ask_text(event, chat, sender.id, "📦 **Masukkan Quota (GB):**")
		exp = await ask_choice(
			event,
			chat,
			sender.id,
			"📅 **Pilih masa aktif:**",
			["3", "7", "30", "60"],
		)
		await short_progress(event, "Membuat akun VLESS...")
		cmd = f'printf "%s\n" "{user}" "{exp}" "{pw}" | addvless'
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond("❌ **Username sudah terdaftar.**")
		else:
			today = DT.date.today()
			later = today + DT.timedelta(days=int(exp))
			x = [x.group() for x in re.finditer("vless://(.*)",a)]
			uuid = re.search("vless://(.*?)@",x[0]).group(1)
			msg = build_result(
				"VLESS Account Created",
				[
					("Username", user),
					("Host", DOMAIN),
					("XRAY DNS", HOST),
					("Quota", f"{pw} GB"),
					("UUID", uuid),
					("Expired", str(later)),
				],
				[
					("TLS", x[0]),
					("NTLS", x[1].replace(" ", "")),
					("gRPC", x[2].replace(" ", "")),
					("OpenClash", f"https://{DOMAIN}:81/vless-{user}.txt"),
				],
			)
			await event.respond(msg)
			await send_tls_qr(event, x[0], "QR TLS VLESS")
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await create_vless_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'cek-vless'))
async def cek_vless(event):
	async def cek_vless_(event):
		cmd = 'bot-cek-vless'.strip()
		_, z = run_command(cmd)
		z = z or "Tidak ada sesi login VLESS aktif."
		await event.respond(f"""

{z}

**Shows Logged In Users Vless**
**» 🤖@AutoFTbot**
""",buttons=[[Button.inline("‹ Main Menu ›","menu")]])
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await cek_vless_(event)
	else:
		await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'list-vless'))
async def list_vless(event):
	async def list_vless_(event):
		cmd = "grep -E '^### ' /etc/vless/.vless.db 2>/dev/null | awk '{printf \"%-20s %s\\n\",$2,$3}'"
		_, out = run_command(cmd)
		if not out:
			out = "Tidak ada user VLESS."
		await event.respond(f"📋 **Daftar User VLESS**\n```\n{out}\n```")

	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await list_vless_(event)
	else:
		await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'renew-vless'))
async def renew_vless(event):
	async def renew_vless_(event):
		user = await ask_text(event, chat, sender.id, "👤 **Masukkan Username VLESS:**")
		user = sanitize_username(user)
		if not user:
			await event.respond("❌ Username tidak valid. Gunakan huruf/angka/._-")
			return

		days = await ask_choice(event, chat, sender.id, "📅 **Tambah masa aktif (hari):**", ["1", "3", "7", "30", "60"])
		quota = await ask_text(event, chat, sender.id, "📦 **Quota baru (GB, kosong=0):**")
		quota = quota if quota else "0"
		iplim = await ask_text(event, chat, sender.id, "🌐 **Limit IP (kosong=1):**")
		iplim = iplim if iplim else "1"

		await short_progress(event, "Memperpanjang akun VLESS...")
		_, out = run_command("renewvless", [user, days, quota, iplim])
		_, exp = run_command(f"grep -wE '^#& {user} ' /etc/xray/config.json | awk '{{print $3}}' | head -n1")
		if exp:
			msg = build_result(
				"VLESS Account Renewed",
				[
					("Username", user),
					("Added Days", days),
					("Quota", f"{quota} GB"),
					("Limit IP", iplim),
					("Expired", exp),
				],
				[("OpenClash", f"https://{DOMAIN}:81/vless-{user}.txt")],
			)
			await event.respond(msg)
		else:
			await event.respond(f"⚠️ Perpanjangan diproses, cek output:\n```\n{out or 'Tidak ada output'}\n```")

	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await renew_vless_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'delete-vless'))
async def delete_vless(event):
	async def delete_vless_(event):
		async with bot.conversation(chat) as user:
			await event.respond('**Username:**')
			user = user.wait_event(events.NewMessage(incoming=True, from_users=sender.id))
			user = (await user).raw_text
		cmd = f'printf "%s\n" "{user}" | delvless'
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond("**User Not Found**")
		else:
			msg = f"""**Successfully Deleted**"""
			await event.respond(msg)
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await delete_vless_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'suspend-vless'))
async def suspend_vless(event):
	async def suspend_vless_(event):
		async with bot.conversation(chat) as user:
			await event.respond('**Username:**')
			user = user.wait_event(events.NewMessage(incoming=True, from_users=sender.id))
			user = (await user).raw_text
		cmd = f'printf "%s\n" "{user}" | suspvless'
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond("**Failed to suspend user**")
		else:
			await event.respond(f"**{a.strip()}**")
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await suspend_vless_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'unsuspend-vless'))
async def unsuspend_vless(event):
	async def unsuspend_vless_(event):
		async with bot.conversation(chat) as user:
			await event.respond('**Username:**')
			user = user.wait_event(events.NewMessage(incoming=True, from_users=sender.id))
			user = (await user).raw_text
		cmd = f'printf "%s\n" "{user}" | unsuspvless'
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond("**Failed to unsuspend user**")
		else:
			await event.respond(f"**{a.strip()}**")
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await unsuspend_vless_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'trial-vless'))
async def trial_vless(event):
	async def trial_vless_(event):
		exp = await ask_choice(event, chat, sender.id, "⏱️ **Trial VLESS (menit):**", ["10", "15", "30", "60"])
		await short_progress(event, "Membuat trial VLESS...")
		cmd = f'printf "%s\n" "{exp}" | trialvless'
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond("❌ **Gagal membuat trial VLESS.**")
		else:
			x = [x.group() for x in re.finditer("vless://(.*)",a)]
			remarks = re.search("#(.*)",x[0]).group(1)
			uuid = re.search("vless://(.*?)@",x[0]).group(1)
			msg = build_result(
				"VLESS Trial Created",
				[
					("Username", remarks),
					("Host", DOMAIN),
					("UUID", uuid),
					("Mode", "Trial"),
					("Expired", f"{exp} menit"),
				],
				[
					("TLS", x[0]),
					("NTLS", x[1].replace(" ", "")),
					("gRPC", x[2].replace(" ", "")),
				],
			)
			await event.respond(msg)
			await send_tls_qr(event, x[0], "QR TLS VLESS Trial")
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await trial_vless_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'vless'))
async def vless(event):
	async def vless_(event):
		inline = [
			[Button.inline("🧪 Trial", "trial-vless"), Button.inline("➕ Create", "create-vless")],
			[Button.inline("👀 Check Login", "cek-vless"), Button.inline("📋 List User", "list-vless")],
			[Button.inline("🗓️ Renew", "renew-vless"), Button.inline("🗑️ Delete", "delete-vless")],
			[Button.inline("⛔ Suspend", "suspend-vless"), Button.inline("✅ Unsuspend", "unsuspend-vless")],
			[Button.inline("⬅️ Main Menu", "menu")],
		]
		msg = manager_banner("VLESS Manager", "VLESS")
		await event.edit(msg,buttons=inline)
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await vless_(event)
	else:
		await event.answer("Access Denied",alert=True)
