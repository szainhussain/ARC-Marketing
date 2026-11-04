from flask import jsonify
from flask_login import current_user, login_required

from app.api.v1 import api_v1
from app.models.membership import APPROVAL_CAPABLE_ROLES
from app.services.authorization_service import get_membership_or_403, require_role
from app.workflows.engine import cancel_run, get_run_or_404, pause_run, resume_run


@api_v1.route("/organizations/<organization_id>/runs/<run_id>", methods=["GET"])
@login_required
def get_run_route(organization_id, run_id):
    get_membership_or_403(organization_id)
    run = get_run_or_404(organization_id, run_id)
    return jsonify({"workflow_run": run.to_dict()}), 200


@api_v1.route("/organizations/<organization_id>/runs/<run_id>/cancel", methods=["POST"])
@login_required
def cancel_run_route(organization_id, run_id):
    membership = get_membership_or_403(organization_id)
    require_role(membership, APPROVAL_CAPABLE_ROLES)
    run = cancel_run(organization_id, run_id, current_user.id)
    return jsonify({"workflow_run": run.to_dict()}), 200


@api_v1.route("/organizations/<organization_id>/runs/<run_id>/pause", methods=["POST"])
@login_required
def pause_run_route(organization_id, run_id):
    membership = get_membership_or_403(organization_id)
    require_role(membership, APPROVAL_CAPABLE_ROLES)
    run = pause_run(organization_id, run_id, current_user.id)
    return jsonify({"workflow_run": run.to_dict()}), 200


@api_v1.route("/organizations/<organization_id>/runs/<run_id>/resume", methods=["POST"])
@login_required
def resume_run_route(organization_id, run_id):
    membership = get_membership_or_403(organization_id)
    require_role(membership, APPROVAL_CAPABLE_ROLES)
    run = resume_run(organization_id, run_id, current_user.id)
    return jsonify({"workflow_run": run.to_dict()}), 200
