from kyt import *
import asyncio
import zlib


SERVICE_LABELS = {
    "ssh": "SSH",
    "vmess": "VMESS",
    "vless": "VLESS",
    "trojan": "TROJAN",
    "shadowsocks": "SHADOWSOCKS",
}


def _expiry_notice_days() -> int:
    try:
        return max(0, int(globals().get("EXPIRY_NOTICE_DAYS", 3)))
    except Exception:
        return 3


def _expiry_notice_interval() -> int:
    try:
        minutes = int(globals().get("EXPIRY_NOTICE_INTERVAL_MINUTES", 360))
        return max(60, minutes * 60)
    except Exception:
        return 21600


def _dedupe_ids(values) -> list:
    seen = set()
    result = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _notice_targets(account: dict) -> list:
    targets = []
    owner_id = str(account.get("tg_id") or "").strip()
    owner_status = str(account.get("telegram_status") or "").strip().lower()
    if owner_id and (owner_status == "approved" or is_admin_user(owner_id)):
        targets.append(owner_id)

    targets.extend(get_all_admin_ids())
    return _dedupe_ids(targets)


def _renew_buttons(service: str, username: str):
    callback = f"renew-{service}:{username}".encode()
    return [[Button.inline("Renew Akun", callback)]]


def _synthetic_account_id(service: str, username: str) -> int:
    raw = f"xray:{service}:{username}".encode()
    value = int(zlib.crc32(raw) or 1)
    return -value


def _read_system_xray_accounts(days_before: int) -> list:
    path = "/etc/xray/config.json"
    if not os.path.isfile(path):
        return []

    today = DT.date.today()
    window = max(0, int(days_before))
    patterns = (
        ("shadowsocks", re.compile(r"^#!#\s+(\S+)\s+(\S+)")),
        ("trojan", re.compile(r"^#!\s+(\S+)\s+(\S+)")),
        ("vless", re.compile(r"^#&\s+(\S+)\s+(\S+)")),
        ("vmess", re.compile(r"^###\s+(\S+)\s+(\S+)")),
    )
    seen = set()
    accounts = []

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            lines = fh.readlines()
    except Exception as exc:
        logging.warning("Gagal membaca akun Xray dari %s: %s", path, exc)
        return []

    for line in lines:
        text = line.strip()
        for service, pattern in patterns:
            match = pattern.match(text)
            if not match:
                continue

            username = match.group(1).strip()
            expires_at = match.group(2).strip()
            key = (service, username.lower())
            if key in seen:
                break
            seen.add(key)

            expiry = parse_account_expiry_date(expires_at)
            if expiry is None:
                break

            days_left = (expiry - today).days
            if 0 <= days_left <= window:
                accounts.append(
                    {
                        "id": _synthetic_account_id(service, username),
                        "tg_id": "",
                        "service": service,
                        "category": "xray",
                        "username": username,
                        "expires_at": expires_at,
                        "expiry_date": expiry.isoformat(),
                        "days_left": days_left,
                        "telegram_status": "",
                    }
                )
            break

    return accounts


def _format_days_left(days_left: int) -> str:
    if days_left <= 0:
        return "hari ini"
    if days_left == 1:
        return "1 hari lagi"
    return f"{days_left} hari lagi"


def _notice_text(account: dict) -> str:
    service = str(account.get("service") or "").strip().lower()
    label = SERVICE_LABELS.get(service, service.upper() or "VPN")
    username = str(account.get("username") or "-").strip()
    expiry = str(account.get("expiry_date") or account.get("expires_at") or "-").strip()
    days_left = int(account.get("days_left", 0) or 0)
    owner_id = str(account.get("tg_id") or "").strip()

    lines = [
        "⚠️ **Masa aktif akun VPN hampir habis**",
        "",
        f"• Service: `{label}`",
        f"• Username: `{username}`",
    ]
    if owner_id:
        lines.append(f"• Telegram member: `{owner_id}`")
    lines.extend(
        [
            f"• Expired: `{expiry}` ({_format_days_left(days_left)})",
            "",
            "Silakan lakukan renew agar akun tidak terputus.",
        ]
    )
    return "\n".join(lines)


async def send_expiry_notifications_once():
    notice_day = DT.date.today().isoformat()
    notice_days = _expiry_notice_days()
    accounts = list_expiring_accounts(notice_days)
    seen = {
        (str(item.get("service") or "").strip().lower(), str(item.get("username") or "").strip().lower())
        for item in accounts
    }
    for account in _read_system_xray_accounts(notice_days):
        key = (
            str(account.get("service") or "").strip().lower(),
            str(account.get("username") or "").strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        accounts.append(account)

    for account in accounts:
        account_id = account.get("id")
        service = str(account.get("service") or "").strip().lower()
        username = str(account.get("username") or "").strip()
        if not account_id or not service or not username:
            continue

        text = _notice_text(account)
        buttons = _renew_buttons(service, username)

        for target_id in _notice_targets(account):
            if expiry_notification_sent(account_id, target_id, notice_day):
                continue
            try:
                await bot.send_message(int(target_id), text, buttons=buttons)
                mark_expiry_notification_sent(account_id, target_id, notice_day)
            except Exception as exc:
                logging.warning(
                    "Gagal kirim notifikasi expired akun %s/%s ke %s: %s",
                    service,
                    username,
                    target_id,
                    exc,
                )


async def expiry_notification_loop():
    await asyncio.sleep(10)
    while True:
        try:
            await send_expiry_notifications_once()
        except Exception as exc:
            logging.exception("Loop notifikasi expiry gagal: %s", exc)
        await asyncio.sleep(_expiry_notice_interval())


def _start_expiry_notifier():
    try:
        bot.loop.create_task(expiry_notification_loop())
        logging.info("Expiry notifier aktif: reminder %s hari sebelum expired", _expiry_notice_days())
    except Exception as exc:
        logging.warning("Gagal mengaktifkan expiry notifier: %s", exc)


_start_expiry_notifier()
