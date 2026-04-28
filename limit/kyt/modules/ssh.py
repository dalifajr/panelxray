from kyt import *
import asyncio
from kyt.modules.ui import (
	ask_choice,
	ask_expiry,
	ask_text_clean,
	build_result,
	manager_banner,
	back_button,
	delete_messages,
	upsert_message,
	sanitize_username,
	notify_then_back,
	ensure_creation_quota,
	is_admin,
	run_command,
	ask_renew_account,
	show_account_browser,
)


def _progress_bar(percent: int, width: int = 24) -> str:
	clamped = max(0, min(100, int(percent)))
	filled = int((clamped * width) / 100)
	return "#" * filled + "-" * (width - filled)

#DELETESSH
@bot.on(events.CallbackQuery(data=b'delete-ssh'))
async def delete_ssh(event):
	async def delete_ssh_(event):
		await show_account_browser(event, "ssh", "delete")
		return
		msgs_to_del = []
		user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username SSH yang akan dihapus:**")
		msgs_to_del.extend(msgs)
		user = sanitize_username(user)

		if not user:
			await delete_messages(chat, msgs_to_del)
			await upsert_message(event, "❌ Username tidak valid.", buttons=back_button("ssh"))
			return

		if not is_admin(sender.id) and not user_owns_account(str(sender.id), "ssh", user, active_only=True):
			await delete_messages(chat, msgs_to_del)
			await upsert_message(event, "⛔ Anda hanya bisa menghapus akun SSH milik Anda sendiri.", buttons=back_button("ssh"))
			return

		await delete_messages(chat, msgs_to_del)
		cmd = f'printf "%s\\n" "{user}" | delssh'
		try:
			subprocess.check_output(cmd, shell=True).decode("utf-8")
		except Exception:
			await upsert_message(event, f"❌ User `{user}` tidak ditemukan.", buttons=back_button("ssh"))
		else:
			mark_account_inactive("ssh", user)
			await notify_then_back(event, f"✅ User `{user}` berhasil dihapus.", ssh, delay=2)
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await delete_ssh_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)


@bot.on(events.CallbackQuery(pattern=b"^renew-ssh(?::.+)?$"))
async def renew_ssh(event):
	async def renew_ssh_(event):
		if (event.data or b"") == b"renew-ssh":
			await show_account_browser(event, "ssh", "renew")
			return
		msgs_to_del = []
		user, msgs = await ask_renew_account(event, chat, sender.id, "ssh", "SSH", "ssh")
		msgs_to_del.extend(msgs)
		if not user and not msgs_to_del:
			return
		user = sanitize_username(user)

		if not user:
			await delete_messages(chat, msgs_to_del)
			await upsert_message(event, "❌ Username tidak valid.", buttons=back_button("ssh"))
			return

		if not is_admin(sender.id) and not user_owns_account(str(sender.id), "ssh", user, active_only=True):
			await delete_messages(chat, msgs_to_del)
			await upsert_message(event, "⛔ Anda hanya bisa renew akun SSH milik Anda sendiri.", buttons=back_button("ssh"))
			return

		days = await ask_choice(event, chat, sender.id, "📅 **Tambah masa aktif (hari):**", ["3", "7", "30", "60"])
		iplim, msgs = await ask_text_clean(event, chat, sender.id, "🌐 **Limit IP baru (kosong=1):**", [])
		msgs_to_del.extend(msgs)
		iplim = iplim if iplim else "1"
		if not str(iplim).isdigit():
			await delete_messages(chat, msgs_to_del)
			await upsert_message(event, "❌ Limit IP harus angka.", buttons=back_button("ssh"))
			return

		await delete_messages(chat, msgs_to_del)

		try:
			uid_text = subprocess.check_output(f'id -u "{user}"', shell=True).decode("utf-8").strip()
			uid_num = int(uid_text)
		except Exception:
			await upsert_message(event, f"❌ User `{user}` tidak ditemukan.", buttons=back_button("ssh"))
			return

		if uid_num < 1000:
			await upsert_message(event, "⛔ Akun sistem tidak bisa di-renew dari menu bot.", buttons=back_button("ssh"))
			return

		try:
			exp_raw = subprocess.check_output(
				f"chage -l \"{user}\" | awk -F\": \" '/Account expires/ {{print $2}}'",
				shell=True,
			).decode("utf-8").strip()
		except Exception:
			exp_raw = ""

		base_ts = int(time.time())
		if exp_raw and exp_raw.lower() != "never":
			try:
				base_ts = int(subprocess.check_output(f'date -d "{exp_raw}" +%s', shell=True).decode("utf-8").strip())
			except Exception:
				base_ts = int(time.time())

		target_ts = base_ts + (int(days) * 86400)
		new_exp = subprocess.check_output(f'date -u -d "@{target_ts}" +%Y-%m-%d', shell=True).decode("utf-8").strip()

		cmd = f'passwd -u "{user}" >/dev/null 2>&1 || true; usermod -e "{new_exp}" "{user}"'
		code = subprocess.call(cmd, shell=True)
		if code != 0:
			await upsert_message(event, "❌ Gagal renew akun SSH.", buttons=back_button("ssh"))
			return

		if int(iplim) > 0:
			subprocess.call(f'mkdir -p /etc/kyt/limit/ssh/ip; echo "{iplim}" > /etc/kyt/limit/ssh/ip/{user}', shell=True)
		else:
			subprocess.call(f'rm -f /etc/kyt/limit/ssh/ip/{user}', shell=True)

		refresh_account_expiry("ssh", user, new_exp)
		msg = build_result(
			"SSH Account Renewed",
			[
				("Username", user),
				("Added Days", days),
				("Limit IP", iplim),
				("Expired", new_exp),
			],
			[],
		)
		await upsert_message(event, msg, buttons=back_button("ssh"))

	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await renew_ssh_(event)
	else:
		await event.answer("Akses Ditolak", alert=True)


@bot.on(events.CallbackQuery(data=b'suspend-ssh'))
async def suspend_ssh(event):
	async def suspend_ssh_(event):
		await show_account_browser(event, "ssh", "suspend")
		return
		msgs_to_del = []
		user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username SSH yang akan disuspend:**")
		msgs_to_del.extend(msgs)
		user = sanitize_username(user)

		if not user:
			await delete_messages(chat, msgs_to_del)
			await upsert_message(event, "❌ Username tidak valid.", buttons=back_button("ssh"))
			return

		if not is_admin(sender.id) and not user_owns_account(str(sender.id), "ssh", user, active_only=True):
			await delete_messages(chat, msgs_to_del)
			await upsert_message(event, "⛔ Anda hanya bisa suspend akun SSH milik Anda sendiri.", buttons=back_button("ssh"))
			return

		await delete_messages(chat, msgs_to_del)
		code, out = run_command("suspssh", [user])
		if code != 0:
			await upsert_message(event, f"❌ Gagal suspend akun SSH.\n```\n{out or 'Tidak ada output'}\n```", buttons=back_button("ssh"))
		else:
			await upsert_message(event, f"⛔ {(out or 'Akun SSH berhasil disuspend').strip()}", buttons=back_button("ssh"))

	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await suspend_ssh_(event)
	else:
		await event.answer("Akses Ditolak", alert=True)


@bot.on(events.CallbackQuery(data=b'unsuspend-ssh'))
async def unsuspend_ssh(event):
	async def unsuspend_ssh_(event):
		await show_account_browser(event, "ssh", "unsuspend")
		return
		msgs_to_del = []
		user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Username SSH yang akan di-unsuspend:**")
		msgs_to_del.extend(msgs)
		user = sanitize_username(user)

		if not user:
			await delete_messages(chat, msgs_to_del)
			await upsert_message(event, "❌ Username tidak valid.", buttons=back_button("ssh"))
			return

		if not is_admin(sender.id) and not user_owns_account(str(sender.id), "ssh", user, active_only=True):
			await delete_messages(chat, msgs_to_del)
			await upsert_message(event, "⛔ Anda hanya bisa unsuspend akun SSH milik Anda sendiri.", buttons=back_button("ssh"))
			return

		await delete_messages(chat, msgs_to_del)
		code, out = run_command("unsuspssh", [user])
		if code != 0:
			await upsert_message(event, f"❌ Gagal unsuspend akun SSH.\n```\n{out or 'Tidak ada output'}\n```", buttons=back_button("ssh"))
		else:
			await upsert_message(event, f"✅ {(out or 'Akun SSH berhasil di-unsuspend').strip()}", buttons=back_button("ssh"))

	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await unsuspend_ssh_(event)
	else:
		await event.answer("Akses Ditolak", alert=True)

@bot.on(events.CallbackQuery(data=b'create-ssh'))
async def create_ssh(event):
	async def create_ssh_(event):
		if not await ensure_creation_quota(event, str(sender.id), "ssh"):
			return

		msgs_to_del = []
		user, msgs = await ask_text_clean(event, chat, sender.id, "👤 **Masukkan Username SSH:**")
		msgs_to_del.extend(msgs)
		user = sanitize_username(user)
		if not user:
			await delete_messages(chat, msgs_to_del)
			await upsert_message(event, "❌ Username tidak valid. Gunakan huruf/angka/._-", buttons=back_button("ssh"))
			return

		pw, msgs = await ask_text_clean(event, chat, sender.id, "🔐 **Masukkan Password SSH:**", msgs_to_del)
		msgs_to_del.extend(msgs)
		if not pw:
			await delete_messages(chat, msgs_to_del)
			await upsert_message(event, "❌ Password tidak boleh kosong.", buttons=back_button("ssh"))
			return

		iplim, msgs = await ask_text_clean(event, chat, sender.id, "🌐 **Limit IP (kosong=1):**", [])
		msgs_to_del.extend(msgs)
		iplim = iplim if iplim else "1"
		if not str(iplim).isdigit():
			await delete_messages(chat, msgs_to_del)
			await upsert_message(event, "❌ Limit IP harus angka.", buttons=back_button("ssh"))
			return

		exp, msgs = await ask_expiry(event, chat, sender.id, is_trial=False)
		msgs_to_del.extend(msgs)
		if not exp:
			await delete_messages(chat, msgs_to_del)
			await upsert_message(event, "❌ Proses dibatalkan.", buttons=back_button("ssh"))
			return

		await delete_messages(chat, msgs_to_del)
		await upsert_message(event, "⏳ Membuat akun SSH...")

		try:
			days = max(1, int(exp))
		except Exception:
			days = 7

		today = DT.date.today()
		later = today + DT.timedelta(days=days)

		try:
			subprocess.run(
				["useradd", "-e", str(later), "-s", "/bin/false", "-M", user],
				check=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT,
				text=True,
			)
			subprocess.run(
				["chpasswd"],
				input=f"{user}:{pw}\n",
				check=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT,
				text=True,
			)
		except subprocess.CalledProcessError as exc:
			out = (exc.stdout or "").strip()
			await upsert_message(
				event,
				f"❌ Gagal create akun SSH.\n```\n{out or 'Username sudah terdaftar atau input tidak valid.'}\n```",
				buttons=back_button("ssh"),
			)
			return

		register_account_creation(str(sender.id), "ssh", user, str(later), is_trial=False)
		if int(iplim) > 0:
			subprocess.call(f'mkdir -p /etc/kyt/limit/ssh/ip; echo "{iplim}" > /etc/kyt/limit/ssh/ip/{user}', shell=True)
		else:
			subprocess.call(f'rm -f /etc/kyt/limit/ssh/ip/{user}', shell=True)

		msg = build_result(
			"SSH Account Created",
			[
				("Username", user),
				("Password", pw),
				("Limit IP", iplim),
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
				("Save Link", f"https://{DOMAIN}:81/ssh-{user}.txt"),
			],
		)
		msg += "\n\n🏠 Ketik /menu untuk kembali ke menu utama."
		await upsert_message(event, msg, buttons=back_button("ssh"))
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
		await show_account_browser(event, "ssh", "list")
		return
		if is_admin(sender.id):
			_, out = run_command("bot-member-ssh")
			if not out:
				out = "Tidak ada user SSH."
			await upsert_message(
				event,
				f"📋 **Daftar User SSH**\n```\n{out}\n```",
				buttons=back_button("ssh"),
			)
			return

		accounts = get_user_accounts(str(sender.id), category="ssh", active_only=True, limit=120)
		if not accounts:
			await upsert_message(event, "📭 Anda belum memiliki akun SSH yang tercatat.", buttons=back_button("ssh"))
			return

		lines = ["📋 **List Akun SSH Anda**", ""]
		for idx, account in enumerate(accounts, start=1):
			expires = str(account.get("expires_at") or "-")
			trial = " (TRIAL)" if int(account.get("is_trial", 0) or 0) == 1 else ""
			lines.append(f"{idx}. `{account.get('username', '-')}`{trial} - expired `{expires}`")

		text = "\n".join(lines)
		if len(text) > 3900:
			text = text[:3800] + "\n\n..."
		await upsert_message(event, text, buttons=back_button("ssh"))
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await show_ssh_(event)
	else:
		await event.answer("Access Denied",alert=True)



@bot.on(events.CallbackQuery(data=b'trial-ssh'))
async def trial_ssh(event):
	async def trial_ssh_(event):
		if not await ensure_creation_quota(event, str(sender.id), "ssh"):
			return

		msgs_to_del = []
		exp, msgs = await ask_expiry(event, chat, sender.id, is_trial=True)
		msgs_to_del.extend(msgs)
		if not exp:
			await delete_messages(chat, msgs_to_del)
			await upsert_message(event, "❌ Proses dibatalkan.", buttons=back_button("ssh"))
			return

		await delete_messages(chat, msgs_to_del)
		user = "trialX" + str(random.randint(1000, 9999))
		pw = "1"

		for percent, label in [
			(10, "Menyiapkan trial SSH..."),
			(35, "Menjalankan provisioning..."),
			(65, "Menyimpan konfigurasi..."),
			(90, "Finalisasi akun..."),
		]:
			await upsert_message(event, f"⏳ {label}\n`[{_progress_bar(percent)}] {percent}%`")
			await asyncio.sleep(0.35)

		cmd = f'useradd -e `date -d "{exp} days" +"%Y-%m-%d"` -s /bin/false -M {user} && echo "{pw}\n{pw}" | passwd {user} | tmux new-session -d -s {user} "trial trialssh {user} {exp}"'
		code, out = run_command(cmd)
		if code != 0:
			await upsert_message(
				event,
				f"❌ Gagal membuat trial SSH.\n```\n{out or 'Tidak ada output'}\n```",
				buttons=back_button("ssh"),
			)
			return

		register_account_creation(str(sender.id), "ssh", user, f"{exp} Minutes", is_trial=True)
		msg = build_result(
			"SSH Trial Created",
			[
				("Username", user),
				("Password", pw),
				("Host", DOMAIN),
				("SlowDNS", HOST),
				("Mode", "Trial"),
				("Expired", f"{exp} Minutes"),
			],
			[
				("Payload WSS", f"GET wss://BUG.COM/ HTTP/1.1[crlf]Host: {DOMAIN}[crlf]Upgrade: websocket[crlf][crlf]"),
				("OVPN WS SSL", f"https://{DOMAIN}:81/ws-ssl.ovpn"),
				("OVPN SSL", f"https://{DOMAIN}:81/ssl.ovpn"),
				("OVPN TCP", f"https://{DOMAIN}:81/tcp.ovpn"),
				("OVPN UDP", f"https://{DOMAIN}:81/udp.ovpn"),
				("Save Link", f"https://{DOMAIN}:81/ssh-{user}.txt"),
			],
		)
		msg += "\n\n🏠 Ketik /menu untuk kembali ke menu utama."
		await upsert_message(event, msg, buttons=back_button("ssh"))
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
		_, z = run_command("bot-cek-login-ssh")
		z = z or "Tidak ada sesi login SSH aktif."
		await upsert_message(
			event,
			f"📋 **SSH • Check Login**\n\n{z}",
			buttons=back_button("ssh"),
		)
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await login_ssh_(event)
	else:
		await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'ssh'))
async def ssh(event):
	async def ssh_(event):
		if is_admin(sender.id):
			inline = [
				[Button.inline("🧪 Trial", "trial-ssh"), Button.inline("➕ Create", "create-ssh")],
				[Button.inline("👀 Check Login", "login-ssh"), Button.inline("📋 List User", "show-ssh")],
				[Button.inline("🗓️ Renew", "renew-ssh"), Button.inline("🗑️ Delete", "delete-ssh")],
				[Button.inline("⛔ Suspend", "suspend-ssh"), Button.inline("✅ Unsuspend", "unsuspend-ssh")],
				[Button.inline("⬅️ Main Menu", "menu")],
			]
		else:
			inline = [
				[Button.inline("🧪 Trial", "trial-ssh"), Button.inline("➕ Create", "create-ssh")],
				[Button.inline("📋 Akun Saya", "show-ssh")],
				[Button.inline("🗓️ Renew", "renew-ssh"), Button.inline("🗑️ Delete", "delete-ssh")],
				[Button.inline("⛔ Suspend", "suspend-ssh"), Button.inline("✅ Unsuspend", "unsuspend-ssh")],
				[Button.inline("📨 Request Kuota", "quota-request")],
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
async def regis_ip_deprecated(event):
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await upsert_message(event, "ℹ️ Menu Regis IP sudah dihapus dari submenu SSH.", buttons=back_button("ssh"))
	else:
		await event.answer("Access Denied", alert=True)
