from flask import Flask, request

from .config import Settings
from .controllers.api_controller import api_bp
from .controllers.auth_controller import auth_bp
from .controllers.dashboard_controller import dashboard_bp
from .middleware import ProxyPrefixMiddleware


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="views/templates",
        static_folder="views/static",
    )
    app.config.from_object(Settings)
    app.wsgi_app = ProxyPrefixMiddleware(app.wsgi_app)

    @app.context_processor
    def inject_template_globals() -> dict[str, str]:
        return {
            "asset_version": str(
                app.config.get("WEB_PANEL_ASSET_VERSION", "1")
            )
        }

    @app.after_request
    def apply_no_cache_headers(response):
        static_prefix = app.static_url_path or "/static"
        if request.path.startswith(static_prefix):
            return response

        if response.mimetype in {"text/html", "application/json"}:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)

    return app
