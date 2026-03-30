from datetime import datetime, timezone

from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from . import login_required
from ..models.account_model import load_accounts, summarize_accounts
from ..models.service_model import (
    get_default_service_key,
    get_service_catalog,
    get_service_definition,
    get_service_protocols,
    get_service_status,
    normalize_service_key,
)

dashboard_bp = Blueprint("dashboard", __name__)


def _build_workspace_initial_payload(context: dict[str, object]) -> dict[str, object]:
    return {
        "operator": context.get("operator", "admin"),
        "summary": context.get("summary", {}),
        "services": context.get("services", {}),
        "accounts": context.get("accounts", []),
        "service_catalog": context.get("service_catalog", []),
        "active_service_key": context.get("active_service_key", get_default_service_key()),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_protocol_operation_catalog(service_key: str) -> dict[str, list[dict[str, object]]]:
    catalog: dict[str, list[dict[str, object]]] = {}
    for protocol_key in get_service_protocols(service_key):
        profile = get_service_definition(protocol_key)
        if not profile:
            continue
        catalog[protocol_key] = profile.get("operations", [])

    if service_key not in catalog:
        active_profile = get_service_definition(service_key)
        if active_profile:
            catalog[service_key] = active_profile.get("operations", [])

    return catalog


def _build_service_context(service_key: str) -> dict[str, object]:
    accounts = load_accounts(current_app.config["XRAY_CONFIG_PATH"])
    summary = summarize_accounts(accounts)
    services = get_service_status()
    service_catalog = get_service_catalog()
    active_service = get_service_definition(service_key)

    service_protocols = set(get_service_protocols(service_key))
    filtered_accounts = [
        row for row in accounts if row.get("protocol") in service_protocols
    ]

    return {
        "operator": session.get("operator", "admin"),
        "audit_log_path": current_app.config["AUDIT_LOG_PATH"],
        "summary": summary,
        "services": services,
        "accounts": filtered_accounts,
        "active_service_key": service_key,
        "active_service": active_service,
        "service_catalog": service_catalog,
        "protocol_operation_catalog": _build_protocol_operation_catalog(service_key),
    }


@dashboard_bp.get("/")
def index():
    if session.get("authenticated"):
        return redirect(
            url_for(
                "dashboard.workspace",
                service=get_default_service_key(),
            )
        )
    return redirect(url_for("auth.login_form"))


@dashboard_bp.get("/dashboard")
@login_required
def dashboard():
    return redirect(
        url_for(
            "dashboard.workspace",
            service=get_default_service_key(),
        )
    )


@dashboard_bp.get("/workspace")
@login_required
def workspace_default():
    return redirect(
        url_for(
            "dashboard.workspace",
            service=get_default_service_key(),
        )
    )


@dashboard_bp.get("/workspace/<service>")
@login_required
def workspace(service: str):
    service_key = normalize_service_key(service)
    if not service_key:
        abort(404)

    context = _build_service_context(service_key)
    return render_template(
        "workspace_m3.html",
        page_title="VPNXRay Workspace",
        page_subtitle="Material You 3 expressive workspace untuk monitoring dan manajemen akun.",
        current_view="workspace",
        workspace_initial=_build_workspace_initial_payload(context),
        **context,
    )


@dashboard_bp.get("/dashboard/<service>")
@login_required
def service_dashboard(service: str):
    service_key = normalize_service_key(service)
    if not service_key:
        abort(404)

    return render_template(
        "dashboard.html",
        page_title="VPNXRay Dashboard",
        page_subtitle="Ringkasan service dan shortcut manajemen akun.",
        current_view="dashboard",
        **_build_service_context(service_key),
    )


@dashboard_bp.get("/dashboard/<service>/accounts")
@login_required
def manage_accounts(service: str):
    service_key = normalize_service_key(service)
    if not service_key:
        abort(404)

    return render_template(
        "accounts_manage.html",
        page_title="Manajemen Akun",
        page_subtitle="Cari akun, buka detail konfigurasi, lalu jalankan aksi dari popup.",
        current_view="accounts",
        **_build_service_context(service_key),
    )


@dashboard_bp.get("/dashboard/<service>/result")
@login_required
def service_result_page(service: str):
    service_key = normalize_service_key(service)
    if not service_key:
        abort(404)

    expected_operation = str(request.args.get("operation", "")).strip().lower()
    expected_username = str(request.args.get("username", "")).strip()
    expected_protocol = normalize_service_key(request.args.get("protocol", "")) or ""

    if service_key != "xray":
        expected_protocol = service_key
    elif expected_protocol not in set(get_service_protocols(service_key)):
        expected_protocol = ""

    return render_template(
        "mutation_result.html",
        page_title="Hasil Mutasi Akun",
        page_subtitle="Status pembuatan akun dan detail konfigurasi ditampilkan di halaman ini.",
        current_view="result",
        expected_operation=expected_operation,
        expected_username=expected_username,
        expected_protocol=expected_protocol,
        **_build_service_context(service_key),
    )
