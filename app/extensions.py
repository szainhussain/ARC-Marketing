from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_cors import CORS

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
cors = CORS()

from flask_limiter import Limiter  # noqa: E402
from flask_limiter.util import get_remote_address  # noqa: E402

# Applied per-route to unauthenticated, abuse-prone endpoints (login,
# registration, password reset, contact). Storage is configured via
# RATELIMIT_STORAGE_URI (memory:// locally; use Redis in production).
limiter = Limiter(key_func=get_remote_address, default_limits=[])
