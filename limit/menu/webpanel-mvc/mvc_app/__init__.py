from flask import Flask

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

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(api_bp)

    return app
