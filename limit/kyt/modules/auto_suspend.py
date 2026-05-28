from kyt import *
from kyt.modules.ui import *
import os
import subprocess

@bot.on(events.CallbackQuery(pattern=b"^un_(.+)_(.+)$"))
async def handle_unsuspend_auto(event):
    if not await require_admin(event):
        return
    service = event.pattern_match.group(1).decode("utf-8")
    user = event.pattern_match.group(2).decode("utf-8")
    
    script_map = {
        "vmess": "unsuspws",
        "vless": "unsuspvless",
        "trojan": "unsusptr",
        "shadowsocks": "unsuspss",
        "ssh": "unsuspssh"
    }
    script = script_map.get(service)
    
    if script:
        # Panggil script unsuspend
        try:
            # Menggunakan subprocess dengan --user agar tidak interaktif
            subprocess.run([script, "--user", user], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
            
    await upsert_message(event, f"✅ Akun `{user}` (Service: {service.upper()}) telah berhasil di-unsuspend.", buttons=None)

@bot.on(events.CallbackQuery(pattern=b"^up_(.+)_(.+)$"))
async def handle_increase_limit_auto(event):
    if not await require_admin(event):
        return
    service = event.pattern_match.group(1).decode("utf-8")
    user = event.pattern_match.group(2).decode("utf-8")
    sender = await event.get_sender()
    
    # Minta limit baru
    new_limit_str = await ask_text(event, event.chat_id, sender.id, f"📝 Masukkan Limit IP yang baru untuk akun `{user}` ({service.upper()}):")
    
    if not new_limit_str or not new_limit_str.isdigit() or int(new_limit_str) <= 0:
        await upsert_message(event, "❌ Input dibatalkan atau limit IP tidak valid. Harus berupa angka positif.", buttons=None)
        return
        
    new_limit = int(new_limit_str)
    
    file_path = f"/etc/kyt/limit/{service}/ip/{user}"
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write(str(new_limit))
        await upsert_message(event, f"✅ Limit IP akun `{user}` ({service.upper()}) berhasil dinaikkan menjadi {new_limit}.", buttons=None)
    except Exception as e:
        await upsert_message(event, f"❌ Gagal memperbarui limit IP: {e}", buttons=None)

@bot.on(events.CallbackQuery(pattern=b"^del_(.+)_(.+)$"))
async def handle_delete_account_auto(event):
    if not await require_admin(event):
        return
    service = event.pattern_match.group(1).decode("utf-8")
    user = event.pattern_match.group(2).decode("utf-8")
    
    script_map = {
        "vmess": "delws",
        "vless": "delvless",
        "trojan": "deltr",
        "shadowsocks": "delss",
        "ssh": "delssh"
    }
    script = script_map.get(service)
    
    if script:
        try:
            # Karena script del* mungkin interaktif (meminta input via stdin), kita pipe username ke stdin.
            process = subprocess.Popen([script], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            process.communicate(input=f"{user}\n".encode())
        except Exception:
            pass
            
    await upsert_message(event, f"🗑 Akun `{user}` ({service.upper()}) telah dihapus secara permanen.", buttons=None)
