"""Download deliverables and reports as branded Excel, PowerPoint or PDF."""

from flask import Response, request
from flask_login import current_user, login_required

from app.api.v1 import api_v1
from app.extensions import limiter
from app.services.audit_service import record_audit_event
from app.services.authorization_service import get_membership_or_403
from app.services.export_service import export_deliverable, export_monthly_report


def _download(data: bytes, filename: str, mimetype: str) -> Response:
    return Response(data, mimetype=mimetype, headers={
        "Content-Disposition": f'attachment; filename="{filename}"', "X-Content-Type-Options": "nosniff"})


@api_v1.route("/organizations/<organization_id>/deliverables/<deliverable_id>/export", methods=["GET"])
@login_required
@limiter.limit("60 per hour")
def export_deliverable_route(organization_id, deliverable_id):
    get_membership_or_403(organization_id)
    data, name, mime = export_deliverable(organization_id, deliverable_id, request.args.get("format", ""))
    from app.extensions import db

    record_audit_event(organization_id, "deliverable.exported_document", actor_user_id=current_user.id,
                       target_type="deliverable", target_id=deliverable_id, metadata={"format": name.rsplit(".", 1)[-1]})
    db.session.commit()
    return _download(data, name, mime)


@api_v1.route("/organizations/<organization_id>/reports/monthly/export", methods=["GET"])
@login_required
@limiter.limit("60 per hour")
def export_monthly_report_route(organization_id):
    get_membership_or_403(organization_id)
    data, name, mime = export_monthly_report(organization_id, request.args.get("month", ""), request.args.get("format", ""))
    return _download(data, name, mime)
