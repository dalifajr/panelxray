from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Iterator

from .audit_service import append_audit_log
from .lock_service import LockTimeoutError, mutation_lock

SUPPORTED_PROTOCOLS = {"ssh", "vless", "vmess", "trojan", "shadowsocks"}
SUPPORTED_OPERATIONS = {
    "create",
    "renew",
    "delete",
    "trial",
    "suspend",
    "unsuspend",
}

SCRIPT_NAME_MAP = {
    "ssh": {
        "create": "addssh",
        "renew": "renewssh",
        "delete": "delssh",
        "trial": "trial",
    },
    "vless": {
        "create": "addvless",
        "renew": "renewvless",
        "delete": "delvless",
        "trial": "trialvless",
        "suspend": "suspvless",
        "unsuspend": "unsuspvless",
    },
    "vmess": {
        "create": "addws",
        "renew": "renewws",
        "delete": "delws",
        "trial": "trialws",
        "suspend": "suspws",
        "unsuspend": "unsuspws",
    },
    "trojan": {
        "create": "addtr",
        "renew": "renewtr",
        "delete": "deltr",
        "trial": "trialtr",
        "suspend": "susptr",
        "unsuspend": "unsusptr",
    },
    "shadowsocks": {
        "create": "addss",
        "renew": "renewss",
        "delete": "delss",
        "trial": "trialss",
    },
}

ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
LINK_RE = re.compile(r"(?:https?://|vmess://|vless://|trojan://|ss://)\S+", re.IGNORECASE)

TRIAL_MODE_MAP = {
    "1": "1",
    "2": "2",
    "3": "3",
    "4": "4",
    "tls": "1",
    "ntls": "2",
    "grpc": "3",
    "all": "4",
    "semua": "4",
}

ARTIFACT_PATTERNS = {
    "ssh": ["/var/www/html/ssh-{username}.txt"],
    "vmess": ["/var/www/html/vmess-{username}.txt"],
    "vless": ["/var/www/html/vless-{username}.txt"],
    "trojan": ["/var/www/html/trojan-{username}.txt"],
    "shadowsocks": [
        "/var/www/html/sodosokws-{username}.txt",
        "/var/www/html/sodosokgrpc-{username}.txt",
    ],
}


@contextmanager
def _shim_bin_dir() -> Iterator[str]:
    # Shim command mencegah script legacy kembali ke menu interaktif.
    with tempfile.TemporaryDirectory(prefix="vpnxray-webpanel-shim-") as tmp_dir:
        script_body = "#!/bin/sh\nexit 0\n"
        for command_name in (
            "menu",
            "m-trojan",
            "v2ray-menu",
            "vmess",
            "vless",
            "trojan",
            "ssh",
            "m-vless",
            "m-vmess",
            "m-ssws",
            "m-sshws",
        ):
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


def _normalize_trial_mode(choice: Any) -> str:
    text = str(choice or "").strip().lower()
    return TRIAL_MODE_MAP.get(text, "4")


def _build_create_input(protocol: str, payload: dict[str, Any]) -> str:
    username = str(payload.get("username", "")).strip()
    if not username:
        raise MutationError("Username wajib diisi.")

    days = _safe_int(payload.get("days"), 0)
    quota_gb = _safe_int(payload.get("quota_gb"), 0)
    ip_limit = _safe_int(payload.get("ip_limit"), 0)

    if days <= 0:
        raise MutationError("Expired days harus lebih dari 0.")

    if protocol == "ssh":
        password = str(payload.get("password", "")).strip()
        if not password:
            raise MutationError("Password wajib diisi untuk create SSH.")

        lines = [
            username,
            password,
            str(max(0, ip_limit)),
            str(max(0, quota_gb)),
            str(days),
        ]
        return "\n".join(lines) + "\n"

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

    if protocol == "ssh":
        return f"{username}\n{days}\n"

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


def _build_trial_input(protocol: str, payload: dict[str, Any]) -> str:
    if protocol == "ssh":
        minutes = max(1, _safe_int(payload.get("trial_minutes"), 60))
        return f"{minutes}\n"

    if protocol in {"vmess", "vless", "trojan"}:
        mode = _normalize_trial_mode(payload.get("trial_config_mode"))
        minutes = max(1, _safe_int(payload.get("trial_minutes"), 60))
        return f"{mode}\n{minutes}\n"

    return ""


def _build_script_args(operation: str, payload: dict[str, Any]) -> list[str]:
    if operation not in {"suspend", "unsuspend"}:
        return []

    username = str(payload.get("username", "")).strip()
    if not username:
        raise MutationError("Username wajib diisi.")

    args = ["--user", username]
    if operation == "suspend":
        reason = str(payload.get("reason", "")).strip() or "manual"
        args.extend(["--reason", reason])

    return args


def _build_stdin(operation: str, protocol: str, payload: dict[str, Any]) -> str:
    if operation == "create":
        return _build_create_input(protocol, payload)
    if operation == "renew":
        return _build_renew_input(protocol, payload)
    if operation == "delete":
        return _build_delete_input(payload)
    if operation == "trial":
        return _build_trial_input(protocol, payload)
    return ""


def _tail_lines(text: str, max_lines: int = 40) -> str:
    cleaned = _strip_ansi(text)
    rows = cleaned.splitlines()
    if len(rows) <= max_lines:
        return cleaned.strip()
    return "\n".join(rows[-max_lines:]).strip()


def _strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text or "").replace("\r", "")


def _is_separator(text: str) -> bool:
    if not text:
        return True
    return not any(ch.isalnum() for ch in text)


def _normalize_field_key(label: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "_", label.strip().lower())
    return key.strip("_")


def _extract_fields_and_links(stdout: str) -> tuple[list[dict[str, str]], list[str]]:
    fields: list[dict[str, str]] = []
    links: list[str] = []
    pending_label = ""
    seen_pairs: set[tuple[str, str]] = set()

    for raw_line in _strip_ansi(stdout).splitlines():
        line = raw_line.strip()
        if not line or _is_separator(line):
            continue

        for candidate in LINK_RE.findall(line):
            links.append(candidate)

        if pending_label and LINK_RE.fullmatch(line):
            key = _normalize_field_key(pending_label)
            pair_key = (pending_label, line)
            if pair_key not in seen_pairs:
                fields.append({"key": key, "label": pending_label, "value": line})
                seen_pairs.add(pair_key)
            pending_label = ""
            continue

        if ":" in line:
            label, value = line.split(":", 1)
            label = label.strip()
            value = value.strip()
            if not label:
                continue

            if value:
                key = _normalize_field_key(label)
                pair_key = (label, value)
                if pair_key not in seen_pairs:
                    fields.append({"key": key, "label": label, "value": value})
                    seen_pairs.add(pair_key)
                pending_label = ""
            else:
                pending_label = label
            continue

        if pending_label:
            key = _normalize_field_key(pending_label)
            pair_key = (pending_label, line)
            if pair_key not in seen_pairs:
                fields.append({"key": key, "label": pending_label, "value": line})
                seen_pairs.add(pair_key)
            pending_label = ""

    return fields, _dedupe_strings(links)


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = value.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _extract_username(payload: dict[str, Any], fields: list[dict[str, str]], stdout: str) -> str:
    requested_username = str(payload.get("username", "")).strip()
    if requested_username:
        return requested_username

    for field in fields:
        key = field.get("key", "")
        if key in {"username", "remarks", "client_name", "user"}:
            candidate = field.get("value", "").strip()
            if candidate:
                return candidate

    match = re.search(
        r"(?:Username|Remarks|Client\s*Name|Client)\s*:\s*([A-Za-z0-9_.\-]+)",
        _strip_ansi(stdout),
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()

    return ""


def _read_panel_domain() -> str:
    path = Path("/etc/xray/domain")
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore").strip()


def _resolve_artifacts(protocol: str, username: str) -> list[dict[str, str]]:
    patterns = ARTIFACT_PATTERNS.get(protocol, [])
    domain = _read_panel_domain()
    artifacts: list[dict[str, str]] = []

    for pattern in patterns:
        artifact_path = Path(pattern.format(username=username))
        if not artifact_path.exists() or not artifact_path.is_file():
            continue

        item: dict[str, str] = {
            "path": str(artifact_path),
            "filename": artifact_path.name,
        }
        if domain:
            item["url"] = f"https://{domain}:81/{artifact_path.name}"
        artifacts.append(item)

    return artifacts


def _build_result_details(
    operation: str,
    protocol: str,
    payload: dict[str, Any],
    stdout: str,
) -> dict[str, Any]:
    fields, links = _extract_fields_and_links(stdout)
    username = _extract_username(payload, fields, stdout)

    artifacts: list[dict[str, str]] = []
    if username and operation in {"create", "trial"}:
        artifacts = _resolve_artifacts(protocol, username)
        links.extend(item.get("url", "") for item in artifacts)

    return {
        "username": username,
        "fields": fields[:60],
        "links": _dedupe_strings(links)[:20],
        "artifacts": artifacts,
    }


@dataclass
class MutationResult:
    operation: str
    protocol: str
    script_name: str
    username: str
    returncode: int
    stdout_tail: str
    stderr_tail: str
    details: dict[str, Any]


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
        raise MutationError(
            "Operation tidak valid. Gunakan create, renew, delete, trial, suspend, atau unsuspend."
        )
    if protocol not in SUPPORTED_PROTOCOLS:
        raise MutationError("Protocol tidak valid.")

    protocol_scripts = SCRIPT_NAME_MAP.get(protocol, {})
    if operation not in protocol_scripts:
        raise MutationError("Operation tidak didukung untuk service ini.")

    script_name = protocol_scripts[operation]
    script_path = Path(script_root) / script_name
    if not script_path.exists():
        raise MutationError(f"Script tidak ditemukan: {script_path}")

    stdin_data = _build_stdin(operation, protocol, payload)
    script_args = _build_script_args(operation, payload)
    username = str(payload.get("username", "")).strip()

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
                    ["bash", str(script_path), *script_args],
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

    details = _build_result_details(
        operation=operation,
        protocol=protocol,
        payload=payload,
        stdout=completed.stdout or "",
    )
    resolved_username = details.get("username", "") or username

    result = MutationResult(
        operation=operation,
        protocol=protocol,
        script_name=script_name,
        username=resolved_username,
        returncode=completed.returncode,
        stdout_tail=_tail_lines(completed.stdout or ""),
        stderr_tail=_tail_lines(completed.stderr or ""),
        details=details,
    )

    audit_row = {
        **audit_context,
        "username": result.username,
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
