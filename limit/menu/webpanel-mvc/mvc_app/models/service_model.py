import shutil
import subprocess
from typing import Dict, Iterable

DEFAULT_SERVICES = ["xray", "nginx", "haproxy", "ws", "ssh", "dropbear"]


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
