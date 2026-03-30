import os
from pathlib import Path


def _safe_int(value: str, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _safe_bool(value: str, fallback: bool) -> bool:
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return fallback


def _default_secret() -> str:
    return "vpnxray-webpanel-dev-secret"


class Settings:
    WEB_PANEL_HOST = os.getenv("WEB_PANEL_HOST", "127.0.0.1")
    WEB_PANEL_PORT = _safe_int(os.getenv("WEB_PANEL_PORT", "3000"), 3000)

    WEB_PANEL_SECRET_KEY = os.getenv("WEB_PANEL_SECRET_KEY", _default_secret())
    SECRET_KEY = WEB_PANEL_SECRET_KEY

    PANEL_USER_FILE = os.getenv("PANEL_USER_FILE", "/usr/bin/user")
    PANEL_PASS_FILE = os.getenv("PANEL_PASS_FILE", "/usr/bin/password")
    XRAY_CONFIG_PATH = os.getenv("XRAY_CONFIG_PATH", "/etc/xray/config.json")

    CLI_SCRIPT_ROOT = os.getenv("CLI_SCRIPT_ROOT", "/usr/local/sbin")
    MUTATION_LOCK_FILE = os.getenv(
        "MUTATION_LOCK_FILE", "/var/lock/vpnxray-webpanel/mutation.lock"
    )
    MUTATION_LOCK_TIMEOUT_SEC = _safe_int(
        os.getenv("MUTATION_LOCK_TIMEOUT_SEC", "30"), 30
    )
    CLI_MUTATION_TIMEOUT_SEC = _safe_int(
        os.getenv("CLI_MUTATION_TIMEOUT_SEC", "180"), 180
    )
    AUDIT_LOG_PATH = os.getenv(
        "AUDIT_LOG_PATH", "/var/log/vpnxray-webpanel/audit.log"
    )
    MUTATION_SAFETY_ENABLED = _safe_bool(
        os.getenv("MUTATION_SAFETY_ENABLED", "1"), True
    )
    MUTATION_PRECHECK_XRAY = _safe_bool(
        os.getenv("MUTATION_PRECHECK_XRAY", "1"), True
    )
    MUTATION_POSTCHECK_TIMEOUT_SEC = _safe_int(
        os.getenv("MUTATION_POSTCHECK_TIMEOUT_SEC", "25"), 25
    )
    MUTATION_SNAPSHOT_DIR = os.getenv(
        "MUTATION_SNAPSHOT_DIR", "/etc/xray/backup-webpanel"
    )
    XRAY_BINARY_PATH = os.getenv("XRAY_BINARY_PATH", "/usr/bin/xray")
    WEB_PANEL_ASSET_VERSION = os.getenv("WEB_PANEL_ASSET_VERSION", "1")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # HTTPS termination biasanya terjadi di HAProxy/Nginx.
    SESSION_COOKIE_SECURE = False

    BASE_DIR = Path(__file__).resolve().parent.parent
