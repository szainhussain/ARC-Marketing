from flask import Flask

from app.api.error_handlers import register_error_handlers
from app.config import get_config
from app.extensions import cors, csrf, db, login_manager, migrate
from app.logging_config import configure_logging


def create_app(config_name: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(get_config(config_name))

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["FRONTEND_ORIGIN"]}},
        supports_credentials=True,
    )

    configure_logging(app)

    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return User.query.get(user_id)

    @login_manager.unauthorized_handler
    def unauthorized():
        from flask import jsonify

        return jsonify({"error": {"code": "AUTHENTICATION_ERROR", "message": "Sign in required."}}), 401

    from app.api.v1 import api_v1

    app.register_blueprint(api_v1)

    register_error_handlers(app)

    return app
