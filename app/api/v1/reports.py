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


@api_v1.route("/organizations/<organization_id>/audit-events/export.csv", methods=["GET"])
@login_required
def audit_events_export_route(organization_id):
    """Full audit log as CSV, for admins and compliance reviews."""

    import csv
    import io

    from flask import Response

    from app.models.membership import WORKSPACE_ADMIN_ROLES
    from app.models.user import User
    from app.services.authorization_service import require_role

    me = get_membership_or_403(organization_id)
    require_role(me, WORKSPACE_ADMIN_ROLES)
    events = AuditEvent.query.filter_by(organization_id=organization_id).order_by(AuditEvent.created_at.asc()).all()
    emails = {u.id: u.email for u in User.query.filter(User.id.in_({e.actor_user_id for e in events if e.actor_user_id})).all()} if events else {}
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["time_utc", "action", "actor", "target_type", "target_id", "outcome", "details"])

    def cell(v):
        # Neutralise spreadsheet formulas (CSV injection) in any text cell.
        v = "" if v is None else str(v)
        return "'" + v if v[:1] in ("=", "+", "-", "@", chr(9), chr(13)) else v

    for e in events:
        writer.writerow([cell(x) for x in (e.created_at.isoformat(), e.action,
                                           emails.get(e.actor_user_id, "system / agent / external"),
                                           e.target_type, e.target_id, e.outcome, e.metadata_json)])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=arc-audit-log.csv"})
