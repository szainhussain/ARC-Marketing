import os


def _bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _database_url() -> str:
    url = (os.environ.get("DATABASE_URL") or "sqlite:///dev.db").strip()
    # Tolerate the "psql '<url>'" snippet some dashboards show, and quotes.
    if url.startswith("psql "):
        url = url[len("psql "):].strip()
    url = url.strip("'\"")
    # Some hosts hand out "postgres://", which SQLAlchemy 2 no longer accepts.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    # SQLAlchemy 2.1 defaults "postgresql://" to the psycopg (v3) driver; we
    # ship psycopg2-binary, so name it explicitly.
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def _origins() -> list[str]:
    raw = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-key")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Comma-separated list allowed for CORS; the first is used in emailed links.
    FRONTEND_ORIGINS = _origins()
    FRONTEND_ORIGIN = FRONTEND_ORIGINS[0]
    # Flask-WTF's HTTPS Referer check requires same-origin requests; turn it
    # off only when the frontend is on a different domain (the CSRF token
    # header + CORS allowlist still protect every mutating request).
    WTF_CSRF_SSL_STRICT = _bool_env("WTF_CSRF_SSL_STRICT", True)
    # Run the agent worker as a thread inside the web process (free hosting
    # tiers without background workers). Use 1 gunicorn worker with it.
    RUN_EMBEDDED_WORKER = _bool_env("RUN_EMBEDDED_WORKER", False)

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

    # Worker retry backoff (exponential with jitter; a provider retry-after wins if longer).
    WORKER_RETRY_BASE_SECONDS = float(os.environ.get("WORKER_RETRY_BASE_SECONDS", "5"))
    WORKER_RETRY_MAX_SECONDS = float(os.environ.get("WORKER_RETRY_MAX_SECONDS", "120"))

    ORG_DEFAULT_MONTHLY_WORKFLOW_LIMIT = int(
        os.environ.get("ORG_DEFAULT_MONTHLY_WORKFLOW_LIMIT", "20")
    )
    KILL_SWITCH_ENABLED = _bool_env("KILL_SWITCH_ENABLED", False)

    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_HEADERS_ENABLED = True
    PASSWORD_RESET_TTL_MINUTES = int(os.environ.get("PASSWORD_RESET_TTL_MINUTES", "60"))
    INVITATION_TTL_DAYS = int(os.environ.get("INVITATION_TTL_DAYS", "7"))
    APPROVAL_TTL_DAYS = int(os.environ.get("APPROVAL_TTL_DAYS", "14"))
    DELETION_GRACE_DAYS = int(os.environ.get("DELETION_GRACE_DAYS", "30"))
    TRIAL_DAYS = int(os.environ.get("TRIAL_DAYS", "14"))
    # Bump when the Terms/Privacy Policy change; must match frontend/src/lib/legal.ts.
    TERMS_VERSION = "2026-11-05"
    # Emails allowed into the platform-owner inbox (demo requests, contact form).
    PLATFORM_ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get("PLATFORM_ADMIN_EMAILS", "").split(",") if e.strip()}

    # Billing: "test" (local test mode, default), "stripe", or "none".
    BILLING_PROVIDER = os.environ.get("BILLING_PROVIDER", "test")
    BILLING_WEBHOOK_SECRET = os.environ.get("BILLING_WEBHOOK_SECRET", "whsec_dev_only_change_me")
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
    # Outbound webhooks may target private/http URLs only in dev/test.
    WEBHOOK_ALLOW_PRIVATE_TARGETS = _bool_env("WEBHOOK_ALLOW_PRIVATE_TARGETS", False)
    # AI_PROVIDER=fixture is honoured only when this is set and never in production.
    ALLOW_FIXTURE_PROVIDER = _bool_env("ALLOW_FIXTURE_PROVIDER", False)
    IS_PRODUCTION = False
    TRUSTED_PROXY_HOPS = int(os.environ.get("TRUSTED_PROXY_HOPS", "0"))

    # "local" (files under UPLOAD_DIR) or "supabase" (private Supabase Storage bucket).
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local").strip().lower()
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "").strip()
    SUPABASE_SECRET_KEY = (os.environ.get("SUPABASE_SECRET_KEY")
                           or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    SUPABASE_STORAGE_BUCKET = os.environ.get("SUPABASE_STORAGE_BUCKET", "arc-uploads").strip()
    # Image generation (Gemini REST). Without a key, image jobs fail as capability_unavailable.
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    IMAGE_MODEL = os.environ.get("IMAGE_MODEL", "gemini-2.5-flash-image")
    IMAGE_TIMEOUT_SECONDS = int(os.environ.get("IMAGE_TIMEOUT_SECONDS", "90"))
    IMAGE_MONTHLY_LIMIT = int(os.environ.get("IMAGE_MONTHLY_LIMIT", "50"))
    ASSISTANT_MONTHLY_LIMIT = int(os.environ.get("ASSISTANT_MONTHLY_LIMIT", "300"))
    # Semantic search for Ask ARC (Gemini embeddings; same GEMINI_API_KEY). Keyword search without it.
    EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "gemini-embedding-001")
    EMBEDDING_DIMS = int(os.environ.get("EMBEDDING_DIMS", "768"))
    UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "storage/uploads")
    MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "10"))
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "10")) * 1024 * 1024


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    WORKER_RETRY_BASE_SECONDS = 0.0
    RATELIMIT_ENABLED = False
    SESSION_COOKIE_SECURE = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    # Proxies in front of the app that append to X-Forwarded-For. Default 2:
    # Vercel (frontend rewrite of /api/*) then Render's load balancer. Used so
    # rate limits key on the visitor's IP, not the proxy's.
    TRUSTED_PROXY_HOPS = int(os.environ.get("TRUSTED_PROXY_HOPS", "2"))
    IS_PRODUCTION = True
    ALLOW_FIXTURE_PROVIDER = False
    BILLING_PROVIDER = os.environ.get("BILLING_PROVIDER", "none")
    SESSION_COOKIE_SECURE = True


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None):
    name = name or os.environ.get("FLASK_ENV", "development")
    return CONFIG_BY_NAME.get(name, DevelopmentConfig)
