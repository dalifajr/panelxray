from kyt import *
from kyt.modules.ui import ask_choice, ask_text, build_result, manager_banner, short_progress

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
		x = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
		print(x)
		z = subprocess.check_output(cmd, shell=True).decode("utf-8")
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
		async with bot.conversation(chat) as exp:
			await event.respond("**Choose Expiry Minutes**",buttons=[
[Button.inline(" 10 Menit ","10"),
Button.inline(" 15 Menit ","15")],
[Button.inline(" 30 Menit ","30"),
Button.inline(" 60 Menit ","60")]])
			exp = exp.wait_event(events.CallbackQuery)
			exp = (await exp).data.decode("ascii")
		await event.edit("Processing.")
		await event.edit("Processing..")
		await event.edit("Processing...")
		await event.edit("Processing....")
		time.sleep(3)
		await event.edit("`Processing Crate Premium Account`")
		time.sleep(1)
		await event.edit("`Processing... 0%\n▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 4%\n█▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(2)
		await event.edit("`Processing... 8%\n██▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(3)
		await event.edit("`Processing... 20%\n█████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(2)
		await event.edit("`Processing... 36%\n█████████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 52%\n█████████████▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 84%\n█████████████████████▒▒▒▒ `")
		time.sleep(0)
		await event.edit("`Processing... 100%\n█████████████████████████ `")
		time.sleep(1)
		await event.edit("`Wait.. Setting up an Account`")
		cmd = f'printf "%s\n" "{exp}" | trialvless'
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond("**User Already Exist**")
		else:
			#today = DT.date.today()
			#later = today + DT.timedelta(days=int(exp))
			x = [x.group() for x in re.finditer("vless://(.*)",a)]
			print(x)
			remarks = re.search("#(.*)",x[0]).group(1)
			# domain = re.search("@(.*?):",x[0]).group(1)
			uuid = re.search("vless://(.*?)@",x[0]).group(1)
			# path = re.search("path=(.*)&",x[0]).group(1)
			msg = f"""
**━━━━━━━━━━━━━━━━━**
**🐾🕊️ Xray/Vless Account 🕊️🐾**
**━━━━━━━━━━━━━━━━━**
**» Remarks     :** `{remarks}`
**» Host Server :** `{DOMAIN}`
**» Host XrayDNS:** `{HOST}`
**» User Quota  :** `Unlimited`
**» Port DNS    :** `443, 53`
**» port TLS    :** `222-1000`
**» Port NTLS   :** `80, 8080, 8081-9999`
**» NetWork     :** `(WS) or (gRPC)`
**» User ID     :** `{uuid}`
**» Path Vless  :** `(/multi path)/vless `
**» Path Dynamic:** `http://BUG.COM/vless `
**» Pub Key     :** `{PUB}`
**━━━━━━━━━━━━━━━━━**
**» Link TLS   : **
`{x[0]}`
**━━━━━━━━━━━━━━━━━**
**» Link NTLS  :**
`{x[1].replace(" ","")}`
**━━━━━━━━━━━━━━━━━**
**» Link GRPC  :**
`{x[2].replace(" ","")}`
**━━━━━━━━━━━━━━━━━**
**» Expired Until :** `{exp} Minutes`
**» 🤖@AutoFTbot**
"""
			await event.respond(msg)
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
			[Button.inline("👀 Check Login", "cek-vless"), Button.inline("🗑️ Delete", "delete-vless")],
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
