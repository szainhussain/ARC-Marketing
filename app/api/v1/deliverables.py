import json

from flask import jsonify, request
from flask_login import current_user, login_required
from marshmallow import ValidationError as SchemaError

from app.ai.schemas import SCHEMAS_BY_TASK_TYPE
from app.api.v1 import api_v1
from app.models.membership import OPERATOR_ROLES
from app.services.authorization_service import get_membership_or_403, require_role
from app.services.business_profile_service import get_or_create_profile
from app.services.deliverable_service import (
    add_new_version,
    get_deliverable_or_404,
)
from app.services.errors import ValidationError
from app.workflows.evaluation import _check_prohibited


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
    """A person edits a deliverable: the edit becomes a new immutable version
    (invalidating any pending approval), and must still match the schema the
    agent output was validated against."""

    me = get_membership_or_403(organization_id)
    require_role(me, OPERATOR_ROLES + ("contributor",))
    payload = request.get_json(silent=True) or {}
    content = payload.get("content")
    if not isinstance(content, dict):
        raise ValidationError(
            "Please correct the highlighted fields.",
            details=[{"field": "content", "issue": "Must be an object"}],
        )
    existing = get_deliverable_or_404(organization_id, deliverable_id)
    schema_cls = SCHEMAS_BY_TASK_TYPE.get(existing.deliverable_type)
    if schema_cls is not None:
        try:
            content = schema_cls().load(content)
        except SchemaError as exc:
            raise ValidationError("The edited content doesn't match this deliverable's format.",
                                  details=[{"field": f"content.{k}", "issue": "; ".join(map(str, _flatten(v)))}
                                           for k, v in exc.messages.items()])
    deliverable = add_new_version(
        organization_id,
        deliverable_id,
        content,
        current_user.id,
        revision_reason=payload.get("revision_reason"),
    )
    profile = get_or_create_profile(organization_id).to_dict()
    brand = _check_prohibited(json.dumps(content, ensure_ascii=False), profile)
    return jsonify({"deliverable": deliverable.to_dict(include_versions=True), "brand_check": brand}), 201


def _flatten(messages):
    if isinstance(messages, dict):
        return [f"{k}: {m}" for k, v in messages.items() for m in _flatten(v)]
    if isinstance(messages, list):
        return [m for v in messages for m in _flatten(v)]
    return [messages]
