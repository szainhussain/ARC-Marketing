"""Public site API, Command Center analytics, documents/assets, billing
(checkout + signed payment webhooks), outbound webhook management, email
verification, data export & deletion, and the OpenAPI index."""

import csv
import hashlib
import io
import json
import logging
import secrets
from datetime import timedelta

from flask import Response, current_app, jsonify, request
from flask_login import current_user, login_required

from app.agents.registry import agents_in_department_order
from app.api.v1 import api_v1
from app.billing.providers import BillingConfigError, SignatureError, TestPaymentProvider, get_payment_provider
from app.extensions import csrf, db, limiter
from app.integrations.catalog import CATALOG
from app.models.billing import WEBHOOK_EVENTS, WebhookDelivery, WebhookEndpoint
from app.models.document import Document
from app.models.membership import OPERATOR_ROLES, ROLE_OWNER, WORKSPACE_ADMIN_ROLES
from app.models.organization import Organization
from app.models.platform import ContactEnquiry
from app.services.analytics_service import dashboard, platform_analytics
from app.services.audit_service import record_audit_event
from app.services.authorization_service import get_membership_or_403, require_role
from app.services.billing_service import billing_history, handle_webhook, process_event, start_checkout
from app.services.errors import Conflict, NotFound, PermissionDenied, ValidationError
from app.services.platform_service import public_plans
from app.services.webhook_service import create_endpoint
from app.storage import UploadRejected, get_storage, validate_upload

log = logging.getLogger(__name__)


def _invalid(field, issue):
    return ValidationError("Please correct the highlighted fields.", details=[{"field": field, "issue": issue}])


def _days() -> int:
    try:
        days = int(request.args.get("days", 30))
    except ValueError:
        raise _invalid("days", "Must be a number")
    if days not in (7, 14, 30, 90, 180, 365):
        raise _invalid("days", "Use 7, 14, 30, 90, 180 or 365")
    return days


# ---- Public (no auth) -------------------------------------------------------

@api_v1.route("/public/plans", methods=["GET"])
def public_plans_route():
    return jsonify({"plans": [p.to_dict() for p in public_plans()],
                    "pricing_note": "Prices are provisional and configurable; they are not final commercial terms."}), 200


@api_v1.route("/public/agents", methods=["GET"])
def public_agents_route():
    return jsonify({"agents": [a.to_public_dict() for a in agents_in_department_order()]}), 200


@api_v1.route("/public/integrations", methods=["GET"])
def public_integrations_route():
    return jsonify({"integrations": CATALOG}), 200


@api_v1.route("/public/contact", methods=["POST"])
@csrf.exempt  # public form, no session; protected by rate limit + validation
@limiter.limit("5 per hour")
def public_contact_route():
    p = request.get_json(silent=True) or {}
    errors = []
    name = (p.get("name") or "").strip()
    email = (p.get("email") or "").strip().lower()
    message = (p.get("message") or "").strip()
    topic = p.get("topic") or "sales"
    if not name:
        errors.append({"field": "name", "issue": "Required"})
    if "@" not in email or len(email) > 255:
        errors.append({"field": "email", "issue": "A valid email is required"})
    if len(message) < 10:
        errors.append({"field": "message", "issue": "Tell us a little more (10+ characters)"})
    if topic not in ("sales", "demo", "support", "partnership", "security", "cancellation", "other"):
        errors.append({"field": "topic", "issue": "Unknown topic"})
    if errors:
        raise ValidationError("Please correct the highlighted fields.", details=errors)
    db.session.add(ContactEnquiry(name=name[:255], email=email, company=(p.get("company") or "")[:255],
                                  topic=topic, message=message[:5000]))
    db.session.commit()
    return jsonify({"status": "received",
                    "message": "Thanks — your message was received. We'll reply by email."}), 201


# ---- Command Center & analytics --------------------------------------------

@api_v1.route("/organizations/<organization_id>/dashboard", methods=["GET"])
@login_required
def dashboard_route(organization_id):
    get_membership_or_403(organization_id)
    campaign_id = request.args.get("campaign_id") or None
    return jsonify(dashboard(organization_id, _days(), campaign_id)), 200


@api_v1.route("/organizations/<organization_id>/analytics", methods=["GET"])
@login_required
def analytics_route(organization_id):
    get_membership_or_403(organization_id)
    return jsonify(platform_analytics(organization_id, _days())), 200


@api_v1.route("/organizations/<organization_id>/reports/export.csv", methods=["GET"])
@login_required
def report_export_route(organization_id):
    get_membership_or_403(organization_id)
    data = platform_analytics(organization_id, _days())
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "tasks_succeeded", "tasks_failed", "retries", "estimated_cost_usd"])
    for row in data["series"]:
        writer.writerow([row["date"], row["tasks_succeeded"], row["tasks_failed"], row["retries"], row["cost_usd"]])
    writer.writerow([])
    writer.writerow(["agent", "executions", "tokens", "estimated_cost_usd"])
    for row in data["cost_by_agent"]:
        writer.writerow([row["agent_name"], row["executions"], row["tokens"], row["cost_usd"]])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=arc-report-{data['range_days']}d.csv"})


# ---- Documents / brand assets ----------------------------------------------

@api_v1.route("/organizations/<organization_id>/documents", methods=["GET"])
@login_required
def list_documents_route(organization_id):
    get_membership_or_403(organization_id)
    docs = Document.query.filter_by(organization_id=organization_id, status="stored").order_by(
        Document.created_at.desc()).all()
    return jsonify({"documents": [d.to_dict() for d in docs],
                    "limits": {"max_mb": current_app.config.get("MAX_UPLOAD_MB", 10),
                               "allowed": ["png", "jpg", "jpeg", "gif", "webp", "pdf", "txt", "md", "csv"]}}), 200


@api_v1.route("/organizations/<organization_id>/documents", methods=["POST"])
@login_required
def upload_document_route(organization_id):
    me = get_membership_or_403(organization_id)
    require_role(me, OPERATOR_ROLES + ("contributor",))
    upload = request.files.get("file")
    if upload is None:
        raise _invalid("file", "Choose a file to upload")
    data = upload.read()
    try:
        ext = validate_upload(upload.filename, upload.mimetype, data)
    except UploadRejected as exc:
        raise _invalid("file", str(exc))
    key, checksum = get_storage().put(organization_id, ext, data)
    safe_name = "".join(ch for ch in upload.filename if ch.isalnum() or ch in "._- ")[:200] or f"file.{ext}"
    doc = Document(organization_id=organization_id, uploaded_by_user_id=current_user.id, original_filename=safe_name,
                   storage_key=key, content_type=upload.mimetype or "application/octet-stream",
                   size_bytes=len(data), checksum_sha256=checksum)
    db.session.add(doc)
    db.session.flush()
    record_audit_event(organization_id, "document.uploaded", actor_user_id=current_user.id,
                       target_type="document", target_id=doc.id)
    db.session.commit()
    return jsonify({"document": doc.to_dict()}), 201


def _doc_or_404(organization_id, document_id):
    doc = Document.query.filter_by(id=document_id, organization_id=organization_id, status="stored").first()
    if doc is None:
        raise NotFound("Document not found.")
    return doc


@api_v1.route("/organizations/<organization_id>/documents/<document_id>/download", methods=["GET"])
@login_required
def download_document_route(organization_id, document_id):
    get_membership_or_403(organization_id)
    doc = _doc_or_404(organization_id, document_id)
    return Response(get_storage().get(doc.storage_key), mimetype="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"',
                             "X-Content-Type-Options": "nosniff"})


@api_v1.route("/organizations/<organization_id>/documents/<document_id>", methods=["DELETE"])
@login_required
def delete_document_route(organization_id, document_id):
    me = get_membership_or_403(organization_id)
    require_role(me, OPERATOR_ROLES)
    doc = _doc_or_404(organization_id, document_id)
    get_storage().delete(doc.storage_key)
    doc.status = "deleted"
    record_audit_event(organization_id, "document.deleted", actor_user_id=current_user.id,
                       target_type="document", target_id=doc.id)
    db.session.commit()
    return jsonify({"status": "ok"}), 200


# ---- Billing ---------------------------------------------------------------

@api_v1.route("/organizations/<organization_id>/billing/checkout", methods=["POST"])
@login_required
def billing_checkout_route(organization_id):
    me = get_membership_or_403(organization_id)
    require_role(me, (ROLE_OWNER,))
    try:
        session = start_checkout(organization_id, (request.get_json(silent=True) or {}).get("plan_code"))
    except BillingConfigError as exc:
        raise Conflict(f"Billing is not configured: {exc}")
    record_audit_event(organization_id, "billing.checkout_started", actor_user_id=current_user.id,
                       target_type="subscription", metadata={"mode": session.get("mode")})
    db.session.commit()
    return jsonify({"checkout": session}), 201


@api_v1.route("/organizations/<organization_id>/billing/history", methods=["GET"])
@login_required
def billing_history_route(organization_id):
    get_membership_or_403(organization_id)
    return jsonify({"events": billing_history(organization_id)}), 200


@api_v1.route("/organizations/<organization_id>/billing/test-complete", methods=["POST"])
@login_required
def billing_test_complete_route(organization_id):
    """TEST MODE ONLY: simulates the provider sending a signed
    checkout.session.completed webhook. Disabled unless BILLING_PROVIDER=test."""

    me = get_membership_or_403(organization_id)
    require_role(me, (ROLE_OWNER,))
    provider = get_payment_provider(current_app.config)
    if not isinstance(provider, TestPaymentProvider):
        raise PermissionDenied("Test checkout is only available in billing test mode.")
    p = request.get_json(silent=True) or {}
    body, signature = provider.build_event("checkout.session.completed", {
        "id": p.get("session_id") or "cs_test", "client_reference_id": organization_id,
        "metadata": {"organization_id": organization_id, "plan_code": p.get("plan_code")},
    })
    result = handle_webhook(body, signature)  # same verified path as a real webhook
    return jsonify(result), 200


@api_v1.route("/billing/webhook", methods=["POST"])
@csrf.exempt  # authenticated by signature, not session
def billing_webhook_route():
    try:
        result = handle_webhook(request.get_data(), request.headers.get("Stripe-Signature"))
    except SignatureError as exc:
        log.warning("Rejected billing webhook: %s", exc)
        return jsonify({"error": {"code": "INVALID_SIGNATURE", "message": "Invalid signature."}}), 400
    return jsonify(result), 200


# ---- Outbound webhooks -----------------------------------------------------

@api_v1.route("/organizations/<organization_id>/webhooks", methods=["GET"])
@login_required
def list_webhooks_route(organization_id):
    me = get_membership_or_403(organization_id)
    require_role(me, WORKSPACE_ADMIN_ROLES)
    endpoints = WebhookEndpoint.query.filter_by(organization_id=organization_id).all()
    deliveries = (WebhookDelivery.query.filter_by(organization_id=organization_id)
                  .order_by(WebhookDelivery.created_at.desc()).limit(30).all())
    return jsonify({"endpoints": [e.to_dict() for e in endpoints], "deliveries": [d.to_dict() for d in deliveries],
                    "event_types": list(WEBHOOK_EVENTS)}), 200


@api_v1.route("/organizations/<organization_id>/webhooks", methods=["POST"])
@login_required
def create_webhook_route(organization_id):
    me = get_membership_or_403(organization_id)
    require_role(me, WORKSPACE_ADMIN_ROLES)
    p = request.get_json(silent=True) or {}
    endpoint = create_endpoint(organization_id, p.get("url"), p.get("events") or [], p.get("description"))
    record_audit_event(organization_id, "webhook.created", actor_user_id=current_user.id,
                       target_type="webhook_endpoint", target_id=endpoint.id)
    db.session.commit()
    return jsonify({"endpoint": endpoint.to_dict(), "signing_secret": endpoint.secret,
                    "note": "Store this secret now; it is not shown again."}), 201


@api_v1.route("/organizations/<organization_id>/webhooks/<endpoint_id>", methods=["DELETE"])
@login_required
def delete_webhook_route(organization_id, endpoint_id):
    me = get_membership_or_403(organization_id)
    require_role(me, WORKSPACE_ADMIN_ROLES)
    ep = WebhookEndpoint.query.filter_by(id=endpoint_id, organization_id=organization_id).first()
    if ep is None:
        raise NotFound("Webhook endpoint not found.")
    ep.is_active = False
    db.session.commit()
    return jsonify({"status": "ok"}), 200


# ---- Email verification ----------------------------------------------------

def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


@api_v1.route("/auth/verify-email/request", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
def request_email_verification_route():
    from app.models.platform import PasswordResetToken  # reuse token table with a purpose prefix
    from app.models.base import utcnow

    token = secrets.token_urlsafe(32)
    db.session.add(PasswordResetToken(user_id=current_user.id, token_hash=_hash("verify:" + token),
                                      expires_at=utcnow() + timedelta(days=2)))
    db.session.commit()
    link = f"{current_app.config['FRONTEND_ORIGIN']}/verify-email?token={token}"
    if current_app.config.get("DEBUG") or current_app.config.get("TESTING"):
        log.warning("Email verification link (dev only): %s", link)
        current_app.extensions["last_verify_link"] = link
    return jsonify({"status": "ok", "message": "If email delivery is configured, a link is on its way.",
                    "email_delivery_configured": False}), 200


@api_v1.route("/auth/verify-email", methods=["POST"])
@login_required
def verify_email_route():
    from datetime import timezone

    from app.models.base import utcnow
    from app.models.platform import PasswordResetToken

    row = PasswordResetToken.query.filter_by(
        token_hash=_hash("verify:" + ((request.get_json(silent=True) or {}).get("token") or ""))).first()
    expires = row.expires_at.replace(tzinfo=timezone.utc) if row and row.expires_at.tzinfo is None else (
        row.expires_at if row else None)
    if row is None or row.used_at or row.user_id != current_user.id or expires < utcnow():
        raise ValidationError("This verification link is invalid or has expired.")
    row.used_at = utcnow()
    current_user.email_verified_at = utcnow()
    db.session.commit()
    return jsonify({"status": "verified"}), 200


# ---- Data export & deletion ------------------------------------------------

@api_v1.route("/organizations/<organization_id>/export", methods=["GET"])
@login_required
def export_workspace_route(organization_id):
    me = get_membership_or_403(organization_id)
    require_role(me, WORKSPACE_ADMIN_ROLES)
    from app.services.data_lifecycle import export_workspace

    data = export_workspace(organization_id)
    record_audit_event(organization_id, "workspace.exported", actor_user_id=current_user.id,
                       target_type="organization", target_id=organization_id)
    db.session.commit()
    return Response(json.dumps(data, indent=2, default=str), mimetype="application/json",
                    headers={"Content-Disposition": "attachment; filename=arc-workspace-export.json"})


@api_v1.route("/organizations/<organization_id>/deletion", methods=["POST"])
@login_required
def request_deletion_route(organization_id):
    me = get_membership_or_403(organization_id)
    require_role(me, (ROLE_OWNER,))
    from app.models.base import utcnow

    org = db.session.get(Organization, organization_id)
    if (request.get_json(silent=True) or {}).get("confirm_name") != org.name:
        raise _invalid("confirm_name", "Type the workspace name exactly to confirm")
    org.status = "deletion_scheduled"
    org.deletion_scheduled_at = utcnow() + timedelta(days=current_app.config.get("DELETION_GRACE_DAYS", 30))
    org.automation_paused = True
    org.kill_switch_enabled = True
    record_audit_event(organization_id, "workspace.deletion_scheduled", actor_user_id=current_user.id,
                       target_type="organization", target_id=organization_id)
    db.session.commit()
    return jsonify({"status": "deletion_scheduled", "deletion_scheduled_at": org.deletion_scheduled_at.isoformat()}), 200


@api_v1.route("/organizations/<organization_id>/deletion", methods=["DELETE"])
@login_required
def cancel_deletion_route(organization_id):
    me = get_membership_or_403(organization_id)
    require_role(me, (ROLE_OWNER,))
    org = db.session.get(Organization, organization_id)
    if org.status != "deletion_scheduled":
        raise Conflict("No deletion is scheduled.")
    org.status, org.deletion_scheduled_at = "active", None
    record_audit_event(organization_id, "workspace.deletion_cancelled", actor_user_id=current_user.id,
                       target_type="organization", target_id=organization_id)
    db.session.commit()
    return jsonify({"status": "active"}), 200


# ---- OpenAPI ---------------------------------------------------------------

@api_v1.route("/openapi.json", methods=["GET"])
def openapi_route():
    from app.api.openapi import build_spec

    return jsonify(build_spec(current_app)), 200
