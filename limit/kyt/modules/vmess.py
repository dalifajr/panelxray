from kyt import *
from kyt.modules.ui import ask_choice, ask_text, build_result, manager_banner, run_command, sanitize_username, send_tls_qr, short_progress

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
		sni_profile = await ask_choice(
			event,
			chat,
			sender.id,
			"🌐 **Pilih profil SNI:**\n1) support.zoom.us\n2) live.iflix.com\n3) Tanpa konfigurasi",
			["1", "2", "3"],
		)
		cfg_mode = await ask_choice(
			event,
			chat,
			sender.id,
			"⚙️ **Pilih konfigurasi yang ditampilkan:**",
			["TLS", "NTLS", "GRPC", "ALL"],
		)
		iplimit = await ask_text(event, chat, sender.id, "🌐 **Limit IP (kosong=1):**")
		iplimit = iplimit if iplimit else "1"
		await short_progress(event, "Membuat akun VMESS...")
		code, a = run_command("addws", [sni_profile, user, exp, pw, iplimit])
		if code != 0:
			await event.respond("❌ **Username sudah terdaftar.**")
		else:
			today = DT.date.today()
			later = today + DT.timedelta(days=int(exp))
			b = [x.group() for x in re.finditer("vmess://(.*)",a)]
			if len(b) < 3:
				await event.respond("❌ **Gagal membaca link VMESS dari panel.**")
				return
			z = base64.b64decode(b[0].replace("vmess://","")).decode("ascii")
			z = json.loads(z)
			links = {
				"TLS": b[0].strip("'").replace(" ", ""),
				"NTLS": b[1].strip("'").replace(" ", ""),
				"GRPC": b[2].strip("'"),
			}
			selected_links = []
			if cfg_mode == "ALL":
				selected_links = [("TLS", links["TLS"]), ("NTLS", links["NTLS"]), ("gRPC", links["GRPC"])]
			elif cfg_mode == "GRPC":
				selected_links = [("gRPC", links["GRPC"])]
			else:
				selected_links = [(cfg_mode, links[cfg_mode])]
			msg = build_result(
				"VMESS Account Created",
				[
					("Username", z["ps"]),
					("Domain", z["add"]),
					("XRAY DNS", HOST),
					("Quota", f"{pw} GB"),
					("Limit IP", iplimit),
					("Config", cfg_mode),
					("User ID", z["id"]),
					("Expired", str(later)),
				],
				selected_links + [("OpenClash", f"https://{DOMAIN}:81/vmess-{user}.txt")],
			)
			await event.respond(msg)
			if cfg_mode in ("TLS", "ALL"):
				await send_tls_qr(event, links["TLS"], "QR TLS VMESS")
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
		exp = await ask_choice(event, chat, sender.id, "⏱️ **Trial VMESS (menit):**", ["10", "15", "30", "60"])
		cfg_mode = await ask_choice(
			event,
			chat,
			sender.id,
			"⚙️ **Pilih konfigurasi trial yang ditampilkan:**",
			["TLS", "NTLS", "GRPC", "ALL"],
		)
		await short_progress(event, "Membuat trial VMESS...")
		code, a = run_command("trialws", [cfg_mode, exp])
		if code != 0:
			await event.respond("❌ **Gagal membuat trial VMESS.**")
		else:
			b = [x.group() for x in re.finditer("vmess://(.*)",a)]
			if len(b) < 3:
				await event.respond("❌ **Gagal membaca link trial VMESS dari panel.**")
				return
			z = base64.b64decode(b[0].replace("vmess://","")).decode("ascii")
			z = json.loads(z)
			links = {
				"TLS": b[0].strip("'").replace(" ", ""),
				"NTLS": b[1].strip("'").replace(" ", ""),
				"GRPC": b[2].strip("'"),
			}
			selected_links = []
			if cfg_mode == "ALL":
				selected_links = [("TLS", links["TLS"]), ("NTLS", links["NTLS"]), ("gRPC", links["GRPC"])]
			elif cfg_mode == "GRPC":
				selected_links = [("gRPC", links["GRPC"])]
			else:
				selected_links = [(cfg_mode, links[cfg_mode])]
			msg = build_result(
				"VMESS Trial Created",
				[
					("Username", z["ps"]),
					("Domain", DOMAIN),
					("Mode", "Trial"),
					("Config", cfg_mode),
					("Expired", f"{exp} menit"),
				],
				selected_links + [("OpenClash", f"https://{DOMAIN}:81/vmess-{z['ps']}.txt")],
			)
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
		_, z = run_command(cmd)
		z = z or "Tidak ada sesi login VMESS aktif."
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


@bot.on(events.CallbackQuery(data=b'list-vmess'))
async def list_vmess(event):
	async def list_vmess_(event):
		cmd = "grep -E '^### ' /etc/vmess/.vmess.db 2>/dev/null | awk '{printf \"%-20s %s\\n\",$2,$3}'"
		_, out = run_command(cmd)
		if not out:
			out = "Tidak ada user VMESS."
		await event.respond(f"📋 **Daftar User VMESS**\n```\n{out}\n```")

	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await list_vmess_(event)
	else:
		await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'renew-vmess'))
async def renew_vmess(event):
	async def renew_vmess_(event):
		user = await ask_text(event, chat, sender.id, "👤 **Masukkan Username VMESS:**")
		user = sanitize_username(user)
		if not user:
			await event.respond("❌ Username tidak valid. Gunakan huruf/angka/._-")
			return

		days = await ask_choice(event, chat, sender.id, "📅 **Tambah masa aktif (hari):**", ["1", "3", "7", "30", "60"])
		quota = await ask_text(event, chat, sender.id, "📦 **Quota baru (GB, kosong=0):**")
		quota = quota if quota else "0"
		iplim = await ask_text(event, chat, sender.id, "🌐 **Limit IP (kosong=1):**")
		iplim = iplim if iplim else "1"

		await short_progress(event, "Memperpanjang akun VMESS...")
		_, out = run_command("renewws", [user, days, quota, iplim])
		_, exp = run_command(f"grep -wE '^### {user} ' /etc/xray/config.json | awk '{{print $3}}' | head -n1")
		if exp:
			msg = build_result(
				"VMESS Account Renewed",
				[
					("Username", user),
					("Added Days", days),
					("Quota", f"{quota} GB"),
					("Limit IP", iplim),
					("Expired", exp),
				],
				[("OpenClash", f"https://{DOMAIN}:81/vmess-{user}.txt")],
			)
			await event.respond(msg)
		else:
			await event.respond(f"⚠️ Perpanjangan diproses, cek output:\n```\n{out or 'Tidak ada output'}\n```")

	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await renew_vmess_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

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
			[Button.inline("👀 Check Login", "cek-vmess"), Button.inline("📋 List User", "list-vmess")],
			[Button.inline("🗓️ Renew", "renew-vmess"), Button.inline("🗑️ Delete", "delete-vmess")],
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