from flask import jsonify, request
from flask_login import current_user, login_required

from app.api.v1 import api_v1
from app.services.authorization_service import get_membership_or_403
from app.services.errors import ValidationError
from app.services.external_action_service import (
    confirm_manual_publication,
    execute_manual_handoff,
)


@api_v1.route(
    "/organizations/<organization_id>/approvals/<approval_id>/execute", methods=["POST"]
)
@login_required
def execute_external_action_route(organization_id, approval_id):
    get_membership_or_403(organization_id)
    payload = request.get_json(silent=True) or {}
    idempotency_key = request.headers.get("Idempotency-Key") or payload.get("idempotency_key")
    if not idempotency_key:
        raise ValidationError(
            "Please correct the highlighted fields.",
            details=[{"field": "idempotency_key", "issue": "Required"}],
        )
    action = execute_manual_handoff(organization_id, approval_id, current_user.id, idempotency_key)
    return jsonify({"external_action": action.to_dict()}), 200


@api_v1.route(
    "/organizations/<organization_id>/external-actions/<action_id>/confirm-publication",
    methods=["POST"],
)
@login_required
def confirm_publication_route(organization_id, action_id):
    get_membership_or_403(organization_id)
    action = confirm_manual_publication(organization_id, action_id, current_user.id)
    return jsonify({"external_action": action.to_dict()}), 200
