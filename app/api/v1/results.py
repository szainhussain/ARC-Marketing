"""Campaign results (entered by the team) and the monthly report."""

from flask import jsonify, request
from flask_login import current_user, login_required

from app.api.v1 import api_v1
from app.models.membership import OPERATOR_ROLES
from app.services.authorization_service import get_membership_or_403, require_role
from app.services.results_service import create_result, delete_result, monthly_report, summarize, update_result

RESULT_EDITORS = OPERATOR_ROLES + ("analyst",)


def _date_arg(name):
    from app.services.results_service import _parse_date

    v = request.args.get(name)
    return _parse_date(v, name) if v else None


@api_v1.route("/organizations/<organization_id>/results", methods=["GET"])
@login_required
def list_results_route(organization_id):
    get_membership_or_403(organization_id)
    return jsonify(summarize(organization_id, _date_arg("from"), _date_arg("to"),
                             request.args.get("campaign_id") or None)), 200


@api_v1.route("/organizations/<organization_id>/results", methods=["POST"])
@login_required
def create_result_route(organization_id):
    me = get_membership_or_403(organization_id)
    require_role(me, RESULT_EDITORS)
    row = create_result(organization_id, current_user.id, request.get_json(silent=True) or {})
    return jsonify({"result": row.to_dict()}), 201


@api_v1.route("/organizations/<organization_id>/results/<result_id>", methods=["PATCH"])
@login_required
def update_result_route(organization_id, result_id):
    me = get_membership_or_403(organization_id)
    require_role(me, RESULT_EDITORS)
    row = update_result(organization_id, result_id, current_user.id, request.get_json(silent=True) or {})
    return jsonify({"result": row.to_dict()}), 200


@api_v1.route("/organizations/<organization_id>/results/<result_id>", methods=["DELETE"])
@login_required
def delete_result_route(organization_id, result_id):
    me = get_membership_or_403(organization_id)
    require_role(me, RESULT_EDITORS)
    delete_result(organization_id, result_id, current_user.id)
    return jsonify({"status": "ok"}), 200


@api_v1.route("/organizations/<organization_id>/reports/monthly", methods=["GET"])
@login_required
def monthly_report_route(organization_id):
    get_membership_or_403(organization_id)
    return jsonify(monthly_report(organization_id, request.args.get("month") or "")), 200
