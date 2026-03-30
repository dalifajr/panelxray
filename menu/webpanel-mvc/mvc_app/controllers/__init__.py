from datetime import datetime, timezone
from functools import wraps

from flask import jsonify, redirect, request, session, url_for


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("authenticated"):
            is_api_request = (
                request.blueprint == "api"
                or request.path.startswith("/api")
                or "/api/" in request.path
            )
            if is_api_request:
                return (
                    jsonify(
                        {
                            "ok": False,
                            "message": "Sesi login habis. Silakan login ulang.",
                            "checked_at": datetime.now(timezone.utc).isoformat(),
                        }
                    ),
                    401,
                )
            return redirect(url_for("auth.login_form"))
        return view(*args, **kwargs)

    return wrapped_view
