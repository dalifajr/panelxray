from kyt import *
import asyncio
from kyt.modules.ui import manager_banner, back_button, upsert_message, is_admin


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
			proc = await asyncio.create_subprocess_shell(
				cmd,
				stdout=asyncio.subprocess.PIPE,
				stderr=asyncio.subprocess.STDOUT,
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
		
@bot.on(events.CallbackQuery(data=b'speedtest'))
async def speedtest(event):
	async def speedtest_(event):
		cmd = 'speedtest-cli --share'.strip()
		z = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
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
		await event.respond(f"""
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
		async with bot.conversation(chat) as user:
			await event.respond('**Input Email:**')
			user = user.wait_event(events.NewMessage(incoming=True, from_users=sender.id))
			user = (await user).raw_text
		cmd = f'printf "%s\n" "{user}" | bot-backup'
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond("**Not Exist**")
		else:
			msg = f"""
```
{a}
```
**» 🤖@AutoFTbot**
"""
			await event.respond(msg, buttons=back_button("backer"))
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
		async with bot.conversation(chat) as user:
			await event.respond('**Input Link Backup:**')
			user = user.wait_event(events.NewMessage(incoming=True, from_users=sender.id))
			user = (await user).raw_text
		cmd = f'printf "%s\n" "{user}" | bot-restore'
		try:
			a = subprocess.check_output(cmd, shell=True).decode("utf-8")
		except:
			await event.respond("**Link Not Exist**")
		else:
			msg = f"""```{a}```
**🤖@AutoFTbot**
"""
			await event.respond(msg, buttons=back_button("backer"))
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
		await event.edit(msg,buttons=inline)
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
[Button.inline(" UPDATE PANEL","panel-update")],
[Button.inline(" REBOOT SERVER","reboot"),
Button.inline(" RESTART SERVICE","resx")],
[Button.inline("⬅️ Kembali","menu")]]
		msg = f"{manager_banner('Settings & Utilities', 'UTILITY')}\n\n⚙️ Pilih aksi maintenance server."
		await event.edit(msg,buttons=inline)
	sender = await event.get_sender()
	a = valid(str(sender.id))
	if a == "true":
		await settings_(event)
	else:
		await event.answer("Access Denied",alert=True)
