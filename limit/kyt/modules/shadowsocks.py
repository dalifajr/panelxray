from kyt import *
from kyt.modules.ui import ask_choice, ask_text, build_result, manager_banner, send_tls_qr, short_progress

@bot.on(events.CallbackQuery(data=b'create-shadowsocks'))
async def create_shadowsocks(event):
	async def create_shadowsocks_(event):
		user = await ask_text(event, chat, sender.id, "👤 **Masukkan Username Shadowsocks:**")
		pw = await ask_text(event, chat, sender.id, "📦 **Masukkan Quota (GB):**")
		exp = await ask_choice(
			event,
			chat,
			sender.id,
			"📅 **Pilih masa aktif:**",
			["3", "7", "30", "60"],
		)
		await short_progress(event, "Membuat akun Shadowsocks...")
		cmd = f'printf "%s\n" "{user}" "{exp}" "{pw}" | addss'
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond("❌ **Username sudah terdaftar.**")
		else:
			today = DT.date.today()
			later = today + DT.timedelta(days=int(exp))
			x = [x.group() for x in re.finditer("ss://(.*)",a)]
			uuid = re.search("ss://(.*?)@",x[0]).group(1)
			msg = build_result(
				"Shadowsocks Account Created",
				[
					("Username", user),
					("Host", DOMAIN),
					("XRAY DNS", HOST),
					("Quota", f"{pw} GB"),
					("Password", uuid),
					("Cipher", "aes-128-gcm"),
					("Expired", str(later)),
				],
				[
					("TLS", x[0]),
					("gRPC", x[1].replace(" ", "")),
					("JSON", f"https://{DOMAIN}:81/ss-{user}.txt"),
				],
			)
			await event.respond(msg)
			await send_tls_qr(event, x[0], "QR TLS SHADOWSOCKS")
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await create_shadowsocks_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'cek-shadowsocks'))
async def cek_shadowsocks(event):
	async def cek_shadowsocks_(event):
		cmd = 'bot-cek-ss'.strip()
		x = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
		print(x)
		z = subprocess.check_output(cmd, shell=True).decode("utf-8")
		await event.respond(f"""

{z}

**Shows Logged In Users Shadowsocks**
**» 🤖@AutoFTbot**
""",buttons=[[Button.inline("‹ Main Menu ›","menu")]])
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await cek_shadowsocks_(event)
	else:
		await event.answer("Access Denied",alert=True)

@bot.on(events.CallbackQuery(data=b'delete-shadowsocks'))
async def delete_shadowsocks(event):
	async def delete_shadowsocks_(event):
		async with bot.conversation(chat) as user:
			await event.respond('**Username:**')
			user = user.wait_event(events.NewMessage(incoming=True, from_users=sender.id))
			user = (await user).raw_text
		cmd = f'printf "%s\n" "{user}" | del-ss'
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
		await delete_shadowsocks_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'trial-shadowsocks'))
async def trial_shadowsocks(event):
	async def trial_shadowsocks_(event):
		exp = await ask_choice(event, chat, sender.id, "⏱️ **Trial SHADOWSOCKS (menit):**", ["10", "15", "30", "60"])
		await short_progress(event, "Membuat trial Shadowsocks...")
		cmd = f'printf "%s\n" "{exp}" | trialss'
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond("❌ **Gagal membuat trial SHADOWSOCKS.**")
		else:
			x = [x.group() for x in re.finditer("ss://(.*)",a)]
			remarks = re.search("#(.*)",x[0]).group(1)
			uuid = re.search("ss://(.*?)@",x[0]).group(1)
			msg = build_result(
				"Shadowsocks Trial Created",
				[
					("Username", remarks),
					("Host", DOMAIN),
					("Password", uuid),
					("Mode", "Trial"),
					("Expired", f"{exp} menit"),
				],
				[
					("TLS", x[0]),
					("gRPC", x[1].replace(" ", "")),
					("JSON", f"https://{DOMAIN}:81/ss-{remarks}.txt"),
				],
			)
			await event.respond(msg)
			await send_tls_qr(event, x[0], "QR TLS SHADOWSOCKS Trial")
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await trial_shadowsocks_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'shadowsocks'))
async def shadowsocks(event):
	async def shadowsocks_(event):
		inline = [
			[Button.inline("🧪 Trial", "trial-shadowsocks"), Button.inline("➕ Create", "create-shadowsocks")],
			[Button.inline("👀 Check Login", "cek-shadowsocks"), Button.inline("🗑️ Delete", "delete-shadowsocks")],
			[Button.inline("⬅️ Main Menu", "menu")],
		]
		msg = manager_banner("Shadowsocks Manager", "SHADOWSOCKS")
		await event.edit(msg,buttons=inline)
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await shadowsocks_(event)
	else:
		await event.answer("Access Denied",alert=True)
