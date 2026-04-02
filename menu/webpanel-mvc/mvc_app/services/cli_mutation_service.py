from __future__ import annotations

import base64
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import shutil
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
        "suspend": "suspssh",
        "unsuspend": "unsuspssh",
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
        "suspend": "suspss",
        "unsuspend": "unsuspss",
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

STDERR_NOISE_PATTERNS = [
    re.compile(r"^job-working-directory: error retrieving current directory", re.IGNORECASE),
    re.compile(r"^shell-init: error retrieving current directory", re.IGNORECASE),
    re.compile(r"getcwd: cannot access parent directories", re.IGNORECASE),
    re.compile(r"^/root/\.profile: line \d+: mesg: command not found", re.IGNORECASE),
]

QR_CHARS = {" ", "█", "▀", "▄"}
XRAY_PROTOCOLS = {"vmess", "vless", "trojan", "shadowsocks"}
XRAY_SNAPSHOT_DB_FILES = [
    "/etc/vmess/.vmess.db",
    "/etc/vless/.vless.db",
    "/etc/trojan/.trojan.db",
    "/etc/shadowsocks/.shadowsocks.db",
]
SSH_SNAPSHOT_DB_FILES = ["/etc/ssh/.ssh.db"]


def _safe_snapshot_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "")).strip("-")
    if not cleaned:
        return "anon"
    return cleaned[:64]


def _build_snapshot_targets(protocol: str, xray_config_path: str) -> list[str]:
    if protocol in XRAY_PROTOCOLS:
        return [xray_config_path, *XRAY_SNAPSHOT_DB_FILES]
    if protocol == "ssh":
        return SSH_SNAPSHOT_DB_FILES.copy()
    return []


def _create_snapshot(
    *,
    protocol: str,
    operation: str,
    username: str,
    snapshot_root: str,
    xray_config_path: str,
) -> dict[str, Any]:
    root = Path(snapshot_root)
    root.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_username = _safe_snapshot_name(username)
    snapshot_id = f"{timestamp}-{protocol}-{operation}-{safe_username}"
    snapshot_dir = root / snapshot_id

    suffix = 1
    while snapshot_dir.exists():
        snapshot_dir = root / f"{snapshot_id}-{suffix}"
        suffix += 1

    snapshot_dir.mkdir(parents=True, exist_ok=False)

    entries: list[dict[str, str]] = []
    for source_text in _build_snapshot_targets(protocol, xray_config_path):
        source = Path(source_text)
        if not source.exists() or not source.is_file():
            continue

        safe_name = source.as_posix().strip("/").replace("/", "__")
        backup = snapshot_dir / f"{len(entries) + 1:02d}__{safe_name}"
        shutil.copy2(source, backup)
        entries.append(
            {
                "source": str(source),
                "backup": str(backup),
            }
        )

    return {
        "id": snapshot_dir.name,
        "path": str(snapshot_dir),
        "entries": entries,
    }


def _restore_snapshot(snapshot: dict[str, Any]) -> tuple[bool, list[str]]:
    entries = list(snapshot.get("entries") or [])
    if not entries:
        return True, []

    errors: list[str] = []
    for item in entries:
        source = Path(str(item.get("source", "")))
        backup = Path(str(item.get("backup", "")))

        if not backup.exists() or not backup.is_file():
            errors.append(f"backup hilang: {backup}")
            continue

        try:
            source.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, source)
        except OSError as exc:
            errors.append(f"restore gagal untuk {source}: {exc}")

    return len(errors) == 0, errors


def _run_xray_test(
    *,
    xray_binary_path: str,
    xray_config_path: str,
    timeout_seconds: int,
) -> None:
    binary = str(xray_binary_path or "xray").strip() or "xray"
    if "/" in binary and not Path(binary).exists():
        raise MutationError(f"Binary xray tidak ditemukan: {binary}")

    try:
        completed = subprocess.run(
            [binary, "-test", "-config", xray_config_path],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except OSError as exc:
        raise MutationError(f"Gagal menjalankan preflight xray: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise MutationError("Preflight xray timeout.") from exc

    if completed.returncode != 0:
        reason = _tail_lines(_filter_stderr_noise(completed.stderr or ""), max_lines=12)
        if not reason:
            reason = _tail_lines(completed.stdout or "", max_lines=12)
        detail = f" ({reason})" if reason else ""
        raise MutationError(f"Preflight xray config gagal{detail}")


def _restart_xray_service(timeout_seconds: int) -> None:
    try:
        restart = subprocess.run(
            ["systemctl", "restart", "xray"],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except OSError as exc:
        raise MutationError(f"Gagal restart service xray: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise MutationError("Restart service xray timeout.") from exc

    if restart.returncode != 0:
        detail = _tail_lines(_filter_stderr_noise(restart.stderr or ""), max_lines=10)
        raise MutationError(
            f"Restart service xray gagal{f' ({detail})' if detail else ''}"
        )

    status = subprocess.run(
        ["systemctl", "is-active", "xray"],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_seconds,
    )
    if status.returncode != 0:
        state = (status.stdout or status.stderr or "unknown").strip() or "unknown"
        raise MutationError(f"Service xray tidak aktif setelah restart ({state}).")


def _postcheck_xray_runtime(
    *,
    xray_binary_path: str,
    xray_config_path: str,
    timeout_seconds: int,
) -> None:
    _run_xray_test(
        xray_binary_path=xray_binary_path,
        xray_config_path=xray_config_path,
        timeout_seconds=timeout_seconds,
    )
    _restart_xray_service(timeout_seconds=timeout_seconds)


def _attempt_rollback(
    *,
    snapshot: dict[str, Any] | None,
    protocol: str,
    xray_binary_path: str,
    xray_config_path: str,
    timeout_seconds: int,
) -> tuple[bool, str]:
    if not snapshot:
        return False, "snapshot tidak tersedia"

    restored, errors = _restore_snapshot(snapshot)
    if protocol in XRAY_PROTOCOLS:
        try:
            _postcheck_xray_runtime(
                xray_binary_path=xray_binary_path,
                xray_config_path=xray_config_path,
                timeout_seconds=timeout_seconds,
            )
        except MutationError as exc:
            restored = False
            errors.append(str(exc))

    if restored:
        return True, "rollback selesai"

    return False, "; ".join(errors) if errors else "rollback gagal"


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
        lines = [username, str(days), str(max(0, quota_gb)), str(max(0, ip_limit))]
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
        ip_limit = _safe_int(payload.get("ip_limit"), 0)
        return f"{username}\n{days}\n{max(0, ip_limit)}\n"

    if protocol == "shadowsocks":
        ip_limit = _safe_int(payload.get("ip_limit"), 0)
        return f"{username}\n{days}\n{max(0, ip_limit)}\n"

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


def _filter_stderr_noise(text: str) -> str:
    rows: list[str] = []
    for raw_line in _strip_ansi(text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if any(pattern.search(line) for pattern in STDERR_NOISE_PATTERNS):
            continue
        rows.append(raw_line)
    return "\n".join(rows).strip()


def _is_qr_ascii_line(line: str) -> bool:
    if not line:
        return False
    chars = set(line)
    if not chars.issubset(QR_CHARS):
        return False
    return any(char in {"█", "▀", "▄"} for char in chars)


def _extract_ascii_qr_lines(text: str) -> list[str]:
    best: list[str] = []
    current: list[str] = []

    for raw_line in _strip_ansi(text).splitlines():
        line = raw_line.rstrip()
        if _is_qr_ascii_line(line):
            current.append(line)
            continue

        if len(current) > len(best):
            best = current.copy()
        current = []

    if len(current) > len(best):
        best = current.copy()

    if len(best) < 12:
        return []

    width = max(len(line) for line in best)
    return [line.ljust(width, " ") for line in best]


def _trim_qr_matrix(matrix: list[list[int]]) -> list[list[int]]:
    if not matrix or not matrix[0]:
        return matrix

    top = 0
    bottom = len(matrix)
    left = 0
    right = len(matrix[0])

    while top < bottom and not any(matrix[top]):
        top += 1
    while bottom > top and not any(matrix[bottom - 1]):
        bottom -= 1

    while left < right and not any(row[left] for row in matrix[top:bottom]):
        left += 1
    while right > left and not any(row[right - 1] for row in matrix[top:bottom]):
        right -= 1

    return [row[left:right] for row in matrix[top:bottom]]


def _ascii_qr_to_svg_data_uri(lines: list[str]) -> str:
    if not lines:
        return ""

    matrix: list[list[int]] = []
    for line in lines:
        upper_row: list[int] = []
        lower_row: list[int] = []
        for char in line:
            if char == "█":
                upper_row.append(1)
                lower_row.append(1)
            elif char == "▀":
                upper_row.append(1)
                lower_row.append(0)
            elif char == "▄":
                upper_row.append(0)
                lower_row.append(1)
            else:
                upper_row.append(0)
                lower_row.append(0)
        matrix.append(upper_row)
        matrix.append(lower_row)

    matrix = _trim_qr_matrix(matrix)
    if not matrix or not matrix[0]:
        return ""

    module = 6
    margin = 3
    height = len(matrix)
    width = len(matrix[0])
    svg_width = (width + (margin * 2)) * module
    svg_height = (height + (margin * 2)) * module

    rects: list[str] = []
    for y, row in enumerate(matrix):
        for x, value in enumerate(row):
            if value:
                rects.append(
                    f'<rect x="{(x + margin) * module}" y="{(y + margin) * module}" width="{module}" height="{module}" />'
                )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width}" height="{svg_height}" '
        f'viewBox="0 0 {svg_width} {svg_height}">'
        f'<rect width="{svg_width}" height="{svg_height}" fill="#ffffff" />'
        f'<g fill="#111111">{"".join(rects)}</g>'
        "</svg>"
    )
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


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
    normalized_links = _dedupe_strings(links)

    artifacts: list[dict[str, str]] = []
    if username and operation in {"create", "trial"}:
        artifacts = _resolve_artifacts(protocol, username)
        normalized_links.extend(item.get("url", "") for item in artifacts)

    qr_lines = _extract_ascii_qr_lines(stdout)
    qr_images: list[dict[str, str]] = []
    qr_inline_svg = _ascii_qr_to_svg_data_uri(qr_lines)
    if qr_inline_svg:
        qr_images.append(
            {
                "label": "QR dari output script",
                "source": "stdout_ascii",
                "image": qr_inline_svg,
            }
        )

    normalized_links = _dedupe_strings(normalized_links)

    return {
        "username": username,
        "fields": fields[:60],
        "links": normalized_links[:20],
        "artifacts": artifacts,
        "qr_payloads": normalized_links[:8],
        "qr_images": qr_images,
    }


def get_account_config_details(protocol: str, username: str) -> dict[str, Any]:
    normalized_protocol = str(protocol or "").strip().lower()
    if normalized_protocol not in SUPPORTED_PROTOCOLS:
        raise MutationError("Protocol tidak valid.")

    normalized_username = str(username or "").strip()
    if not normalized_username:
        raise MutationError("Username tidak valid.")

    artifacts = _resolve_artifacts(normalized_protocol, normalized_username)
    if not artifacts:
        raise MutationError("File konfigurasi akun belum ditemukan.")

    files: list[dict[str, Any]] = []
    links: list[str] = []
    qr_images: list[dict[str, str]] = []

    for artifact in artifacts:
        path = Path(artifact.get("path", ""))
        if not path.exists() or not path.is_file():
            continue

        content = path.read_text(encoding="utf-8", errors="ignore")
        cleaned_content = _strip_ansi(content)
        file_links = LINK_RE.findall(cleaned_content)
        links.extend(file_links)

        qr_lines = _extract_ascii_qr_lines(cleaned_content)
        qr_inline_svg = _ascii_qr_to_svg_data_uri(qr_lines)
        if qr_inline_svg:
            qr_images.append(
                {
                    "label": f"QR {artifact.get('filename', 'config')}",
                    "source": "artifact_ascii",
                    "image": qr_inline_svg,
                }
            )

        clipped = cleaned_content
        truncated = False
        if len(clipped) > 20000:
            clipped = clipped[:20000] + "\n\n... [truncated by web panel]"
            truncated = True

        files.append(
            {
                "filename": artifact.get("filename", path.name),
                "path": str(path),
                "content": clipped,
                "truncated": truncated,
            }
        )

    normalized_links = _dedupe_strings(links)
    return {
        "protocol": normalized_protocol,
        "username": normalized_username,
        "artifacts": artifacts,
        "files": files,
        "links": normalized_links,
        "qr_payloads": normalized_links[:8],
        "qr_images": qr_images,
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
    mutation_safety_enabled: bool = True,
    mutation_snapshot_dir: str = "/etc/xray/backup-webpanel",
    xray_binary_path: str = "/usr/bin/xray",
    xray_config_path: str = "/etc/xray/config.json",
    mutation_postcheck_timeout_seconds: int = 25,
    mutation_precheck_xray: bool = True,
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
    safety_enabled = bool(mutation_safety_enabled)
    postcheck_timeout = max(5, int(mutation_postcheck_timeout_seconds))

    safety_details: dict[str, Any] = {
        "enabled": safety_enabled,
        "preflight_ok": False,
        "postcheck_ok": False,
        "snapshot_id": "",
        "snapshot_dir": "",
        "snapshot_files": [],
        "rollback_performed": False,
        "rollback_status": "not-needed",
        "rollback_reason": "",
        "rollback_error": "",
    }
    snapshot: dict[str, Any] | None = None

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
            if safety_enabled:
                if protocol in XRAY_PROTOCOLS and mutation_precheck_xray:
                    _run_xray_test(
                        xray_binary_path=xray_binary_path,
                        xray_config_path=xray_config_path,
                        timeout_seconds=postcheck_timeout,
                    )
                    safety_details["preflight_ok"] = True

                snapshot = _create_snapshot(
                    protocol=protocol,
                    operation=operation,
                    username=username,
                    snapshot_root=mutation_snapshot_dir,
                    xray_config_path=xray_config_path,
                )
                safety_details["snapshot_id"] = str(snapshot.get("id", ""))
                safety_details["snapshot_dir"] = str(snapshot.get("path", ""))
                safety_details["snapshot_files"] = [
                    str(item.get("source", ""))
                    for item in snapshot.get("entries", [])
                    if str(item.get("source", "")).strip()
                ]

            with _shim_bin_dir() as shim_dir:
                base_env = os.environ.copy()
                default_path = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
                inherited_path = base_env.get("PATH", "").strip()
                effective_path = inherited_path or default_path
                if "/usr/bin" not in effective_path:
                    effective_path = f"{effective_path}:{default_path}"
                base_env["PATH"] = f"{shim_dir}:{script_root}:{effective_path}"
                base_env.setdefault("TERM", "dumb")

                run_cwd = script_root if Path(script_root).is_dir() else "/"

                completed = subprocess.run(
                    ["bash", str(script_path), *script_args],
                    input=stdin_data,
                    capture_output=True,
                    text=True,
                    timeout=command_timeout_seconds,
                    check=False,
                    env=base_env,
                    cwd=run_cwd,
                )
    except MutationError as exc:
        append_audit_log(
            audit_log_path,
            {
                **audit_context,
                "status": "safety_failed",
                "error": str(exc),
                "safety": safety_details,
            },
        )
        raise
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

    final_error_message = ""
    if completed.returncode != 0:
        final_error_message = "Eksekusi script gagal. Cek audit log untuk detail terakhir."
        if safety_enabled:
            rollback_ok, rollback_info = _attempt_rollback(
                snapshot=snapshot,
                protocol=protocol,
                xray_binary_path=xray_binary_path,
                xray_config_path=xray_config_path,
                timeout_seconds=postcheck_timeout,
            )
            safety_details["rollback_performed"] = True
            safety_details["rollback_reason"] = "script_failed"
            safety_details["rollback_status"] = "success" if rollback_ok else "failed"
            if not rollback_ok:
                safety_details["rollback_error"] = rollback_info
                final_error_message = f"{final_error_message} Rollback gagal: {rollback_info}"
            else:
                final_error_message = f"{final_error_message} Rollback otomatis berhasil."

    if not final_error_message and safety_enabled and protocol in XRAY_PROTOCOLS:
        try:
            _postcheck_xray_runtime(
                xray_binary_path=xray_binary_path,
                xray_config_path=xray_config_path,
                timeout_seconds=postcheck_timeout,
            )
            safety_details["postcheck_ok"] = True
        except MutationError as exc:
            final_error_message = str(exc)
            rollback_ok, rollback_info = _attempt_rollback(
                snapshot=snapshot,
                protocol=protocol,
                xray_binary_path=xray_binary_path,
                xray_config_path=xray_config_path,
                timeout_seconds=postcheck_timeout,
            )
            safety_details["rollback_performed"] = True
            safety_details["rollback_reason"] = "postcheck_failed"
            safety_details["rollback_status"] = "success" if rollback_ok else "failed"
            if not rollback_ok:
                safety_details["rollback_error"] = rollback_info
                final_error_message = f"{final_error_message} Rollback gagal: {rollback_info}"
            else:
                final_error_message = f"{final_error_message} Rollback otomatis berhasil."

    details = _build_result_details(
        operation=operation,
        protocol=protocol,
        payload=payload,
        stdout=completed.stdout or "",
    )
    details["safety"] = safety_details
    resolved_username = details.get("username", "") or username

    effective_returncode = completed.returncode
    if final_error_message and effective_returncode == 0:
        effective_returncode = 1

    result = MutationResult(
        operation=operation,
        protocol=protocol,
        script_name=script_name,
        username=resolved_username,
        returncode=effective_returncode,
        stdout_tail=_tail_lines(completed.stdout or ""),
        stderr_tail=_tail_lines(_filter_stderr_noise(completed.stderr or "")),
        details=details,
    )

    audit_row = {
        **audit_context,
        "username": result.username,
        "status": "success" if result.returncode == 0 and not final_error_message else "failed",
        "returncode": result.returncode,
        "stdout_tail": result.stdout_tail,
        "stderr_tail": result.stderr_tail,
        "safety": safety_details,
    }
    append_audit_log(audit_log_path, audit_row)

    if final_error_message:
        raise MutationError(final_error_message)

    if result.returncode != 0:
        raise MutationError("Eksekusi script gagal. Cek audit log untuk detail terakhir.")

    return result
