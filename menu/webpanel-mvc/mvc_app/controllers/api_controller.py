from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request, session

from . import login_required
from ..models.account_model import load_accounts, summarize_accounts
from ..models.service_model import get_service_status
from ..services import MutationError, run_cli_mutation

api_bp = Blueprint("api", __name__, url_prefix="/api")


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
        }
    )


@api_bp.get("/accounts")
@login_required
def accounts():
    rows = load_accounts(current_app.config["XRAY_CONFIG_PATH"])
    return jsonify(rows)


@api_bp.get("/stats")
@login_required
def stats():
    rows = load_accounts(current_app.config["XRAY_CONFIG_PATH"])
    summary = summarize_accounts(rows)
    statuses = get_service_status()

    return jsonify(
        {
            "accounts": summary,
            "services": statuses,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@api_bp.post("/mutations")
@login_required
def mutate_accounts():
    payload = request.get_json(silent=True) or {}
    operation = payload.get("operation", "")
    protocol = payload.get("protocol", "")
    operator = session.get("operator", "admin")

    try:
        result = run_cli_mutation(
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
    except MutationError as exc:
        return (
            jsonify(
                {
                    "ok": False,
                    "message": str(exc),
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                }
            ),
            400,
        )

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
            },
        }
    )
