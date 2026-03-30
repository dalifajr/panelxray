from datetime import datetime, timezone

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

    payload = request.get_json(silent=True) or {}
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
    payload = request.get_json(silent=True) or {}
    operation = str(payload.get("operation", "")).strip().lower()
    protocol = normalize_service_key(payload.get("protocol", ""))

    if not protocol:
        return _build_error_response("Protocol tidak valid.")

    allowed_operations = _allowed_operations(protocol)
    if operation not in allowed_operations:
        return _build_error_response("Operation tidak didukung untuk service ini.")

    try:
        result = _run_mutation(
            operation=operation,
            protocol=protocol,
            payload=payload,
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
