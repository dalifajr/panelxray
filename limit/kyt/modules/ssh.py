from kyt import *
from kyt.modules.ui import ask_choice, ask_text, build_result, manager_banner, short_progress, back_button

#DELETESSH
@bot.on(events.CallbackQuery(data=b'delete-ssh'))
async def delete_ssh(event):
	async def delete_ssh_(event):
		async with bot.conversation(chat) as user:
			await event.respond("**Username To Be Deleted:**")
			user = user.wait_event(events.NewMessage(incoming=True, from_users=sender.id))
			user = (await user).raw_text
			cmd = f'printf "%s\n" "{user}" | delssh'
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond(f"**User** `{user}` **Not Found**", buttons=back_button("ssh"))
		else:
			await event.respond(f"**Successfully Deleted** `{user}`", buttons=back_button("ssh"))
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await delete_ssh_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'create-ssh'))
async def create_ssh(event):
	async def create_ssh_(event):
		user = await ask_text(event, chat, sender.id, "👤 **Masukkan Username SSH:**")
		pw = await ask_text(event, chat, sender.id, "🔐 **Masukkan Password SSH:**")
		exp = await ask_choice(
			event,
			chat,
			sender.id,
			"📅 **Pilih masa aktif:**",
			["3", "7", "30", "60"],
		)
		await short_progress(event, "Membuat akun SSH...")
		cmd = f'useradd -e `date -d "{exp} days" +"%Y-%m-%d"` -s /bin/false -M {user} && echo "{pw}\n{pw}" | passwd {user}'
		try:
			subprocess.check_output(cmd,shell=True)
		except:
			await event.respond("❌ **Username sudah terdaftar.**")
		else:
			today = DT.date.today()
			later = today + DT.timedelta(days=int(exp))
			msg = build_result(
				"SSH Account Created",
				[
					("Username", user.strip()),
					("Password", pw.strip()),
					("Host", DOMAIN),
					("SlowDNS", HOST),
					("OpenSSH Port", "443,80,22"),
					("Dropbear Port", "443,109"),
					("Expired", str(later)),
				],
				[
					("Payload WSS", f"GET wss://BUG.COM/ HTTP/1.1[crlf]Host: {DOMAIN}[crlf]Upgrade: websocket[crlf][crlf]"),
					("OVPN WS SSL", f"https://{DOMAIN}:81/ws-ssl.ovpn"),
					("OVPN SSL", f"https://{DOMAIN}:81/ssl.ovpn"),
					("OVPN TCP", f"https://{DOMAIN}:81/tcp.ovpn"),
					("OVPN UDP", f"https://{DOMAIN}:81/udp.ovpn"),
					("Save Link", f"https://{DOMAIN}:81/ssh-{user.strip()}.txt"),
				],
			)
			await event.respond(msg)
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await create_ssh_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'show-ssh'))
async def show_ssh(event):
	async def show_ssh_(event):
		cmd = 'bot-member-ssh'.strip()
		x = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
		print(x)
		z = subprocess.check_output(cmd, shell=True).decode("utf-8")
		await event.respond(f"""
```
{z}
```
**Show All SSH User**
**» 🤖@AutoFTbot**
""",buttons=back_button("ssh"))
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await show_ssh_(event)
	else:
		await event.answer("Access Denied",alert=True)



@bot.on(events.CallbackQuery(data=b'trial-ssh'))
async def trial_ssh(event):
	async def trial_ssh_(event):
		async with bot.conversation(chat) as exp:
			await event.respond("**Choose Expiry Minutes**",buttons=[
[Button.inline(" 10 Menit ","10"),
Button.inline(" 15 Menit ","15")],
[Button.inline(" 30 Menit ","30"),
Button.inline(" 60 Menit ","60")]])
			exp = exp.wait_event(events.CallbackQuery)
			exp = (await exp).data.decode("ascii")
		user = "trialX"+str(random.randint(100,1000))
		pw = "1"
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
		cmd = f'useradd -e `date -d "{exp} days" +"%Y-%m-%d"` -s /bin/false -M {user} && echo "{pw}\n{pw}" | passwd {user} | tmux new-session -d -s {user} "trial trialssh {user} {exp}"'
		try:
			subprocess.check_output(cmd,shell=True)
		except:
			await event.respond("**User Already Exist**")
		else:
			#today = DT.date.today()
			#later = today + DT.timedelta(days=int(exp))
			msg = f"""
**━━━━━━━━━━━━━━━━━**
**🐾🕊️ SSH OVPN ACCOUNT 🕊️🐾**
**━━━━━━━━━━━━━━━━━**
**» Username         :** `{user.strip()}`
**» Password         :** `{pw.strip()}`
**━━━━━━━━━━━━━━━━━**
**» Host             :** `{DOMAIN}`
**» Host Slowdns     :** `{HOST}`
**» Pub Key          :** `{PUB}`
**» Port OpenSSH     :** `443, 80, 22`
**» Port DNS         :** `443, 53 ,22`
**» Port Dropbear    :** `443, 109`
**» Port Dropbear WS :** `443, 109`
**» Port SSH WS      :** `80, 8080, 8081-9999 `
**» Port SSH SSL WS  :** `443`
**» Port SSL/TLS     :** `222-1000`
**» Port OVPN WS SSL :** `443`
**» Port OVPN SSL    :** `443`
**» Port OVPN TCP    :** `443, 1194`
**» Port OVPN UDP    :** `2200`
**» Proxy Squid      :** `3128`
**» BadVPN UDP       :** `7100, 7300, 7300`
**━━━━━━━━━━━━━━━━━**
**» Payload WSS      :** `GET wss://BUG.COM/ HTTP/1.1[crlf]Host: {DOMAIN}[crlf]Upgrade: websocket[crlf][crlf]`
**━━━━━━━━━━━━━━━━━**
**» OpenVPN WS SSL   :** `https://{DOMAIN}:81/ws-ssl.ovpn`
**» OpenVPN SSL      :** `https://{DOMAIN}:81/ssl.ovpn`
**» OpenVPN TCP      :** `https://{DOMAIN}:81/tcp.ovpn`
**» OpenVPN UDP      :** `https://{DOMAIN}:81/udp.ovpn`
**━━━━━━━━━━━━━━━━━**
**» Save Link Account:** `https://{DOMAIN}:81/ssh-{user.strip()}.txt`
**» Expired Until:** `{exp} Minutes`
**» 🤖@AutoFTbot**
"""
			await event.respond(msg)
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await trial_ssh_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)
		
@bot.on(events.CallbackQuery(data=b'login-ssh'))
async def login_ssh(event):
	async def login_ssh_(event):
		cmd = 'bot-cek-login-ssh'.strip()
		x = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
		print(x)
		z = subprocess.check_output(cmd, shell=True).decode("utf-8")
		await event.respond(f"""

{z}

**shows logged in users SSH Ovpn**
**» 🤖@AutoFTbot**
""",buttons=back_button("ssh"))
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await login_ssh_(event)
	else:
		await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'ssh'))
async def ssh(event):
	async def ssh_(event):
		inline = [
			[Button.inline("🧪 Trial", "trial-ssh"), Button.inline("➕ Create", "create-ssh")],
			[Button.inline("👀 Check Login", "login-ssh"), Button.inline("📋 List User", "show-ssh")],
			[Button.inline("🗑️ Delete", "delete-ssh"), Button.inline("🧾 Regis IP", "regis")],
			[Button.inline("⬅️ Main Menu", "menu")],
		]
		msg = manager_banner("SSH/OVPN Manager", "SSH")
		await event.edit(msg,buttons=inline)
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await ssh_(event)
	else:
		await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'regis'))
async def regis_ip(event):
	async def regis_ip_(event):
		ip = await ask_text(event, chat, sender.id, "🌐 **Masukkan IP untuk registrasi akses SSH:**")
		cmd = f'printf "%s\n" "{ip}" | add-ip'
		try:
			out = subprocess.check_output(cmd, shell=True).decode("utf-8", errors="ignore").strip()
		except Exception:
			await event.respond("❌ Gagal registrasi IP.", buttons=back_button("ssh"))
		else:
			await event.respond(f"✅ Registrasi IP berhasil.\n`{out}`", buttons=back_button("ssh"))

	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await regis_ip_(event)
	else:
		await event.answer("Access Denied", alert=True)
