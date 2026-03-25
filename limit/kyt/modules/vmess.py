from kyt import *
from kyt.modules.ui import ask_choice, ask_text, build_result, manager_banner, short_progress

#CRATE VMESS
@bot.on(events.CallbackQuery(data=b'create-vmess'))
async def create_vmess(event):
	async def create_vmess_(event):
		user = await ask_text(event, chat, sender.id, "👤 **Masukkan Username VMESS:**")
		pw = await ask_text(event, chat, sender.id, "📦 **Masukkan Quota (GB):**")
		exp = await ask_choice(
			event,
			chat,
			sender.id,
			"📅 **Pilih masa aktif:**",
			["3", "7", "30", "60"],
		)
		await short_progress(event, "Membuat akun VMESS...")
		cmd = f'printf "%s\n" "{user}" "{exp}" "{pw}" | addws'
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond("❌ **Username sudah terdaftar.**")
		else:
			today = DT.date.today()
			later = today + DT.timedelta(days=int(exp))
			b = [x.group() for x in re.finditer("vmess://(.*)",a)]
			z = base64.b64decode(b[0].replace("vmess://","")).decode("ascii")
			z = json.loads(z)
			msg = build_result(
				"VMESS Account Created",
				[
					("Username", z["ps"]),
					("Domain", z["add"]),
					("XRAY DNS", HOST),
					("Quota", f"{pw} GB"),
					("User ID", z["id"]),
					("Expired", str(later)),
				],
				[
					("TLS", b[0].strip("'").replace(" ", "")),
					("NTLS", b[1].strip("'").replace(" ", "")),
					("gRPC", b[2].strip("'")),
					("OpenClash", f"https://{DOMAIN}:81/vmess-{user}.txt"),
				],
			)
			await event.respond(msg)
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await create_vmess_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

# TRIAL VMESS
@bot.on(events.CallbackQuery(data=b'trial-vmess'))
async def trial_vmess(event):
	async def trial_vmess_(event):
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
		cmd = f'printf "%s\n" "{exp}" | trialws'
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond("**User Already Exist**")
		else:
			b = [x.group() for x in re.finditer("vmess://(.*)",a)]
			print(b)
			z = base64.b64decode(b[0].replace("vmess://","")).decode("ascii")
			z = json.loads(z)
			msg = f"""
**◇━━━━━━━━━━━━━━━━━◇**
**⟨ Xray/Vmess Account ⟩**
**◇━━━━━━━━━━━━━━━━━◇**
**» Domain       :** `{DOMAIN}`
**» port TLS     :** `443`
**» Port NTLS    :** `80`
**» Port GRPC    :** `443`
**» port TLS CDN :** `443`
**» Port NTLS CDN:** `80`
**» Port GRPC CDN:** `443`
**» OpenClash WS :** `443`
**» OpenClash NWS:** `80`
**» AlterId      :** `0`
**» Security     :** `auto`
**» NetWork      :** `(WS) or (gRPC)`
**» Path TLS     :** `/vmess`
**» Path NLS     :** `/vmess`
**» Path Dynamic :** `http://BUG.COM`
**» ServiceName  :** `vmess-grpc`
**◇━━━━━━━━━━━━━━━━━◇**
**» Link TLS     :** 
`{b[0].strip("'").replace(" ","")}`
**◇━━━━━━━━━━━━━━━━━◇**
**» Link NTLS    :** 
`{b[1].strip("'").replace(" ","")}`
**◇━━━━━━━━━━━━━━━━━◇**
**» Link GRPC    :** 
`{b[2].strip("'")}`
**◇━━━━━━━━━━━━━━━━━◇**
**» Format OpenClash :** https://{DOMAIN}:81/vmess-{z["ps"]}.txt
**◇━━━━━━━━━━━━━━━━━◇**
**» Expired Until:** ` {exp} Minutes`
**◇━━━━━━━━━━━━━━━━━◇**
"""
			await event.respond(msg)
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await trial_vmess_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

#CEK VMESS
@bot.on(events.CallbackQuery(data=b'cek-vmess'))
async def cek_vmess(event):
	async def cek_vmess_(event):
		cmd = 'bot-cek-ws'.strip()
		x = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
		print(x)
		z = subprocess.check_output(cmd, shell=True).decode("utf-8")
		await event.respond(f"""

{z}

**Shows Logged In Users Vmess**
**» 🤖@AutoFTbot**
""",buttons=[[Button.inline("‹ Main Menu ›","menu")]])
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await cek_vmess_(event)
	else:
		await event.answer("Access Denied",alert=True)

@bot.on(events.CallbackQuery(data=b'delete-vmess'))
async def delete_vmess(event):
	async def delete_vmess_(event):
		async with bot.conversation(chat) as user:
			await event.respond('**Username:**')
			user = user.wait_event(events.NewMessage(incoming=True, from_users=sender.id))
			user = (await user).raw_text
		cmd = f'printf "%s\n" "{user}" | delws'
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
		await delete_vmess_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'suspend-vmess'))
async def suspend_vmess(event):
	async def suspend_vmess_(event):
		async with bot.conversation(chat) as user:
			await event.respond('**Username:**')
			user = user.wait_event(events.NewMessage(incoming=True, from_users=sender.id))
			user = (await user).raw_text
		cmd = f'printf "%s\n" "{user}" | suspws'
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
		await suspend_vmess_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'unsuspend-vmess'))
async def unsuspend_vmess(event):
	async def unsuspend_vmess_(event):
		async with bot.conversation(chat) as user:
			await event.respond('**Username:**')
			user = user.wait_event(events.NewMessage(incoming=True, from_users=sender.id))
			user = (await user).raw_text
		cmd = f'printf "%s\n" "{user}" | unsuspws'
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
		await unsuspend_vmess_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'vmess'))
async def vmess(event):
	async def vmess_(event):
		inline = [
			[Button.inline("🧪 Trial", "trial-vmess"), Button.inline("➕ Create", "create-vmess")],
			[Button.inline("👀 Check Login", "cek-vmess"), Button.inline("🗑️ Delete", "delete-vmess")],
			[Button.inline("⛔ Suspend", "suspend-vmess"), Button.inline("✅ Unsuspend", "unsuspend-vmess")],
			[Button.inline("⬅️ Main Menu", "menu")],
		]
		msg = manager_banner("VMESS Manager", "VMESS")
		await event.edit(msg,buttons=inline)
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await vmess_(event)
	else:
		await event.answer("Access Denied",alert=True)