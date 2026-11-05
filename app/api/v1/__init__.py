from flask import Blueprint

api_v1 = Blueprint("api_v1", __name__, url_prefix="/api/v1")

from app.api.v1 import (  # noqa: E402,F401
    admin,
    approvals,
    auth,
    business_profile,
    campaigns,
    collaboration,
    deliverables,
    exports,
    external_actions,
    health,
    integrations,
    me,
    media,
    operations,
    platform,
    workspace,
    organizations,
    reports,
    results,
    runs,
)
