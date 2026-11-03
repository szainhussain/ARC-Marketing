import os


def _bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = _bool_env("SESSION_COOKIE_SECURE", False)
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    WTF_CSRF_TIME_LIMIT = None

    AI_PROVIDER = os.environ.get("AI_PROVIDER", "anthropic")
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    _AI_MODEL_DEFAULTS = {
        "anthropic": "claude-sonnet-5",
        "groq": "openai/gpt-oss-120b",
    }
    AI_MODEL = os.environ.get("AI_MODEL") or _AI_MODEL_DEFAULTS.get(AI_PROVIDER, "claude-sonnet-5")
    AI_MAX_RETRIES = int(os.environ.get("AI_MAX_RETRIES", "2"))
    AI_TIMEOUT_SECONDS = int(os.environ.get("AI_TIMEOUT_SECONDS", "60"))
    AI_WORKFLOW_BUDGET_USD = float(os.environ.get("AI_WORKFLOW_BUDGET_USD", "1.00"))

    ORG_DEFAULT_MONTHLY_WORKFLOW_LIMIT = int(
        os.environ.get("ORG_DEFAULT_MONTHLY_WORKFLOW_LIMIT", "20")
    )
    KILL_SWITCH_ENABLED = _bool_env("KILL_SWITCH_ENABLED", False)

    UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "storage/uploads")
    MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "10"))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "10")) * 1024 * 1024


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None):
    name = name or os.environ.get("FLASK_ENV", "development")
    return CONFIG_BY_NAME.get(name, DevelopmentConfig)
