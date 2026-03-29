from dataclasses import dataclass, asdict
from pathlib import Path
import re
from typing import Dict, List, Tuple

MARKER_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("shadowsocks", re.compile(r"^#!#\s+(\S+)\s+(\S+)")),
    ("trojan", re.compile(r"^#!\s+(\S+)\s+(\S+)")),
    ("vless", re.compile(r"^#&\s+(\S+)\s+(\S+)")),
    ("vmess", re.compile(r"^###\s+(\S+)\s+(\S+)")),
]


@dataclass
class Account:
    protocol: str
    username: str
    expiry: str


def _parse_marker_line(line: str) -> Tuple[str, str, str] | None:
    text = line.strip()
    for protocol, pattern in MARKER_PATTERNS:
        match = pattern.match(text)
        if match:
            return protocol, match.group(1), match.group(2)
    return None


def load_accounts(config_path: str) -> List[Dict[str, str]]:
    path = Path(config_path)
    if not path.exists():
        return []

    raw_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

    unique: Dict[Tuple[str, str], Account] = {}
    for line in raw_lines:
        parsed = _parse_marker_line(line)
        if not parsed:
            continue

        protocol, username, expiry = parsed
        key = (protocol, username)
        unique[key] = Account(protocol=protocol, username=username, expiry=expiry)

    rows = [asdict(account) for account in unique.values()]
    rows.sort(key=lambda item: (item["protocol"], item["username"]))
    return rows


def summarize_accounts(accounts: List[Dict[str, str]]) -> Dict[str, int]:
    summary = {
        "vmess": 0,
        "vless": 0,
        "trojan": 0,
        "shadowsocks": 0,
        "total": 0,
    }

    for account in accounts:
        protocol = account.get("protocol", "")
        if protocol in summary:
            summary[protocol] += 1
            summary["total"] += 1

    return summary
