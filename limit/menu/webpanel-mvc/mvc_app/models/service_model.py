import shutil
import subprocess
from copy import deepcopy
from typing import Any, Dict, Iterable, List

DEFAULT_SERVICES = ["xray", "nginx", "haproxy", "ws", "ssh", "dropbear"]
DEFAULT_SERVICE_KEY = "vmess"
SERVICE_ORDER = ["ssh", "vmess", "vless", "trojan", "shadowsocks"]

SERVICE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "ssh": {
        "key": "ssh",
        "label": "SSH OVPN",
        "description": "Kelola akun SSH, OpenVPN, dan SSH WebSocket.",
        "operations": [
            {
                "name": "create",
                "label": "Create SSH",
                "tone": "primary",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                        "placeholder": "ssh001",
                    },
                    {
                        "name": "password",
                        "label": "Password",
                        "type": "text",
                        "required": True,
                        "placeholder": "password123",
                    },
                    {
                        "name": "ip_limit",
                        "label": "Limit IP",
                        "type": "number",
                        "required": True,
                        "min": 0,
                        "value": 1,
                    },
                    {
                        "name": "quota_gb",
                        "label": "Quota (GB)",
                        "type": "number",
                        "required": True,
                        "min": 0,
                        "value": 0,
                    },
                    {
                        "name": "days",
                        "label": "Expired (Days)",
                        "type": "number",
                        "required": True,
                        "min": 1,
                        "value": 30,
                    },
                ],
            },
            {
                "name": "renew",
                "label": "Renew SSH",
                "tone": "secondary",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    },
                    {
                        "name": "days",
                        "label": "Tambah Hari",
                        "type": "number",
                        "required": True,
                        "min": 1,
                        "value": 30,
                    },
                ],
            },
            {
                "name": "delete",
                "label": "Delete SSH",
                "tone": "danger",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    }
                ],
            },
            {
                "name": "trial",
                "label": "Trial SSH",
                "tone": "accent",
                "fields": [
                    {
                        "name": "trial_minutes",
                        "label": "Durasi Trial (Menit)",
                        "type": "number",
                        "required": True,
                        "min": 1,
                        "value": 60,
                    }
                ],
            },
        ],
    },
    "vmess": {
        "key": "vmess",
        "label": "VMESS",
        "description": "Kelola akun VMESS WS dan gRPC.",
        "operations": [
            {
                "name": "create",
                "label": "Create VMESS",
                "tone": "primary",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                        "placeholder": "vm001",
                    },
                    {
                        "name": "days",
                        "label": "Expired (Days)",
                        "type": "number",
                        "required": True,
                        "min": 1,
                        "value": 30,
                    },
                    {
                        "name": "quota_gb",
                        "label": "Quota (GB)",
                        "type": "number",
                        "required": True,
                        "min": 0,
                        "value": 0,
                    },
                    {
                        "name": "ip_limit",
                        "label": "Limit IP",
                        "type": "number",
                        "required": True,
                        "min": 0,
                        "value": 1,
                    },
                    {
                        "name": "sni_profile",
                        "label": "SNI Profile",
                        "type": "select",
                        "required": True,
                        "value": "3",
                        "options": [
                            {"value": "3", "label": "Default"},
                            {"value": "1", "label": "support.zoom.us"},
                            {"value": "2", "label": "live.iflix.com"},
                        ],
                    },
                ],
            },
            {
                "name": "renew",
                "label": "Renew VMESS",
                "tone": "secondary",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    },
                    {
                        "name": "days",
                        "label": "Tambah Hari",
                        "type": "number",
                        "required": True,
                        "min": 1,
                        "value": 30,
                    },
                    {
                        "name": "quota_gb",
                        "label": "Quota Baru (GB)",
                        "type": "number",
                        "required": True,
                        "min": 0,
                        "value": 0,
                    },
                    {
                        "name": "ip_limit",
                        "label": "Limit IP Baru",
                        "type": "number",
                        "required": True,
                        "min": 0,
                        "value": 1,
                    },
                ],
            },
            {
                "name": "delete",
                "label": "Delete VMESS",
                "tone": "danger",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    }
                ],
            },
            {
                "name": "trial",
                "label": "Trial VMESS",
                "tone": "accent",
                "fields": [
                    {
                        "name": "trial_config_mode",
                        "label": "Mode Konfigurasi",
                        "type": "select",
                        "required": True,
                        "value": "4",
                        "options": [
                            {"value": "1", "label": "TLS"},
                            {"value": "2", "label": "NTLS"},
                            {"value": "3", "label": "GRPC"},
                            {"value": "4", "label": "Semua"},
                        ],
                    }
                ],
            },
            {
                "name": "suspend",
                "label": "Suspend VMESS",
                "tone": "warning",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    },
                    {
                        "name": "reason",
                        "label": "Reason",
                        "type": "text",
                        "required": False,
                        "placeholder": "manual",
                    },
                ],
            },
            {
                "name": "unsuspend",
                "label": "Unsuspend VMESS",
                "tone": "secondary",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    }
                ],
            },
        ],
    },
    "vless": {
        "key": "vless",
        "label": "VLESS",
        "description": "Kelola akun VLESS WS dan gRPC.",
        "operations": [
            {
                "name": "create",
                "label": "Create VLESS",
                "tone": "primary",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                        "placeholder": "vls001",
                    },
                    {
                        "name": "days",
                        "label": "Expired (Days)",
                        "type": "number",
                        "required": True,
                        "min": 1,
                        "value": 30,
                    },
                    {
                        "name": "quota_gb",
                        "label": "Quota (GB)",
                        "type": "number",
                        "required": True,
                        "min": 0,
                        "value": 0,
                    },
                    {
                        "name": "ip_limit",
                        "label": "Limit IP",
                        "type": "number",
                        "required": True,
                        "min": 0,
                        "value": 1,
                    },
                    {
                        "name": "sni_profile",
                        "label": "SNI Profile",
                        "type": "select",
                        "required": True,
                        "value": "3",
                        "options": [
                            {"value": "3", "label": "Default"},
                            {"value": "1", "label": "support.zoom.us"},
                            {"value": "2", "label": "live.iflix.com"},
                        ],
                    },
                ],
            },
            {
                "name": "renew",
                "label": "Renew VLESS",
                "tone": "secondary",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    },
                    {
                        "name": "days",
                        "label": "Tambah Hari",
                        "type": "number",
                        "required": True,
                        "min": 1,
                        "value": 30,
                    },
                    {
                        "name": "quota_gb",
                        "label": "Quota Baru (GB)",
                        "type": "number",
                        "required": True,
                        "min": 0,
                        "value": 0,
                    },
                    {
                        "name": "ip_limit",
                        "label": "Limit IP Baru",
                        "type": "number",
                        "required": True,
                        "min": 0,
                        "value": 1,
                    },
                ],
            },
            {
                "name": "delete",
                "label": "Delete VLESS",
                "tone": "danger",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    }
                ],
            },
            {
                "name": "trial",
                "label": "Trial VLESS",
                "tone": "accent",
                "fields": [
                    {
                        "name": "trial_config_mode",
                        "label": "Mode Konfigurasi",
                        "type": "select",
                        "required": True,
                        "value": "4",
                        "options": [
                            {"value": "1", "label": "TLS"},
                            {"value": "2", "label": "NTLS"},
                            {"value": "3", "label": "GRPC"},
                            {"value": "4", "label": "Semua"},
                        ],
                    }
                ],
            },
            {
                "name": "suspend",
                "label": "Suspend VLESS",
                "tone": "warning",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    },
                    {
                        "name": "reason",
                        "label": "Reason",
                        "type": "text",
                        "required": False,
                        "placeholder": "manual",
                    },
                ],
            },
            {
                "name": "unsuspend",
                "label": "Unsuspend VLESS",
                "tone": "secondary",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    }
                ],
            },
        ],
    },
    "trojan": {
        "key": "trojan",
        "label": "TROJAN",
        "description": "Kelola akun Trojan WS dan gRPC.",
        "operations": [
            {
                "name": "create",
                "label": "Create TROJAN",
                "tone": "primary",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                        "placeholder": "trj001",
                    },
                    {
                        "name": "days",
                        "label": "Expired (Days)",
                        "type": "number",
                        "required": True,
                        "min": 1,
                        "value": 30,
                    },
                    {
                        "name": "quota_gb",
                        "label": "Quota (GB)",
                        "type": "number",
                        "required": True,
                        "min": 0,
                        "value": 0,
                    },
                    {
                        "name": "ip_limit",
                        "label": "Limit IP",
                        "type": "number",
                        "required": True,
                        "min": 0,
                        "value": 1,
                    },
                    {
                        "name": "sni_profile",
                        "label": "SNI Profile",
                        "type": "select",
                        "required": True,
                        "value": "3",
                        "options": [
                            {"value": "3", "label": "Default"},
                            {"value": "1", "label": "support.zoom.us"},
                            {"value": "2", "label": "live.iflix.com"},
                        ],
                    },
                ],
            },
            {
                "name": "renew",
                "label": "Renew TROJAN",
                "tone": "secondary",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    },
                    {
                        "name": "days",
                        "label": "Tambah Hari",
                        "type": "number",
                        "required": True,
                        "min": 1,
                        "value": 30,
                    },
                    {
                        "name": "quota_gb",
                        "label": "Quota Baru (GB)",
                        "type": "number",
                        "required": True,
                        "min": 0,
                        "value": 0,
                    },
                    {
                        "name": "ip_limit",
                        "label": "Limit IP Baru",
                        "type": "number",
                        "required": True,
                        "min": 0,
                        "value": 1,
                    },
                ],
            },
            {
                "name": "delete",
                "label": "Delete TROJAN",
                "tone": "danger",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    }
                ],
            },
            {
                "name": "trial",
                "label": "Trial TROJAN",
                "tone": "accent",
                "fields": [
                    {
                        "name": "trial_config_mode",
                        "label": "Mode Konfigurasi",
                        "type": "select",
                        "required": True,
                        "value": "4",
                        "options": [
                            {"value": "1", "label": "TLS"},
                            {"value": "2", "label": "NTLS"},
                            {"value": "3", "label": "GRPC"},
                            {"value": "4", "label": "Semua"},
                        ],
                    }
                ],
            },
            {
                "name": "suspend",
                "label": "Suspend TROJAN",
                "tone": "warning",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    },
                    {
                        "name": "reason",
                        "label": "Reason",
                        "type": "text",
                        "required": False,
                        "placeholder": "manual",
                    },
                ],
            },
            {
                "name": "unsuspend",
                "label": "Unsuspend TROJAN",
                "tone": "secondary",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    }
                ],
            },
        ],
    },
    "shadowsocks": {
        "key": "shadowsocks",
        "label": "SHADOWSOCKS",
        "description": "Kelola akun Shadowsocks WS dan gRPC.",
        "operations": [
            {
                "name": "create",
                "label": "Create SS",
                "tone": "primary",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                        "placeholder": "ss001",
                    },
                    {
                        "name": "days",
                        "label": "Expired (Days)",
                        "type": "number",
                        "required": True,
                        "min": 1,
                        "value": 30,
                    },
                    {
                        "name": "quota_gb",
                        "label": "Quota (GB)",
                        "type": "number",
                        "required": True,
                        "min": 0,
                        "value": 0,
                    },
                ],
            },
            {
                "name": "renew",
                "label": "Renew SS",
                "tone": "secondary",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    },
                    {
                        "name": "days",
                        "label": "Tambah Hari",
                        "type": "number",
                        "required": True,
                        "min": 1,
                        "value": 30,
                    },
                ],
            },
            {
                "name": "delete",
                "label": "Delete SS",
                "tone": "danger",
                "fields": [
                    {
                        "name": "username",
                        "label": "Username",
                        "type": "text",
                        "required": True,
                    }
                ],
            },
            {
                "name": "trial",
                "label": "Trial SS",
                "tone": "accent",
                "fields": [],
            },
        ],
    },
}


def _systemctl_available() -> bool:
    return shutil.which("systemctl") is not None


def get_service_status(service_names: Iterable[str] | None = None) -> Dict[str, str]:
    services = list(service_names or DEFAULT_SERVICES)
    if not _systemctl_available():
        return {name: "unknown" for name in services}

    statuses: Dict[str, str] = {}
    for service in services:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True,
                check=False,
            )
            status = result.stdout.strip() or "unknown"
        except OSError:
            status = "unknown"
        statuses[service] = status

    return statuses


def normalize_service_key(service: str | None) -> str | None:
    key = str(service or "").strip().lower()
    if key in SERVICE_DEFINITIONS:
        return key
    return None


def get_default_service_key() -> str:
    return DEFAULT_SERVICE_KEY


def get_service_definition(service: str | None) -> Dict[str, Any] | None:
    key = normalize_service_key(service)
    if key is None:
        return None
    return deepcopy(SERVICE_DEFINITIONS[key])


def get_service_catalog() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for key in SERVICE_ORDER:
        if key not in SERVICE_DEFINITIONS:
            continue
        row = deepcopy(SERVICE_DEFINITIONS[key])
        row["operation_count"] = len(row.get("operations", []))
        rows.append(row)
    return rows


def get_service_operation_names(service: str | None) -> List[str]:
    profile = get_service_definition(service)
    if not profile:
        return []
    return [item.get("name", "") for item in profile.get("operations", [])]
