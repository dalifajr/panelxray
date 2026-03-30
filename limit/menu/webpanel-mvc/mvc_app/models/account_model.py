from dataclasses import asdict, dataclass
from pathlib import Path
import re
from typing import Dict, List, Set, Tuple

MARKER_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("shadowsocks", re.compile(r"^#!#\s+(\S+)\s+(\S+)")),
    ("trojan", re.compile(r"^#!\s+(\S+)\s+(\S+)")),
    ("vless", re.compile(r"^#&\s+(\S+)\s+(\S+)")),
    ("vmess", re.compile(r"^###\s+(\S+)\s+(\S+)")),
]

PROTOCOL_SORT_ORDER = {
    "ssh": 0,
    "vmess": 1,
    "vless": 2,
    "trojan": 3,
    "shadowsocks": 4,
}

DEFAULT_SSH_DB_PATH = "/etc/ssh/.ssh.db"
DEFAULT_SUSPEND_ROOT = "/etc/kyt/suspended"


@dataclass
class Account:
    protocol: str
    username: str
    expiry: str
    status: str = "active"


def _parse_marker_line(line: str) -> Tuple[str, str, str] | None:
    text = line.strip()
    for protocol, pattern in MARKER_PATTERNS:
        match = pattern.match(text)
        if match:
            return protocol, match.group(1), match.group(2)
    return None


def _parse_ssh_db_line(line: str) -> Account | None:
    text = line.strip()
    parts = text.split()
    if len(parts) < 2:
        return None

    if text.startswith("#ssh# "):
        username = parts[1]
        expiry = " ".join(parts[5:]).strip() if len(parts) > 5 else "unknown"
    elif text.startswith("### "):
        # Trial SSH entries are stored as "### <username>" without expiry date.
        username = parts[1]
        expiry = "trial"
    else:
        return None

    if not expiry:
        expiry = "unknown"

    return Account(protocol="ssh", username=username, expiry=expiry, status="active")


def _load_suspended_users(suspended_root: str) -> Set[Tuple[str, str]]:
    root = Path(suspended_root)
    if not root.exists() or not root.is_dir():
        return set()

    suspended: Set[Tuple[str, str]] = set()
    for service_dir in root.iterdir():
        if not service_dir.is_dir():
            continue
        protocol = service_dir.name.strip().lower()
        if not protocol:
            continue

        for user_file in service_dir.iterdir():
            if not user_file.is_file():
                continue
            username = user_file.name.strip()
            if username:
                suspended.add((protocol, username))

    return suspended


def load_accounts(
    config_path: str,
    ssh_db_path: str = DEFAULT_SSH_DB_PATH,
    suspended_root: str = DEFAULT_SUSPEND_ROOT,
) -> List[Dict[str, str]]:
    unique: Dict[Tuple[str, str], Account] = {}

    xray_path = Path(config_path)
    if xray_path.exists():
        raw_lines = xray_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        for line in raw_lines:
            parsed = _parse_marker_line(line)
            if not parsed:
                continue

            protocol, username, expiry = parsed
            key = (protocol, username)
            unique[key] = Account(
                protocol=protocol,
                username=username,
                expiry=expiry,
                status="active",
            )

    ssh_path = Path(ssh_db_path)
    if ssh_path.exists():
        for line in ssh_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            parsed = _parse_ssh_db_line(line)
            if not parsed:
                continue
            unique[(parsed.protocol, parsed.username)] = parsed

    suspended_users = _load_suspended_users(suspended_root)
    for key, account in unique.items():
        if key in suspended_users:
            account.status = "suspended"

    rows = [asdict(account) for account in unique.values()]
    rows.sort(
        key=lambda item: (
            PROTOCOL_SORT_ORDER.get(item.get("protocol", ""), 99),
            item.get("username", ""),
        )
    )
    return rows


def summarize_accounts(accounts: List[Dict[str, str]]) -> Dict[str, int]:
    summary = {
        "ssh": 0,
        "vmess": 0,
        "vless": 0,
        "trojan": 0,
        "shadowsocks": 0,
        "suspended": 0,
        "total": 0,
    }

    for account in accounts:
        protocol = account.get("protocol", "")
        if protocol in summary:
            summary[protocol] += 1
            summary["total"] += 1

        if account.get("status") == "suspended":
            summary["suspended"] += 1

    return summary
