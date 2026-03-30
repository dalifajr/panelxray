from datetime import datetime, timezone
import re
from typing import Any

from flask import Blueprint, current_app, jsonify, request, session
from werkzeug.exceptions import HTTPException

from . import login_required
from ..models.account_model import load_accounts, summarize_accounts
from ..models.service_model import (
    get_service_catalog,
    get_service_definition,
    get_service_protocols,
    get_service_status,
    normalize_service_key,
)
from ..services import MutationError, get_account_config_details, run_cli_mutation

api_bp = Blueprint("api", __name__, url_prefix="/api")

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


def _load_all_accounts() -> list[dict[str, str]]:
    return load_accounts(current_app.config["XRAY_CONFIG_PATH"])


def _filter_accounts_by_service(
    rows: list[dict[str, str]], service_key: str
) -> list[dict[str, str]]:
    protocols = set(get_service_protocols(service_key))
    return [row for row in rows if row.get("protocol") in protocols]


def _allowed_operations(service_key: str) -> set[str]:
    profile = get_service_definition(service_key)
    if not profile:
        return set()
    return {item.get("name", "") for item in profile.get("operations", [])}


def _operation_schema(service_key: str, operation_name: str) -> dict[str, Any] | None:
    profile = get_service_definition(service_key)
    if not profile:
        return None

    normalized_operation = str(operation_name or "").strip().lower()
    for item in profile.get("operations", []):
        name = str(item.get("name", "")).strip().lower()
        if name == normalized_operation:
            return item

    return None


def _parse_payload() -> dict[str, Any]:
    payload = request.get_json(silent=True)
    if payload is None:
        return {}

    if not isinstance(payload, dict):
        raise MutationError("Payload JSON harus berbentuk object.")

    return payload


def _sanitize_field(field: dict[str, Any], payload: dict[str, Any]) -> tuple[bool, Any]:
    field_name = str(field.get("name", "")).strip()
    if not field_name:
        return False, None

    field_label = str(field.get("label") or field_name)
    required = bool(field.get("required"))
    field_type = str(field.get("type", "text")).strip().lower()

    exists = field_name in payload
    raw_value = payload.get(field_name)

    if (raw_value is None or str(raw_value).strip() == "") and "value" in field:
        raw_value = field.get("value")
        exists = True

    if raw_value is None or str(raw_value).strip() == "":
        if required:
            raise MutationError(f"Field {field_label} wajib diisi.")
        return False, None

    if field_type == "number":
        try:
            number_value = int(str(raw_value).strip())
        except (TypeError, ValueError) as exc:
            raise MutationError(f"Field {field_label} harus berupa angka.") from exc

        min_value = field.get("min")
        if min_value is not None:
            min_number = int(min_value)
            if number_value < min_number:
                raise MutationError(
                    f"Field {field_label} minimal bernilai {min_number}."
                )

        return True, number_value

    text_value = str(raw_value).strip()
    if required and not text_value:
        raise MutationError(f"Field {field_label} wajib diisi.")

    if field_name == "username" and not USERNAME_RE.fullmatch(text_value):
        raise MutationError(
            "Username hanya boleh berisi huruf, angka, titik, underscore, atau strip (maks 64 karakter)."
        )

    if field_type == "select":
        valid_options = {
            str(item.get("value", "")).strip()
            for item in field.get("options", [])
            if str(item.get("value", "")).strip()
        }
        if valid_options and text_value not in valid_options:
            raise MutationError(f"Pilihan untuk {field_label} tidak valid.")

    return exists, text_value


def _sanitize_payload_for_operation(
    service_key: str,
    operation_name: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    schema = _operation_schema(service_key, operation_name)
    if not schema:
        return {}

    sanitized: dict[str, Any] = {}
    for field in schema.get("fields", []):
        is_set, value = _sanitize_field(field, payload)
        if not is_set:
            continue
        field_name = str(field.get("name", "")).strip()
        if field_name:
            sanitized[field_name] = value

    return sanitized


def _build_error_response(message: str, status_code: int = 400):
    return (
        jsonify(
            {
                "ok": False,
                "message": message,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
        ),
        status_code,
    )


@api_bp.errorhandler(404)
def _api_not_found(_error):
    return _build_error_response("Endpoint API tidak ditemukan.", 404)


@api_bp.errorhandler(405)
def _api_method_not_allowed(_error):
    return _build_error_response("Metode HTTP tidak didukung untuk endpoint ini.", 405)


@api_bp.errorhandler(Exception)
def _api_unhandled_error(error):
    if isinstance(error, HTTPException):
        return _build_error_response(
            error.description or "Terjadi error pada API.",
            error.code or 500,
        )

    current_app.logger.exception(
        "Unhandled API error on %s %s",
        request.method,
        request.path,
    )
    return _build_error_response("Terjadi error internal saat memproses API.", 500)


def _run_mutation(
    *,
    protocol: str,
    operation: str,
    payload: dict[str, object],
):
    operator = session.get("operator", "admin")
    return run_cli_mutation(
        operation=operation,
        protocol=protocol,
        payload=payload,
        operator=operator,
        script_root=current_app.config["CLI_SCRIPT_ROOT"],
        lock_file=current_app.config["MUTATION_LOCK_FILE"],
        lock_timeout_seconds=current_app.config["MUTATION_LOCK_TIMEOUT_SEC"],
        command_timeout_seconds=current_app.config["CLI_MUTATION_TIMEOUT_SEC"],
        audit_log_path=current_app.config["AUDIT_LOG_PATH"],
        mutation_safety_enabled=bool(
            current_app.config.get("MUTATION_SAFETY_ENABLED", True)
        ),
        mutation_snapshot_dir=str(
            current_app.config.get(
                "MUTATION_SNAPSHOT_DIR",
                "/etc/xray/backup-webpanel",
            )
        ),
        xray_binary_path=str(
            current_app.config.get("XRAY_BINARY_PATH", "/usr/bin/xray")
        ),
        xray_config_path=str(
            current_app.config.get("XRAY_CONFIG_PATH", "/etc/xray/config.json")
        ),
        mutation_postcheck_timeout_seconds=int(
            current_app.config.get("MUTATION_POSTCHECK_TIMEOUT_SEC", 25)
        ),
        mutation_precheck_xray=bool(
            current_app.config.get("MUTATION_PRECHECK_XRAY", True)
        ),
    )


def _build_mutation_success_response(result):
    return jsonify(
        {
            "ok": True,
            "message": "Mutasi berhasil diproses.",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "result": {
                "operation": result.operation,
                "protocol": result.protocol,
                "script": result.script_name,
                "username": result.username,
                "stdout_tail": result.stdout_tail,
                "stderr_tail": result.stderr_tail,
                "details": result.details,
            },
        }
    )


@api_bp.get("/health")
def health():
    statuses = get_service_status()
    active = sum(1 for status in statuses.values() if status == "active")
    total = len(statuses)

    state = "healthy" if total > 0 and active >= total - 1 else "degraded"
    return jsonify(
        {
            "status": state,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "services": statuses,
            "asset_version": str(
                current_app.config.get("WEB_PANEL_ASSET_VERSION", "1")
            ),
        }
    )


@api_bp.get("/accounts")
@login_required
def accounts():
    rows = _load_all_accounts()
    return jsonify(rows)


@api_bp.get("/stats")
@login_required
def stats():
    rows = _load_all_accounts()
    summary = summarize_accounts(rows)
    statuses = get_service_status()

    return jsonify(
        {
            "accounts": summary,
            "services": statuses,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@api_bp.get("/services")
@login_required
def service_catalog():
    return jsonify(get_service_catalog())


@api_bp.get("/services/<service>/accounts")
@login_required
def service_accounts(service: str):
    service_key = normalize_service_key(service)
    if not service_key:
        return _build_error_response("Service tidak ditemukan.", 404)

    rows = _load_all_accounts()
    return jsonify(_filter_accounts_by_service(rows, service_key))


@api_bp.get("/services/<service>/accounts/<username>/config")
@login_required
def service_account_config(service: str, username: str):
    service_key = normalize_service_key(service)
    if not service_key:
        return _build_error_response("Service tidak ditemukan.", 404)

    normalized_username = str(username or "").strip()
    if not normalized_username:
        return _build_error_response("Username tidak valid.")

    protocol = service_key
    if service_key == "xray":
        protocol = normalize_service_key(request.args.get("protocol", "")) or ""
        if protocol not in {"vmess", "vless", "trojan", "shadowsocks"}:
            return _build_error_response(
                "Protocol wajib dipilih untuk workspace Xray."
            )

    try:
        snapshot = get_account_config_details(protocol, normalized_username)
    except MutationError as exc:
        return _build_error_response(str(exc), 404)
    except Exception:
        current_app.logger.exception(
            "Failed to load account config for protocol=%s username=%s",
            protocol,
            normalized_username,
        )
        return _build_error_response(
            "Gagal memuat konfigurasi akun karena error internal.",
            500,
        )

    return jsonify(
        {
            "ok": True,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "result": snapshot,
        }
    )


@api_bp.post("/services/<service>/actions/<operation>")
@login_required
def service_action(service: str, operation: str):
    service_key = normalize_service_key(service)
    if not service_key:
        return _build_error_response("Service tidak ditemukan.", 404)

    normalized_operation = str(operation or "").strip().lower()
    allowed_operations = _allowed_operations(service_key)
    if normalized_operation not in allowed_operations:
        return _build_error_response("Operation tidak didukung untuk service ini.")

    try:
        payload = _parse_payload()
    except MutationError as exc:
        return _build_error_response(str(exc))

    try:
        sanitized_payload = _sanitize_payload_for_operation(
            service_key,
            normalized_operation,
            payload,
        )
    except MutationError as exc:
        return _build_error_response(str(exc))

    payload = sanitized_payload
    payload["protocol"] = service_key
    payload["operation"] = normalized_operation

    try:
        result = _run_mutation(
            protocol=service_key,
            operation=normalized_operation,
            payload=payload,
        )
    except MutationError as exc:
        return _build_error_response(str(exc))
    except Exception:
        current_app.logger.exception(
            "Unhandled mutation error for service=%s operation=%s",
            service_key,
            normalized_operation,
        )
        return _build_error_response(
            "Terjadi error internal saat menjalankan mutasi.",
            500,
        )

    return _build_mutation_success_response(result)


@api_bp.post("/mutations")
@login_required
def mutate_accounts():
    try:
        payload = _parse_payload()
    except MutationError as exc:
        return _build_error_response(str(exc))

    operation = str(payload.get("operation", "")).strip().lower()
    protocol = normalize_service_key(payload.get("protocol", ""))

    if not protocol:
        return _build_error_response("Protocol tidak valid.")

    allowed_operations = _allowed_operations(protocol)
    if operation not in allowed_operations:
        return _build_error_response("Operation tidak didukung untuk service ini.")

    try:
        sanitized_payload = _sanitize_payload_for_operation(
            protocol,
            operation,
            payload,
        )
    except MutationError as exc:
        return _build_error_response(str(exc))

    try:
        result = _run_mutation(
            operation=operation,
            protocol=protocol,
            payload={
                **sanitized_payload,
                "operation": operation,
                "protocol": protocol,
            },
        )
    except MutationError as exc:
        return _build_error_response(str(exc))
    except Exception:
        current_app.logger.exception(
            "Unhandled mutation error for protocol=%s operation=%s",
            protocol,
            operation,
        )
        return _build_error_response(
            "Terjadi error internal saat menjalankan mutasi.",
            500,
        )

    return _build_mutation_success_response(result)
