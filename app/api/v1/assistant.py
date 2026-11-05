"""Ask ARC: each member's private conversation with the workspace assistant."""

from flask import jsonify, request
from flask_login import current_user, login_required

from app.api.v1 import api_v1
from app.extensions import limiter
from app.services.assistant_service import ask, history
from app.services.authorization_service import get_membership_or_403


@api_v1.route("/organizations/<organization_id>/assistant/messages", methods=["GET"])
@login_required
def assistant_history_route(organization_id):
    get_membership_or_403(organization_id)
    return jsonify({"messages": history(organization_id, current_user.id)}), 200


@api_v1.route("/organizations/<organization_id>/assistant/messages", methods=["POST"])
@login_required
@limiter.limit("30 per hour")
def assistant_ask_route(organization_id):
    get_membership_or_403(organization_id)
    q, a = ask(organization_id, current_user.id, (request.get_json(silent=True) or {}).get("content"))
    # The reply is written by the worker; the client polls.
    return jsonify({"question": q.to_dict(), "reply": a.to_dict()}), 202
