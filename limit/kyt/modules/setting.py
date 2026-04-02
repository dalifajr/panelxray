from kyt import *
import asyncio
import shutil
from kyt.modules.ui import manager_banner, back_button, upsert_message, is_admin, ask_text_clean, delete_messages


def _progress_bar(percent: int, width: int = 24) -> str:
	clamped = max(0, min(100, int(percent)))
	filled = int((clamped * width) / 100)
	return "#" * filled + "-" * (width - filled)


def _clean_log_line(line: str) -> str:
	if not line:
		return ""
	# Strip ANSI color/control sequences from shell updater output.
	return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line).strip()


def _resolve_update_command() -> str:
	candidates = [
		"/usr/local/sbin/cek-update",
		"/usr/local/sbin/update.sh",
	]
	for path in candidates:
		if os.path.isfile(path) and os.access(path, os.X_OK):
			return path

	repo_update = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "update.sh"))
	if os.path.isfile(repo_update):
		return f'bash "{repo_update}"'

	return "cek-update"


def _render_update_panel(percent: int, status: str, logs: list) -> str:
	if logs:
		log_text = "\n".join(logs[-10:])
	else:
		log_text = "(menunggu output updater...)"
	if len(log_text) > 1500:
		log_text = "...\n" + log_text[-1450:]

	bar = _progress_bar(percent)
	return (
		"🔄 **Panel Update (GitHub)**\n"
		f"`[{bar}] {percent}%`\n"
		f"Status: {status}\n\n"
		"📜 **Log Updater (terbaru):**\n"
		f"```\n{log_text}\n```"
	)


def _read_last_sshd_value(key: str, fallback: str) -> str:
	config_path = "/etc/ssh/sshd_config"
	if not os.path.isfile(config_path):
		return "(sshd_config tidak ditemukan)"

	pattern = re.compile(rf"^\s*{re.escape(key)}\s+(.+)$", re.IGNORECASE)
	value = ""
	try:
		with open(config_path, "r", encoding="utf-8", errors="ignore") as handle:
			for raw in handle:
				line = raw.strip()
				if not line or line.startswith("#"):
					continue
				match = pattern.match(line)
				if match:
					value = match.group(1).split("#", 1)[0].strip()
	except Exception:
		return fallback

	return value or fallback


def _ensure_sshd_key(lines: list, key: str, value: str) -> list:
	pattern = re.compile(rf"^\s*#?\s*{re.escape(key)}\b", re.IGNORECASE)
	updated = []
	replaced = False

	for raw in lines:
		if pattern.match(raw):
			if not replaced:
				updated.append(f"{key} {value}\n")
				replaced = True
			continue
		updated.append(raw)

	if not replaced:
		if updated and updated[-1].strip():
			updated.append("\n")
		updated.append(f"{key} {value}\n")

	return updated


def _validate_sshd_config(config_path: str = "/etc/ssh/sshd_config") -> tuple:
	candidates = [
		["sshd", "-t", "-f", config_path],
		["/usr/sbin/sshd", "-t", "-f", config_path],
	]

	for cmd in candidates:
		exe = cmd[0]
		if exe.startswith("/"):
			if not os.path.isfile(exe):
				continue
		elif shutil.which(exe) is None:
			continue

		proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
		if proc.returncode == 0:
			return True, "ok"
		return False, (proc.stdout or "").strip() or f"exit {proc.returncode}"

	return False, "Perintah sshd tidak ditemukan untuk validasi konfigurasi."


def _restart_ssh_service() -> tuple:
	commands = [
		["systemctl", "restart", "ssh"],
		["systemctl", "restart", "sshd"],
		["service", "ssh", "restart"],
		["service", "sshd", "restart"],
	]
	errors = []

	for cmd in commands:
		exe = cmd[0]
		if shutil.which(exe) is None:
			continue

		proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
		if proc.returncode == 0:
			return True, " ".join(cmd)
		err = (proc.stdout or "").strip() or f"exit {proc.returncode}"
		errors.append(f"{' '.join(cmd)} => {err}")

	if not errors:
		return False, "Perintah restart SSH tidak ditemukan."
	return False, errors[-1]


def _set_root_password(new_password: str) -> tuple:
	if not new_password:
		return False, "Password kosong"
	if shutil.which("chpasswd") is None:
		return False, "Perintah chpasswd tidak tersedia"

	proc = subprocess.run(
		["chpasswd"],
		input=f"root:{new_password}\n",
		text=True,
		stdout=subprocess.PIPE,
		stderr=subprocess.STDOUT,
	)
	if proc.returncode != 0:
		return False, (proc.stdout or "").strip() or f"exit {proc.returncode}"
	return True, "ok"


def _enable_password_root_login() -> tuple:
	config_path = "/etc/ssh/sshd_config"
	if not os.path.isfile(config_path):
		return False, "File sshd_config tidak ditemukan."

	try:
		with open(config_path, "r", encoding="utf-8", errors="ignore") as handle:
			original = handle.readlines()
	except Exception as exc:
		return False, f"Gagal membaca sshd_config: {exc}"

	updated = _ensure_sshd_key(original, "PasswordAuthentication", "yes")
	updated = _ensure_sshd_key(updated, "PermitRootLogin", "yes")
	changed = updated != original
	backup_path = ""

	if changed:
		backup_path = f"{config_path}.bak.bot.{int(time.time())}"
		try:
			with open(backup_path, "w", encoding="utf-8") as backup:
				backup.writelines(original)
			with open(config_path, "w", encoding="utf-8") as handle:
				handle.writelines(updated)
		except Exception as exc:
			return False, f"Gagal menyimpan sshd_config: {exc}"

	valid, valid_msg = _validate_sshd_config(config_path)
	if not valid:
		if changed:
			try:
				with open(config_path, "w", encoding="utf-8") as handle:
					handle.writelines(original)
			except Exception:
				pass
		return False, f"Validasi sshd gagal: {valid_msg}"

	restarted, restart_msg = _restart_ssh_service()
	if not restarted:
		return False, f"Config tersimpan tetapi restart SSH gagal: {restart_msg}"

	if changed and backup_path:
		return True, f"SSH auth diperbarui (backup: {backup_path})"
	return True, "SSH auth sudah sesuai"


def _render_ssh_auth_status() -> str:
	password_auth = _read_last_sshd_value("PasswordAuthentication", "(default distro)")
	permit_root = _read_last_sshd_value("PermitRootLogin", "(default distro)")

	ok = str(password_auth).lower().startswith("yes") and str(permit_root).lower().startswith("yes")
	state = "✅ Aktif penuh" if ok else "⚠️ Belum aktif penuh"

	auto_reboot_daily = "ON" if os.path.isfile("/etc/cron.d/daily_reboot") else "OFF"
	auto_reboot_legacy = "ON" if os.path.isfile("/etc/cron.d/reboot_otomatis") else "OFF"

	return (
		"🔐 **Status Login SSH Password**\n"
		f"• PasswordAuthentication: `{password_auth}`\n"
		f"• PermitRootLogin: `{permit_root}`\n"
		f"• Effective status: {state}\n\n"
		"🧭 **Status Scheduler Reboot (lockout check):**\n"
		f"• /etc/cron.d/daily_reboot: `{auto_reboot_daily}`\n"
		f"• /etc/cron.d/reboot_otomatis: `{auto_reboot_legacy}`"
	)

@bot.on(events.CallbackQuery(data=b'reboot'))
async def rebooot(event):
	async def rebooot_(event):
		cmd = f'reboot'
		await event.edit("Processing.")
		await event.edit("Processing..")
		await event.edit("Processing...")
		await event.edit("Processing....")
		time.sleep(1)
		await event.edit("`Processing Restart Service Server...`")
		time.sleep(1)
		await event.edit("`Processing... 0%\n▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 4%\n█▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 8%\n██▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 20%\n█████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 36%\n█████████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 52%\n█████████████▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 84%\n█████████████████████▒▒▒▒ `")
		time.sleep(0)
		await event.edit("`Processing... 100%\n█████████████████████████ `")
		subprocess.check_output(cmd, shell=True)
		await event.edit(f"""
**» REBOOT SERVER**
**» 🤖@AutoFTbot**
""",buttons=back_button("setting"))
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await rebooot_(event)
	else:
		await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'resx'))
async def resx(event):
	async def resx_(event):
		cmd = f'systemctl restart xray | systemctl restart nginx | systemctl restart haproxy | systemctl restart server | systemctl restart client'
		subprocess.check_output(cmd, shell=True)
		await event.edit("Processing.")
		await event.edit("Processing..")
		await event.edit("Processing...")
		await event.edit("Processing....")
		time.sleep(1)
		await event.edit("`Processing Restart Service Server...`")
		time.sleep(1)
		await event.edit("`Processing... 0%\n▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 4%\n█▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 8%\n██▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 20%\n█████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 36%\n█████████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 52%\n█████████████▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 84%\n█████████████████████▒▒▒▒ `")
		time.sleep(1)
		await event.edit(f"""
```Processing... 100%\n█████████████████████████ ```
**» Restarting Service Done**
**» 🤖@AutoFTbot**
""",buttons=back_button("setting"))
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await resx_(event)
	else:
		await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'panel-update'))
async def panel_update(event):
	async def panel_update_(event):
		if not is_admin(sender.id):
			await event.answer("Menu khusus admin", alert=True)
			return

		cmd = _resolve_update_command()
		logs = [f"$ {cmd}"]
		percent = 5
		await upsert_message(event, _render_update_panel(percent, "Menyiapkan updater...", logs), buttons=back_button("setting"))

		try:
			env = os.environ.copy()
			if not env.get("TERM"):
				env["TERM"] = "dumb"
			env.setdefault("COLUMNS", "120")
			env.setdefault("LINES", "40")
			env.setdefault("DEBIAN_FRONTEND", "noninteractive")
			proc = await asyncio.create_subprocess_shell(
				cmd,
				stdout=asyncio.subprocess.PIPE,
				stderr=asyncio.subprocess.STDOUT,
				env=env,
			)
		except Exception as exc:
			await upsert_message(
				event,
				_render_update_panel(100, f"Gagal menjalankan updater: {exc}", logs),
				buttons=back_button("setting"),
			)
			return

		last_edit = time.monotonic()
		while True:
			line = await proc.stdout.readline()
			if not line:
				break
			clean = _clean_log_line(line.decode("utf-8", errors="ignore"))
			if clean:
				logs.append(clean)
				logs = logs[-20:]
				percent = min(95, percent + 2)

			now = time.monotonic()
			if now - last_edit >= 1.0:
				await upsert_message(event, _render_update_panel(percent, "Updater sedang berjalan...", logs), buttons=back_button("setting"))
				last_edit = now

		rc = await proc.wait()
		if rc == 0:
			status = "Selesai. Perubahan berhasil diterapkan."
		else:
			status = f"Updater selesai dengan error (exit {rc})."
		await upsert_message(event, _render_update_panel(100, status, logs), buttons=back_button("setting"))

	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await panel_update_(event)
	else:
		await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'ssh-auth-status'))
async def ssh_auth_status(event):
	async def ssh_auth_status_(event):
		if not is_admin(sender.id):
			await event.answer("Menu khusus admin", alert=True)
			return
		await upsert_message(event, _render_ssh_auth_status(), buttons=back_button("setting"))

	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await ssh_auth_status_(event)
	else:
		await event.answer("Access Denied", alert=True)


@bot.on(events.CallbackQuery(data=b'root-passwd'))
async def root_password(event):
	async def root_password_(event):
		if not is_admin(sender.id):
			await event.answer("Menu khusus admin", alert=True)
			return

		chat = event.chat_id
		password, msgs = await ask_text_clean(
			event,
			chat,
			sender.id,
			"🔐 **Masukkan password root baru** (minimal 8 karakter):",
			[],
		)
		confirm, msgs = await ask_text_clean(
			event,
			chat,
			sender.id,
			"🔁 **Konfirmasi password root baru:**",
			msgs,
		)
		await delete_messages(chat, msgs)

		if not password or not confirm:
			await upsert_message(event, "❌ Password kosong. Proses dibatalkan.", buttons=back_button("setting"))
			return
		if len(password) < 8:
			await upsert_message(event, "❌ Password minimal 8 karakter.", buttons=back_button("setting"))
			return
		if password != confirm:
			await upsert_message(event, "❌ Konfirmasi password tidak cocok.", buttons=back_button("setting"))
			return

		await upsert_message(event, "⏳ Mengatur password root dan konfigurasi SSH password login...")

		ok_pw, pw_msg = _set_root_password(password)
		password = ""
		confirm = ""
		if not ok_pw:
			await upsert_message(event, f"❌ Gagal set password root.\n```\n{pw_msg}\n```", buttons=back_button("setting"))
			return

		ok_ssh, ssh_msg = _enable_password_root_login()
		status_panel = _render_ssh_auth_status()
		if not ok_ssh:
			await upsert_message(
				event,
				"⚠️ Password root berhasil diubah, tetapi pengaturan login SSH belum aktif penuh.\n\n"
				f"{status_panel}\n\n"
				f"Detail:\n```\n{ssh_msg}\n```",
				buttons=back_button("setting"),
			)
			return

		await upsert_message(
			event,
			"✅ Password root berhasil diperbarui dan login password SSH sudah diaktifkan.\n\n"
			f"{status_panel}\n\n"
			f"Detail: `{ssh_msg}`",
			buttons=back_button("setting"),
		)

	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await root_password_(event)
	else:
		await event.answer("Access Denied", alert=True)
		
@bot.on(events.CallbackQuery(data=b'speedtest'))
async def speedtest(event):
	async def speedtest_(event):
		cmd = 'speedtest-cli --share'.strip()
		try:
			z = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
		except Exception as exc:
			await upsert_message(event, f"❌ Speedtest gagal dijalankan.\n```\n{exc}\n```", buttons=back_button("setting"))
			return
		time.sleep(0)
		await event.edit("`Processing... 0%\n▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(0)
		await event.edit("`Processing... 4%\n█▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(0)
		await event.edit("`Processing... 8%\n██▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(0)
		await event.edit("`Processing... 20%\n█████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 36%\n█████████▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 52%\n█████████████▒▒▒▒▒▒▒▒▒▒▒▒ `")
		time.sleep(1)
		await event.edit("`Processing... 84%\n█████████████████████▒▒▒▒ `")
		time.sleep(0)
		await event.edit("`Processing... 100%\n█████████████████████████ `")
		await upsert_message(event, f"""
**
{z}
**
**» 🤖@AutoFTbot**
""",buttons=back_button("setting"))
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await speedtest_(event)
	else:
		await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'backup'))
async def backup(event):
	async def backup_(event):
		user_input, msgs = await ask_text_clean(event, chat, sender.id, "📧 **Input Email Backup:**", [])
		await delete_messages(chat, msgs)
		if not user_input:
			await upsert_message(event, "❌ Input email kosong. Proses dibatalkan.", buttons=back_button("backer"))
			return

		try:
			proc = subprocess.run(
				["bot-backup"],
				input=f"{user_input}\n",
				text=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT,
				timeout=180,
			)
		except Exception as exc:
			await upsert_message(event, f"❌ Gagal menjalankan backup.\n```\n{exc}\n```", buttons=back_button("backer"))
			return

		a = (proc.stdout or "").strip()
		if proc.returncode != 0:
			await upsert_message(event, f"❌ Backup gagal.\n```\n{a or 'Not Exist'}\n```", buttons=back_button("backer"))
		else:
			msg = f"""
```
{a}
```
**» 🤖@AutoFTbot**
"""
			await upsert_message(event, msg, buttons=back_button("backer"))
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await backup_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'restore'))
async def restsore(event):
	async def rssestore_(event):
		user_input, msgs = await ask_text_clean(event, chat, sender.id, "🔗 **Input Link Backup:**", [])
		await delete_messages(chat, msgs)
		if not user_input:
			await upsert_message(event, "❌ Input link kosong. Proses dibatalkan.", buttons=back_button("backer"))
			return

		try:
			proc = subprocess.run(
				["bot-restore"],
				input=f"{user_input}\n",
				text=True,
				stdout=subprocess.PIPE,
				stderr=subprocess.STDOUT,
				timeout=180,
			)
		except Exception as exc:
			await upsert_message(event, f"❌ Gagal menjalankan restore.\n```\n{exc}\n```", buttons=back_button("backer"))
			return

		a = (proc.stdout or "").strip()
		if proc.returncode != 0:
			await upsert_message(event, f"❌ Restore gagal.\n```\n{a or 'Link Not Exist'}\n```", buttons=back_button("backer"))
		else:
			msg = f"""```{a}```
**🤖@AutoFTbot**
"""
			await upsert_message(event, msg, buttons=back_button("backer"))
	chat = event.chat_id
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await rssestore_(event)
	else:
		await event.answer("Akses Ditolak",alert=True)

@bot.on(events.CallbackQuery(data=b'backer'))
async def backers(event):
	async def backers_(event):
		inline = [
[Button.inline(" BACKUP","backup"),
Button.inline(" RESTORE","restore")],
[Button.inline("⬅️ Kembali","setting")]]
		msg = f"{manager_banner('Backup & Restore', 'UTILITY')}\n\n📦 Pilih aksi backup atau restore."
		await upsert_message(event, msg, buttons=inline)
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await backers_(event)
	else:
		await event.answer("Access Denied",alert=True)


@bot.on(events.CallbackQuery(data=b'setting'))
async def settings(event):
	async def settings_(event):
		inline = [
[Button.inline(" SPEEDTEST","speedtest"),
Button.inline(" BACKUP & RESTORE","backer")],
[Button.inline(" SSH AUTH STATUS","ssh-auth-status"),
Button.inline(" SET ROOT PASSWORD","root-passwd")],
[Button.inline(" UPDATE PANEL","panel-update")],
[Button.inline(" REBOOT SERVER","reboot"),
Button.inline(" RESTART SERVICE","resx")],
[Button.inline("⬅️ Kembali","menu")]]
		msg = f"{manager_banner('Settings & Utilities', 'UTILITY')}\n\n⚙️ Pilih aksi maintenance server."
		await upsert_message(event, msg, buttons=inline)
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await settings_(event)
	else:
		await event.answer("Access Denied",alert=True)
