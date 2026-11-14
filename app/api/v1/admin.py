"""Platform-owner endpoints (not tenant-scoped): the demo/contact inbox and
headline platform numbers. Access is limited to the emails listed in
PLATFORM_ADMIN_EMAILS; everyone else gets 403, including workspace owners."""

from datetime import timedelta

from flask import current_app, jsonify, request
from flask_login import current_user, login_required

from app.api.v1 import api_v1
from app.extensions import db
from app.models.base import utcnow
from app.models.organization import Organization
from app.models.platform import ContactEnquiry
from app.models.user import User
from app.models.workflow_run import WorkflowRun
from app.services.errors import NotFound, PermissionDenied, ValidationError

ENQUIRY_STATUSES = ("new", "contacted", "closed")


def is_platform_admin(user) -> bool:
    admins = current_app.config.get("PLATFORM_ADMIN_EMAILS") or set()
    return bool(user and getattr(user, "is_authenticated", False) and user.email.lower() in admins)


def _require_admin():
    if not is_platform_admin(current_user):
        raise PermissionDenied("Platform admin access required.")


def _enquiry_dict(e: ContactEnquiry) -> dict:
    return {"id": e.id, "name": e.name, "email": e.email, "company": e.company, "topic": e.topic,
            "message": e.message, "status": e.status, "created_at": e.created_at.isoformat() if e.created_at else None}


@api_v1.route("/admin/enquiries", methods=["GET"])
@login_required
def admin_enquiries_route():
    _require_admin()
    q = ContactEnquiry.query
    status = request.args.get("status")
    if status:
        if status not in ENQUIRY_STATUSES:
            raise ValidationError("Unknown status.", details=[{"field": "status", "issue": f"Use one of {', '.join(ENQUIRY_STATUSES)}"}])
        q = q.filter_by(status=status)
    rows = q.order_by(ContactEnquiry.created_at.desc()).limit(500).all()
    counts = dict(db.session.query(ContactEnquiry.status, db.func.count()).group_by(ContactEnquiry.status).all())
    return jsonify({"enquiries": [_enquiry_dict(e) for e in rows],
                    "counts": {s: counts.get(s, 0) for s in ENQUIRY_STATUSES}}), 200


@api_v1.route("/admin/enquiries/<enquiry_id>", methods=["PATCH"])
@login_required
def admin_update_enquiry_route(enquiry_id):
    _require_admin()
    e = db.session.get(ContactEnquiry, enquiry_id)
    if e is None:
        raise NotFound("Enquiry not found.")
    status = (request.get_json(silent=True) or {}).get("status")
    if status not in ENQUIRY_STATUSES:
        raise ValidationError("Unknown status.", details=[{"field": "status", "issue": f"Use one of {', '.join(ENQUIRY_STATUSES)}"}])
    e.status = status
    db.session.commit()
    return jsonify({"enquiry": _enquiry_dict(e)}), 200


@api_v1.route("/admin/unit-economics", methods=["GET"])
@login_required
def admin_unit_economics_route():
    from app.services.cost_service import platform_unit_economics

    _require_admin()
    rows = platform_unit_economics()
    db.session.commit()  # get_subscription may create a trial row for a workspace that had none
    return jsonify({"workspaces": rows, "basis": "AI cost is an estimate from token counts. Revenue counts active "
                                                 "subscriptions at list price; trials count as zero."}), 200


@api_v1.route("/admin/overview", methods=["GET"])
@login_required
def admin_overview_route():
    _require_admin()
    now = utcnow()
    d7, d30 = now - timedelta(days=7), now - timedelta(days=30)
    return jsonify({
        "users": {"total": User.query.count(),
                  "last_7_days": User.query.filter(User.created_at >= d7).count(),
                  "last_30_days": User.query.filter(User.created_at >= d30).count()},
        "workspaces": {"total": Organization.query.count(),
                       "last_30_days": Organization.query.filter(Organization.created_at >= d30).count()},
        "runs_last_30_days": WorkflowRun.query.filter(WorkflowRun.created_at >= d30).count(),
        "new_enquiries": ContactEnquiry.query.filter_by(status="new").count(),
    }), 200
