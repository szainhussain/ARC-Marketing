from flask import jsonify, request
from flask_login import current_user, login_required

from app.api.v1 import api_v1
from app.services.authorization_service import get_membership_or_403
from app.services.deliverable_service import (
    add_new_version,
    get_deliverable_or_404,
)
from app.services.errors import ValidationError


@api_v1.route("/organizations/<organization_id>/deliverables/<deliverable_id>", methods=["GET"])
@login_required
def get_deliverable_route(organization_id, deliverable_id):
    get_membership_or_403(organization_id)
    deliverable = get_deliverable_or_404(organization_id, deliverable_id)
    return jsonify({"deliverable": deliverable.to_dict()}), 200


@api_v1.route(
    "/organizations/<organization_id>/deliverables/<deliverable_id>/versions",
    methods=["GET"],
)
@login_required
def list_versions_route(organization_id, deliverable_id):
    get_membership_or_403(organization_id)
    deliverable = get_deliverable_or_404(organization_id, deliverable_id)
    return jsonify({"versions": [v.to_dict() for v in deliverable.versions]}), 200


@api_v1.route(
    "/organizations/<organization_id>/deliverables/<deliverable_id>/versions",
    methods=["POST"],
)
@login_required
def create_version_route(organization_id, deliverable_id):
    get_membership_or_403(organization_id)
    payload = request.get_json(silent=True) or {}
    content = payload.get("content")
    if not isinstance(content, dict):
        raise ValidationError(
            "Please correct the highlighted fields.",
            details=[{"field": "content", "issue": "Must be an object"}],
        )
    deliverable = add_new_version(
        organization_id,
        deliverable_id,
        content,
        current_user.id,
        revision_reason=payload.get("revision_reason"),
    )
    return jsonify({"deliverable": deliverable.to_dict(include_versions=True)}), 201
