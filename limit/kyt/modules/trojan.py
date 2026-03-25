from kyt import *
from kyt.modules.ui import ask_choice, ask_text, build_result, manager_banner, short_progress

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
		x = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
		print(x)
		z = subprocess.check_output(cmd, shell=True).decode("utf-8")
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

@bot.on(events.CallbackQuery(data=b'trial-trojan'))
async def trial_trojan(event):
	async def trial_trojan_(event):
		async with bot.conversation(chat) as exp:
			await event.respond("**Choose Expiry Minutes**",buttons=[
[Button.inline(" 10 Menit ","10"),
Button.inline(" 15 Menit ","15")],
[Button.inline(" 30 Menit ","30"),
Button.inline(" 60 Menit ","60")]])
			exp = exp.wait_event(events.CallbackQuery)
			exp = (await exp).data.decode("ascii")
		cmd = f'printf "%s\n" "{exp}" | trialtr'
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
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond("**User Already Exist**")
		else:
			#today = DT.date.today()
			#later = today + DT.timedelta(days=int(exp))
			b = [x.group() for x in re.finditer("trojan://(.*)",a)]
			print(b)
			remarks = re.search("#(.*)",b[0]).group(1)
			domain = re.search("@(.*?):",b[0]).group(1)
			uuid = re.search("trojan://(.*?)@",b[0]).group(1)
			msg = f"""
**━━━━━━━━━━━━━━━━━**
**🐾🕊️ Xray/Trojan Account 🕊️🐾**
**━━━━━━━━━━━━━━━━━**
**» Remarks     :** `{remarks}`
**» Host Server :** `{domain}`
**» Host XrayDNS:** `{HOST}`
**» User Quota  :** `Unlimited`
**» Port DNS    :** `443, 53`
**» port TLS    :** `222-1000`
**» Path Trojan :** `(/multi path)/trojan-ws`
**» User ID     :** `{uuid}`
**» Pub Key     :** {PUB}
**━━━━━━━━━━━━━━━━**
**» Link WS    :** 
`{b[0].replace(" ","")}`
**━━━━━━━━━━━━━━━━**
**» Link GRPC  :** 
`{b[1].replace(" ","")}`
**━━━━━━━━━━━━━━━━**
**» Expired Until:** `{exp} Minutes`
**» 🤖@AutoFTbot**
"""
			await event.respond(msg)
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
			[Button.inline("👀 Check Login", "cek-trojan"), Button.inline("🗑️ Delete", "delete-trojan")],
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
