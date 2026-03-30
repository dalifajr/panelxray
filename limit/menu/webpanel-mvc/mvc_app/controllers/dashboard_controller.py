from flask import (
    Blueprint,
    abort,
    current_app,
    redirect,
    render_template,
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


@dashboard_bp.get("/")
def index():
    if session.get("authenticated"):
        return redirect(
            url_for(
                "dashboard.service_dashboard",
                service=get_default_service_key(),
            )
        )
    return redirect(url_for("auth.login_form"))


@dashboard_bp.get("/dashboard")
@login_required
def dashboard():
    return redirect(
        url_for(
            "dashboard.service_dashboard",
            service=get_default_service_key(),
        )
    )


@dashboard_bp.get("/dashboard/<service>")
@login_required
def service_dashboard(service: str):
    service_key = normalize_service_key(service)
    if not service_key:
        abort(404)

    accounts = load_accounts(current_app.config["XRAY_CONFIG_PATH"])
    summary = summarize_accounts(accounts)
    services = get_service_status()
    service_catalog = get_service_catalog()
    active_service = get_service_definition(service_key)

    service_protocols = set(get_service_protocols(service_key))
    filtered_accounts = [
        row for row in accounts if row.get("protocol") in service_protocols
    ]

    return render_template(
        "dashboard.html",
        operator=session.get("operator", "admin"),
        audit_log_path=current_app.config["AUDIT_LOG_PATH"],
        summary=summary,
        services=services,
        accounts=filtered_accounts,
        active_service_key=service_key,
        active_service=active_service,
        service_catalog=service_catalog,
    )
