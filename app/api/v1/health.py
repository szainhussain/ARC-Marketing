import os

from flask import jsonify
from sqlalchemy import text

from app.api.v1 import api_v1
from app.extensions import db


@api_v1.route("/health/live", methods=["GET"])
def live():
    # Render sets RENDER_GIT_COMMIT; lets you confirm which commit is live.
    commit = (os.environ.get("RENDER_GIT_COMMIT") or "")[:7] or None
    return jsonify({"status": "ok", "commit": commit}), 200


@api_v1.route("/health/ready", methods=["GET"])
def ready():
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({"status": "ok", "database": "ok"}), 200
    except Exception:  # noqa: BLE001 - never leak internals from a health check
        return jsonify({"status": "degraded", "database": "unavailable"}), 503
