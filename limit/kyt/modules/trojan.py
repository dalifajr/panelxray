from kyt import *
from kyt.modules.ui import ask_choice, ask_text, build_result, manager_banner, run_command, sanitize_username, send_tls_qr, short_progress

@bot.on(events.CallbackQuery(data=b'create-trojan'))
async def create_trojan(event):
	async def create_trojan_(event):
		user = await ask_text(event, chat, sender.id, "👤 **Masukkan Username TROJAN:**")
		pw = await ask_text(event, chat, sender.id, "📦 **Masukkan Quota (GB):**")
		exp = await ask_choice(
			event,
			chat,
			sender.id,
			"📅 **Pilih masa aktif:**",
			["3", "7", "30", "60"],
		)
		await short_progress(event, "Membuat akun TROJAN...")
		cmd = f'printf "%s\n" "{user}" "{exp}" "{pw}" | addtr'
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond("❌ **Username sudah terdaftar.**")
		else:
			today = DT.date.today()
			later = today + DT.timedelta(days=int(exp))
			b = [x.group() for x in re.finditer("trojan://(.*)",a)]
			domain = re.search("@(.*?):",b[0]).group(1)
			uuid = re.search("trojan://(.*?)@",b[0]).group(1)
			msg = build_result(
				"TROJAN Account Created",
				[
					("Username", user),
					("Host", domain),
					("XRAY DNS", HOST),
					("Quota", f"{pw} GB"),
					("Password/UUID", uuid),
					("Expired", str(later)),
				],
				[
					("WS", b[0].replace(" ", "")),
					("gRPC", b[1].replace(" ", "")),
					("OpenClash", f"https://{domain}:81/trojan-{user}.txt"),
				],
			)
			await event.respond(msg)
			await send_tls_qr(event, b[0].replace(" ", ""), "QR TLS TROJAN")
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await create_trojan_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'cek-trojan'))
async def cek_trojan(event):
	async def cek_trojan_(event):
		cmd = 'bot-cek-tr'.strip()
		_, z = run_command(cmd)
		z = z or "Tidak ada sesi login TROJAN aktif."
		await event.respond(f"""

{z}

**Shows Logged In Users Trojan**
**» 🤖@AutoFTbot**
""",buttons=[[Button.inline("‹ Main Menu ›","menu")]])
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await cek_trojan_(event)
	else:
		await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'list-trojan'))
async def list_trojan(event):
	async def list_trojan_(event):
		cmd = "grep -E '^### ' /etc/trojan/.trojan.db 2>/dev/null | awk '{printf \"%-20s %s\\n\",$2,$3}'"
		_, out = run_command(cmd)
		if not out:
			out = "Tidak ada user TROJAN."
		await event.respond(f"📋 **Daftar User TROJAN**\n```\n{out}\n```")

	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await list_trojan_(event)
	else:
		await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'renew-trojan'))
async def renew_trojan(event):
	async def renew_trojan_(event):
		user = await ask_text(event, chat, sender.id, "👤 **Masukkan Username TROJAN:**")
		user = sanitize_username(user)
		if not user:
			await event.respond("❌ Username tidak valid. Gunakan huruf/angka/._-")
			return

		days = await ask_choice(event, chat, sender.id, "📅 **Tambah masa aktif (hari):**", ["1", "3", "7", "30", "60"])
		quota = await ask_text(event, chat, sender.id, "📦 **Quota baru (GB, kosong=0):**")
		quota = quota if quota else "0"
		iplim = await ask_text(event, chat, sender.id, "🌐 **Limit IP (kosong=1):**")
		iplim = iplim if iplim else "1"

		await short_progress(event, "Memperpanjang akun TROJAN...")
		_, out = run_command("renewtr", [user, days, quota, iplim])
		_, exp = run_command(f"grep -wE '^#! {user} ' /etc/xray/config.json | awk '{{print $3}}' | head -n1")
		if exp:
			msg = build_result(
				"TROJAN Account Renewed",
				[
					("Username", user),
					("Added Days", days),
					("Quota", f"{quota} GB"),
					("Limit IP", iplim),
					("Expired", exp),
				],
				[("OpenClash", f"https://{DOMAIN}:81/trojan-{user}.txt")],
			)
			await event.respond(msg)
		else:
			await event.respond(f"⚠️ Perpanjangan diproses, cek output:\n```\n{out or 'Tidak ada output'}\n```")

	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await renew_trojan_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'trial-trojan'))
async def trial_trojan(event):
	async def trial_trojan_(event):
		exp = await ask_choice(event, chat, sender.id, "⏱️ **Trial TROJAN (menit):**", ["10", "15", "30", "60"])
		cmd = f'printf "%s\n" "{exp}" | trialtr'
		await short_progress(event, "Membuat trial TROJAN...")
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond("❌ **Gagal membuat trial TROJAN.**")
		else:
			b = [x.group() for x in re.finditer("trojan://(.*)",a)]
			remarks = re.search("#(.*)",b[0]).group(1)
			domain = re.search("@(.*?):",b[0]).group(1)
			uuid = re.search("trojan://(.*?)@",b[0]).group(1)
			msg = build_result(
				"TROJAN Trial Created",
				[
					("Username", remarks),
					("Host", domain),
					("Password/UUID", uuid),
					("Mode", "Trial"),
					("Expired", f"{exp} menit"),
				],
				[
					("TLS/WS", b[0].replace(" ", "")),
					("gRPC", b[1].replace(" ", "")),
				],
			)
			await event.respond(msg)
			await send_tls_qr(event, b[0].replace(" ", ""), "QR TLS TROJAN Trial")
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await trial_trojan_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'delete-trojan'))
async def delete_trojan(event):
	async def delete_trojan_(event):
		async with bot.conversation(chat) as user:
			await event.respond('**Username:**')
			user = user.wait_event(events.NewMessage(incoming=True, from_users=sender.id))
			user = (await user).raw_text
		cmd = f'printf "%s\n" "{user}" | deltr'
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
		await delete_trojan_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'suspend-trojan'))
async def suspend_trojan(event):
	async def suspend_trojan_(event):
		async with bot.conversation(chat) as user:
			await event.respond('**Username:**')
			user = user.wait_event(events.NewMessage(incoming=True, from_users=sender.id))
			user = (await user).raw_text
		cmd = f'printf "%s\n" "{user}" | susptr'
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
		await suspend_trojan_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'unsuspend-trojan'))
async def unsuspend_trojan(event):
	async def unsuspend_trojan_(event):
		async with bot.conversation(chat) as user:
			await event.respond('**Username:**')
			user = user.wait_event(events.NewMessage(incoming=True, from_users=sender.id))
			user = (await user).raw_text
		cmd = f'printf "%s\n" "{user}" | unsusptr'
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
		await unsuspend_trojan_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'trojan'))
async def trojan(event):
	async def trojan_(event):
		inline = [
			[Button.inline("🧪 Trial", "trial-trojan"), Button.inline("➕ Create", "create-trojan")],
			[Button.inline("👀 Check Login", "cek-trojan"), Button.inline("📋 List User", "list-trojan")],
			[Button.inline("🗓️ Renew", "renew-trojan"), Button.inline("🗑️ Delete", "delete-trojan")],
			[Button.inline("⛔ Suspend", "suspend-trojan"), Button.inline("✅ Unsuspend", "unsuspend-trojan")],
			[Button.inline("⬅️ Main Menu", "menu")],
		]
		msg = manager_banner("TROJAN Manager", "TROJAN")
		await event.edit(msg,buttons=inline)
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await trojan_(event)
	else:
		await event.answer("Access Denied",alert=True)
