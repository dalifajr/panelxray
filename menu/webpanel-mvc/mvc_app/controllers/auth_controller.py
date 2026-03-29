from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

from ..models.auth_model import load_panel_credentials

auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/login")
def login_form():
    if session.get("authenticated"):
        return redirect(url_for("dashboard.dashboard"))
    return render_template("login.html", error_message="")


@auth_bp.post("/login")
def login_submit():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")

    expected_username, expected_password = load_panel_credentials(
        current_app.config["PANEL_USER_FILE"],
        current_app.config["PANEL_PASS_FILE"],
    )

    if username == expected_username and password == expected_password:
        session.clear()
        session["authenticated"] = True
        session["operator"] = username
        return redirect(url_for("dashboard.dashboard"))

    return render_template("login.html", error_message="Username atau password salah.")


@auth_bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login_form"))
