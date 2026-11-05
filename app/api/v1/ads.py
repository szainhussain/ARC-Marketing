from flask import jsonify, request
from flask_login import login_required

from app.api.v1 import api_v1
from app.services import ads_service as svc
from app.services.authorization_service import get_membership_or_403


def _body() -> dict:
    return request.get_json(silent=True) or {}


@api_v1.route("/organizations/<organization_id>/ads", methods=["GET"])
@login_required
def ads_overview_route(organization_id):
    get_membership_or_403(organization_id)
    return jsonify(svc.overview(organization_id)), 200


@api_v1.route("/organizations/<organization_id>/ads/guardrail", methods=["PUT", "POST"])
@login_required
def ads_guardrail_route(organization_id):
    m = get_membership_or_403(organization_id)
    return jsonify(svc.set_guardrail(m, _body())), 200


@api_v1.route("/organizations/<organization_id>/ads/launches", methods=["POST"])
@login_required
def ads_request_route(organization_id):
    m = get_membership_or_403(organization_id)
    return jsonify({"launch": svc.request_launch(m, _body())}), 201


@api_v1.route("/organizations/<organization_id>/ads/launches/<launch_id>/decision", methods=["POST"])
@login_required
def ads_decide_route(organization_id, launch_id):
    m = get_membership_or_403(organization_id)
    return jsonify({"launch": svc.decide(m, launch_id, _body())}), 200


@api_v1.route("/organizations/<organization_id>/ads/launches/<launch_id>/<action>", methods=["POST"])
@login_required
def ads_control_route(organization_id, launch_id, action):
    m = get_membership_or_403(organization_id)
    return jsonify({"launch": svc.control(m, launch_id, action)}), 200


@api_v1.route("/organizations/<organization_id>/ads/stop-all", methods=["POST"])
@login_required
def ads_stop_all_route(organization_id):
    m = get_membership_or_403(organization_id)
    return jsonify(svc.stop_all(m)), 200
