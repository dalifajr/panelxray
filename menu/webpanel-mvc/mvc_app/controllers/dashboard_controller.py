from flask import Blueprint, current_app, redirect, render_template, session, url_for

from . import login_required
from ..models.account_model import load_accounts, summarize_accounts
from ..models.service_model import get_service_status

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/")
def index():
    if session.get("authenticated"):
        return redirect(url_for("dashboard.dashboard"))
    return redirect(url_for("auth.login_form"))


@dashboard_bp.get("/dashboard")
@login_required
def dashboard():
    accounts = load_accounts(current_app.config["XRAY_CONFIG_PATH"])
    summary = summarize_accounts(accounts)
    services = get_service_status()

    return render_template(
        "dashboard.html",
        operator=session.get("operator", "admin"),
        audit_log_path=current_app.config["AUDIT_LOG_PATH"],
        summary=summary,
        services=services,
        accounts=accounts,
    )
