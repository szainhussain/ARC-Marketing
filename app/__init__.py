from flask import Flask

from app.api.error_handlers import register_error_handlers
from app.config import get_config
from app.extensions import cors, csrf, db, limiter, login_manager, migrate
from app.logging_config import configure_logging


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    hops = app.config.get("TRUSTED_PROXY_HOPS", 0)
    if hops:
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=hops, x_proto=1, x_host=0)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGINS"]}},
        supports_credentials=True,
    )

    configure_logging(app)

    if app.config.get("SENTRY_DSN"):
        try:
            import sentry_sdk

            # No request bodies or user details: they can hold client content.
            sentry_sdk.init(dsn=app.config["SENTRY_DSN"], send_default_pii=False, traces_sample_rate=0.0,
                            environment="production" if app.config.get("IS_PRODUCTION") else "development")
        except ImportError:  # pragma: no cover
            app.logger.warning("SENTRY_DSN is set but sentry-sdk is not installed.")

    from app.models.user import User

    @login_manager.user_loader
    def load_user(session_id: str):
        from app.extensions import db as _db

        user_id, _, version = session_id.partition(":")
        user = _db.session.get(User, user_id)
        if user is None or not user.is_active_account:
            return None
        if str(user.session_version or 1) != (version or "1"):
            return None  # session was revoked
        return user

    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import jsonify

        return jsonify({"error": {"code": "AUTHENTICATION_ERROR", "message": "Sign in required."}}), 401

    from app.api.v1 import api_v1

    app.register_blueprint(api_v1)

    register_error_handlers(app)

    @app.after_request
    def _security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    from app.cli import register_cli

    register_cli(app)

    return app
