from flask import jsonify
from flask_login import current_user, login_required

from app.api.v1 import api_v1
from app.services.authorization_service import get_membership_or_403
from app.services.workflow_service import cancel_run, get_run_or_404


@api_v1.route("/organizations/<organization_id>/runs/<run_id>", methods=["GET"])
@login_required
def get_run_route(organization_id, run_id):
    get_membership_or_403(organization_id)
    run = get_run_or_404(organization_id, run_id)
    return jsonify({"workflow_run": run.to_dict()}), 200


@api_v1.route("/organizations/<organization_id>/runs/<run_id>/cancel", methods=["POST"])
@login_required
def cancel_run_route(organization_id, run_id):
    get_membership_or_403(organization_id)
    run = cancel_run(organization_id, run_id, current_user.id)
    return jsonify({"workflow_run": run.to_dict()}), 200
