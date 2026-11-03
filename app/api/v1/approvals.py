from flask import jsonify, request
from flask_login import current_user, login_required

from app.api.v1 import api_v1
from app.services.approval_service import decide_approval, request_approval
from app.services.authorization_service import get_membership_or_403


@api_v1.route("/organizations/<organization_id>/approvals", methods=["POST"])
@login_required
def request_approval_route(organization_id):
    get_membership_or_403(organization_id)
    payload = request.get_json(silent=True) or {}
    approval = request_approval(
        organization_id,
        deliverable_id=payload.get("deliverable_id"),
        requested_by_user_id=current_user.id,
        action_type=payload.get("action_type", "manual_handoff"),
        action_payload=payload.get("action_payload"),
    )
    return jsonify({"approval": approval.to_dict()}), 201


@api_v1.route(
    "/organizations/<organization_id>/approvals/<approval_id>/decision", methods=["POST"]
)
@login_required
def decide_approval_route(organization_id, approval_id):
    membership = get_membership_or_403(organization_id)
    payload = request.get_json(silent=True) or {}
    approval = decide_approval(
        organization_id,
        approval_id,
        membership,
        decision=payload.get("decision"),
        comment=payload.get("comment"),
    )
    return jsonify({"approval": approval.to_dict()}), 200
