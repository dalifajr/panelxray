from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Any, Iterator

from .audit_service import append_audit_log
from .lock_service import LockTimeoutError, mutation_lock

SUPPORTED_PROTOCOLS = {"vless", "vmess", "trojan", "shadowsocks"}
SUPPORTED_OPERATIONS = {"create", "renew", "delete"}

SCRIPT_NAME_MAP = {
    "vless": {"create": "addvless", "renew": "renewvless", "delete": "delvless"},
    "vmess": {"create": "addws", "renew": "renewws", "delete": "delws"},
    "trojan": {"create": "addtr", "renew": "renewtr", "delete": "deltr"},
    "shadowsocks": {
        "create": "addss",
        "renew": "renewss",
        "delete": "delss",
    },
}


@contextmanager
def _shim_bin_dir() -> Iterator[str]:
    # Shim command mencegah script legacy kembali ke menu interaktif.
    with tempfile.TemporaryDirectory(prefix="vpnxray-webpanel-shim-") as tmp_dir:
        script_body = "#!/bin/sh\nexit 0\n"
        for command_name in ("menu", "m-trojan", "v2ray-menu"):
            command_path = Path(tmp_dir) / command_name
            command_path.write_text(script_body, encoding="utf-8")
            command_path.chmod(0o755)
        yield tmp_dir


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_choice(choice: Any) -> str:
    text = str(choice or "").strip().lower()
    if text in {"1", "support.zoom.us", "zoom", "support-zoom-us"}:
        return "1"
    if text in {"2", "live.iflix.com", "iflix", "live-iflix-com"}:
        return "2"
    return "3"


def _build_create_input(protocol: str, payload: dict[str, Any]) -> str:
    username = str(payload.get("username", "")).strip()
    if not username:
        raise MutationError("Username wajib diisi.")

    days = _safe_int(payload.get("days"), 0)
    quota_gb = _safe_int(payload.get("quota_gb"), 0)
    ip_limit = _safe_int(payload.get("ip_limit"), 0)

    if days <= 0:
        raise MutationError("Expired days harus lebih dari 0.")

    if protocol == "shadowsocks":
        lines = [username, str(days), str(max(0, quota_gb))]
        return "\n".join(lines) + "\n"

    sni_choice = _normalize_choice(payload.get("sni_profile"))
    lines = [
        sni_choice,
        username,
        str(days),
        str(max(0, quota_gb)),
        str(max(0, ip_limit)),
    ]
    return "\n".join(lines) + "\n"


def _build_renew_input(protocol: str, payload: dict[str, Any]) -> str:
    username = str(payload.get("username", "")).strip()
    if not username:
        raise MutationError("Username wajib diisi.")

    days = _safe_int(payload.get("days"), 0)
    if days <= 0:
        raise MutationError("Expired days harus lebih dari 0.")

    if protocol == "shadowsocks":
        return f"{username}\n{days}\n"

    quota_gb = _safe_int(payload.get("quota_gb"), 0)
    ip_limit = _safe_int(payload.get("ip_limit"), 0)
    lines = [username, str(days), str(max(0, quota_gb)), str(max(0, ip_limit))]
    return "\n".join(lines) + "\n"


def _build_delete_input(payload: dict[str, Any]) -> str:
    username = str(payload.get("username", "")).strip()
    if not username:
        raise MutationError("Username wajib diisi.")
    return f"{username}\n"


def _build_stdin(operation: str, protocol: str, payload: dict[str, Any]) -> str:
    if operation == "create":
        return _build_create_input(protocol, payload)
    if operation == "renew":
        return _build_renew_input(protocol, payload)
    return _build_delete_input(payload)


def _script_command(script_name: str, script_root: str) -> str:
    script_path = f"{script_root.rstrip('/')}/{script_name}"
    return f"set +e; source \"{script_path}\""


def _tail_lines(text: str, max_lines: int = 40) -> str:
    rows = text.splitlines()
    if len(rows) <= max_lines:
        return text.strip()
    return "\n".join(rows[-max_lines:]).strip()


@dataclass
class MutationResult:
    operation: str
    protocol: str
    script_name: str
    username: str
    returncode: int
    stdout_tail: str
    stderr_tail: str


class MutationError(RuntimeError):
    pass


def run_cli_mutation(
    operation: str,
    protocol: str,
    payload: dict[str, Any],
    operator: str,
    *,
    script_root: str,
    lock_file: str,
    lock_timeout_seconds: int,
    command_timeout_seconds: int,
    audit_log_path: str,
) -> MutationResult:
    operation = str(operation or "").strip().lower()
    protocol = str(protocol or "").strip().lower()

    if operation not in SUPPORTED_OPERATIONS:
        raise MutationError("Operation tidak valid. Gunakan create, renew, atau delete.")
    if protocol not in SUPPORTED_PROTOCOLS:
        raise MutationError("Protocol tidak valid.")

    script_name = SCRIPT_NAME_MAP[protocol][operation]
    script_path = Path(script_root) / script_name
    if not script_path.exists():
        raise MutationError(f"Script tidak ditemukan: {script_path}")

    stdin_data = _build_stdin(operation, protocol, payload)
    username = str(payload.get("username", "")).strip()

    command = _script_command(script_name=script_name, script_root=script_root)

    audit_context = {
        "event": "web_crud_mutation",
        "operator": operator,
        "operation": operation,
        "protocol": protocol,
        "script": script_name,
        "username": username,
    }

    append_audit_log(
        audit_log_path,
        {
            **audit_context,
            "status": "started",
        },
    )

    try:
        with mutation_lock(lock_file, timeout_seconds=lock_timeout_seconds):
            with _shim_bin_dir() as shim_dir:
                base_env = os.environ.copy()
                default_path = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
                base_env["PATH"] = (
                    f"{shim_dir}:{script_root}:{base_env.get('PATH', default_path)}"
                )
                base_env.setdefault("TERM", "dumb")

                completed = subprocess.run(
                    ["bash", "-lc", command],
                    input=stdin_data,
                    capture_output=True,
                    text=True,
                    timeout=command_timeout_seconds,
                    check=False,
                    env=base_env,
                )
    except LockTimeoutError as exc:
        append_audit_log(
            audit_log_path,
            {
                **audit_context,
                "status": "lock_timeout",
                "error": str(exc),
            },
        )
        raise MutationError(str(exc)) from exc
    except subprocess.TimeoutExpired as exc:
        append_audit_log(
            audit_log_path,
            {
                **audit_context,
                "status": "timeout",
                "error": "Script timeout",
            },
        )
        raise MutationError("Eksekusi script timeout.") from exc
    except OSError as exc:
        append_audit_log(
            audit_log_path,
            {
                **audit_context,
                "status": "os_error",
                "error": str(exc),
            },
        )
        raise MutationError("Gagal mengeksekusi shell adapter.") from exc

    result = MutationResult(
        operation=operation,
        protocol=protocol,
        script_name=script_name,
        username=username,
        returncode=completed.returncode,
        stdout_tail=_tail_lines(completed.stdout or ""),
        stderr_tail=_tail_lines(completed.stderr or ""),
    )

    audit_row = {
        **audit_context,
        "status": "success" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "stdout_tail": result.stdout_tail,
        "stderr_tail": result.stderr_tail,
    }
    append_audit_log(audit_log_path, audit_row)

    if result.returncode != 0:
        raise MutationError(
            "Eksekusi script gagal. Cek audit log untuk detail terakhir."
        )

    return result
