from flask import jsonify, request
from flask_login import current_user, login_required

from app.api.v1 import api_v1
from app.models.deliverable import Deliverable
from app.services.authorization_service import get_membership_or_403
from app.services.campaign_service import (
    archive_campaign,
    create_campaign,
    get_campaign_or_404,
    list_campaigns,
    update_campaign,
)
from app.models.membership import ROLE_VIEWER, VALID_ROLES
from app.models.workflow_run import WorkflowRun
from app.services.authorization_service import require_role
from app.workflows.engine import enqueue_campaign_run


@api_v1.route("/organizations/<organization_id>/campaigns", methods=["GET"])
@login_required
def list_campaigns_route(organization_id):
    get_membership_or_403(organization_id)
    campaigns = list_campaigns(organization_id)
    return jsonify({"campaigns": [c.to_dict() for c in campaigns]}), 200


@api_v1.route("/organizations/<organization_id>/campaigns", methods=["POST"])
@login_required
def create_campaign_route(organization_id):
    get_membership_or_403(organization_id)
    payload = request.get_json(silent=True) or {}
    campaign = create_campaign(organization_id, current_user.id, payload)
    return jsonify({"campaign": campaign.to_dict()}), 201


@api_v1.route("/organizations/<organization_id>/campaigns/<campaign_id>", methods=["GET"])
@login_required
def get_campaign_route(organization_id, campaign_id):
    get_membership_or_403(organization_id)
    campaign = get_campaign_or_404(organization_id, campaign_id)
    return jsonify({"campaign": campaign.to_dict()}), 200


@api_v1.route("/organizations/<organization_id>/campaigns/<campaign_id>", methods=["PATCH"])
@login_required
def update_campaign_route(organization_id, campaign_id):
    get_membership_or_403(organization_id)
    payload = request.get_json(silent=True) or {}
    campaign = update_campaign(organization_id, campaign_id, current_user.id, payload)
    return jsonify({"campaign": campaign.to_dict()}), 200


@api_v1.route("/organizations/<organization_id>/campaigns/<campaign_id>", methods=["DELETE"])
@login_required
def archive_campaign_route(organization_id, campaign_id):
    get_membership_or_403(organization_id)
    campaign = archive_campaign(organization_id, campaign_id, current_user.id)
    return jsonify({"campaign": campaign.to_dict()}), 200


@api_v1.route(
    "/organizations/<organization_id>/campaigns/<campaign_id>/runs", methods=["POST"]
)
@login_required
def start_run_route(organization_id, campaign_id):
    membership = get_membership_or_403(organization_id)
    require_role(membership, tuple(r for r in VALID_ROLES if r != ROLE_VIEWER))
    payload = request.get_json(silent=True) or {}
    idempotency_key = request.headers.get("Idempotency-Key") or payload.get("idempotency_key")
    if not idempotency_key:
        from app.services.errors import ValidationError

        raise ValidationError(
            "Please correct the highlighted fields.",
            details=[{"field": "idempotency_key", "issue": "Required"}],
        )
    # Only records the run and its tasks; the worker process executes
    # them, so 202 Accepted is literally true.
    run = enqueue_campaign_run(organization_id, campaign_id, current_user.id, idempotency_key)
    return jsonify({"workflow_run": run.to_dict()}), 202


@api_v1.route(
    "/organizations/<organization_id>/campaigns/<campaign_id>/runs", methods=["GET"]
)
@login_required
def list_campaign_runs_route(organization_id, campaign_id):
    get_membership_or_403(organization_id)
    get_campaign_or_404(organization_id, campaign_id)
    runs = (
        WorkflowRun.query.filter_by(organization_id=organization_id, campaign_id=campaign_id)
        .order_by(WorkflowRun.created_at.desc())
        .limit(20)
        .all()
    )
    return jsonify({"workflow_runs": [r.to_dict() for r in runs]}), 200


@api_v1.route(
    "/organizations/<organization_id>/campaigns/<campaign_id>/deliverables", methods=["GET"]
)
@login_required
def list_campaign_deliverables_route(organization_id, campaign_id):
    get_membership_or_403(organization_id)
    get_campaign_or_404(organization_id, campaign_id)
    deliverables = Deliverable.query.filter_by(
        organization_id=organization_id, campaign_id=campaign_id
    ).all()
    return jsonify({"deliverables": [d.to_dict() for d in deliverables]}), 200


@api_v1.route("/organizations/<organization_id>/campaigns/<campaign_id>/recurrence", methods=["POST"])
@login_required
def set_recurrence_route(organization_id, campaign_id):
    from app.models.membership import OPERATOR_ROLES
    from app.services.campaign_service import get_campaign_or_404
    from app.services.recurrence_service import set_recurrence

    membership = get_membership_or_403(organization_id)
    require_role(membership, OPERATOR_ROLES)
    payload = request.get_json(silent=True) or {}
    campaign = set_recurrence(get_campaign_or_404(organization_id, campaign_id), current_user.id,
                              payload.get("recurrence"), payload.get("recurrence_day"))
    return jsonify({"campaign": campaign.to_dict()}), 200
