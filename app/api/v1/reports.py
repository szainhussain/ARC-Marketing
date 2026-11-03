from flask import jsonify
from flask_login import login_required

from app.api.v1 import api_v1
from app.models.audit_event import AuditEvent
from app.services.authorization_service import get_membership_or_403
from app.services.report_service import usage_by_period, workflow_summary


@api_v1.route("/organizations/<organization_id>/reports/summary", methods=["GET"])
@login_required
def reports_summary_route(organization_id):
    get_membership_or_403(organization_id)
    return jsonify({"summary": workflow_summary(organization_id)}), 200


@api_v1.route("/organizations/<organization_id>/usage", methods=["GET"])
@login_required
def usage_route(organization_id):
    get_membership_or_403(organization_id)
    return jsonify({"usage": usage_by_period(organization_id)}), 200


@api_v1.route("/organizations/<organization_id>/audit-events", methods=["GET"])
@login_required
def audit_events_route(organization_id):
    get_membership_or_403(organization_id)
    events = (
        AuditEvent.query.filter_by(organization_id=organization_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(200)
        .all()
    )
    return jsonify({"audit_events": [e.to_dict() for e in events]}), 200
