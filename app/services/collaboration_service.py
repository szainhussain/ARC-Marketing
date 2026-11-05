"""Comments and client review links.

A review link lets someone outside the workspace (usually the client) see one
deliverable version and approve, request changes or reject it once. Creating
one needs an approver role, because the link carries that approver's power for
this single approval. The same guards as an in-app decision apply: the
approval must still be pending and unexpired, and the deliverable must still
be on the exact version the approval was requested for.
"""

import hashlib
import json
import secrets
from datetime import timedelta, timezone

from app.extensions import db
from app.models.approval import DECISION_EXPIRED, DECISION_PENDING, Approval
from app.models.base import utcnow
from app.models.collaboration import DeliverableComment, ReviewLink
from app.models.deliverable import Deliverable, DeliverableVersion
from app.models.organization import Organization
from app.models.user import User
from app.services.approval_service import VALID_DECISION_INPUTS, _is_expired, get_approval_or_404
from app.services.audit_service import record_audit_event
from app.services.deliverable_service import get_deliverable_or_404
from app.services.errors import Conflict, NotFound, PermissionDenied, ValidationError

MAX_COMMENT = 5000
LINK_MAX_DAYS = 14


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _aware(dt):
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def _clean_body(body) -> str:
    text = (body or "").strip() if isinstance(body, str) else ""
    if not text:
        raise ValidationError("Please correct the highlighted fields.", details=[{"field": "body", "issue": "Write a comment"}])
    if len(text) > MAX_COMMENT:
        raise ValidationError("Please correct the highlighted fields.", details=[{"field": "body", "issue": f"Keep it under {MAX_COMMENT} characters"}])
    return text


# ---- Comments --------------------------------------------------------------

def list_comments(organization_id: str, deliverable_id: str) -> list[dict]:
    get_deliverable_or_404(organization_id, deliverable_id)
    rows = DeliverableComment.query.filter_by(organization_id=organization_id, deliverable_id=deliverable_id) \
        .order_by(DeliverableComment.created_at.asc()).all()
    names = {u.id: u.full_name for u in User.query.filter(User.id.in_({r.author_user_id for r in rows if r.author_user_id})).all()} if rows else {}
    return [r.to_dict(author_name=names.get(r.author_user_id)) for r in rows]


def add_comment(organization_id: str, deliverable_id: str, user_id: str, body) -> DeliverableComment:
    deliverable = get_deliverable_or_404(organization_id, deliverable_id)
    comment = DeliverableComment(organization_id=organization_id, deliverable_id=deliverable.id,
                                 deliverable_version_id=deliverable.current_version_id,
                                 author_user_id=user_id, body=_clean_body(body))
    db.session.add(comment)
    db.session.flush()
    record_audit_event(organization_id, "comment.added", actor_user_id=user_id,
                       target_type="deliverable", target_id=deliverable.id)
    db.session.commit()
    return comment


# ---- Review links (workspace side) -----------------------------------------

def create_review_link(organization_id: str, approval_id: str, membership, label: str | None, days) -> tuple[ReviewLink, str]:
    if not membership.can_approve_external_actions():
        raise PermissionDenied("Only approvers can share an approval for client review.")
    approval = get_approval_or_404(organization_id, approval_id)
    if approval.decision != DECISION_PENDING or _is_expired(approval):
        raise Conflict("Only a pending approval can be shared for review.")
    try:
        days = int(days or 7)
    except (TypeError, ValueError):
        days = 7
    days = max(1, min(LINK_MAX_DAYS, days))
    expires = utcnow() + timedelta(days=days)
    if approval.expires_at is not None:
        expires = min(expires, _aware(approval.expires_at))
    token = secrets.token_urlsafe(32)
    link = ReviewLink(organization_id=organization_id, approval_id=approval.id, token_hash=_hash(token),
                      label=(label or "").strip()[:120] or None, created_by_user_id=membership.user_id, expires_at=expires)
    db.session.add(link)
    db.session.flush()
    record_audit_event(organization_id, "review_link.created", actor_user_id=membership.user_id,
                       target_type="approval", target_id=approval.id, metadata={"review_link_id": link.id, "days": days})
    db.session.commit()
    return link, token


def list_review_links(organization_id: str, approval_id: str) -> list[dict]:
    get_approval_or_404(organization_id, approval_id)
    return [l.to_dict() for l in ReviewLink.query.filter_by(organization_id=organization_id, approval_id=approval_id)
            .order_by(ReviewLink.created_at.desc())]


def revoke_review_link(organization_id: str, link_id: str, membership) -> ReviewLink:
    if not membership.can_approve_external_actions():
        raise PermissionDenied("Only approvers can revoke review links.")
    link = ReviewLink.query.filter_by(id=link_id, organization_id=organization_id).first()
    if link is None:
        raise NotFound("Review link not found.")
    if link.revoked_at is None:
        link.revoked_at = utcnow()
        record_audit_event(organization_id, "review_link.revoked", actor_user_id=membership.user_id,
                           target_type="approval", target_id=link.approval_id, metadata={"review_link_id": link.id})
        db.session.commit()
    return link


# ---- Review links (public side) --------------------------------------------

def _link_for_token(token: str) -> ReviewLink:
    link = ReviewLink.query.filter_by(token_hash=_hash(token or "")).first() if token else None
    if link is None or link.revoked_at is not None:
        raise NotFound("This review link is invalid or has been withdrawn.")
    if _aware(link.expires_at) < utcnow():
        raise NotFound("This review link has expired. Ask the team for a new one.")
    return link


def review_payload(token: str) -> dict:
    link = _link_for_token(token)
    approval = db.session.get(Approval, link.approval_id)
    deliverable = db.session.get(Deliverable, approval.deliverable_id)
    version = db.session.get(DeliverableVersion, approval.deliverable_version_id)
    org = db.session.get(Organization, link.organization_id)
    still_current = deliverable.current_version_id == approval.deliverable_version_id
    comments = DeliverableComment.query.filter_by(organization_id=link.organization_id, deliverable_id=deliverable.id,
                                                  deliverable_version_id=version.id) \
        .order_by(DeliverableComment.created_at.asc()).all()
    return {
        "workspace_name": org.name if org else "",
        "deliverable_type": deliverable.deliverable_type,
        "version_number": version.version_number,
        "content": json.loads(version.content_json),
        "decision": approval.decision,
        "decided_at": approval.decided_at.isoformat() if approval.decided_at else None,
        "can_decide": link.used_at is None and approval.decision == DECISION_PENDING and still_current
                      and not _is_expired(approval),
        "superseded": not still_current,
        "expires_at": _aware(link.expires_at).isoformat(),
        # Only comments made through review links; the team's internal comments stay private.
        "comments": [c.to_dict() for c in comments if c.review_link_id is not None],
    }


def _clean_reviewer(name, email) -> tuple[str, str]:
    name = (name or "").strip() if isinstance(name, str) else ""
    email = (email or "").strip().lower() if isinstance(email, str) else ""
    errors = []
    if not name:
        errors.append({"field": "name", "issue": "Required"})
    if "@" not in email or len(email) > 255:
        errors.append({"field": "email", "issue": "A valid email is required"})
    if errors:
        raise ValidationError("Please correct the highlighted fields.", details=errors)
    return name[:120], email


def decide_via_link(token: str, decision: str, name, email, comment) -> Approval:
    if decision not in VALID_DECISION_INPUTS:
        raise ValidationError("Invalid decision.")
    name, email = _clean_reviewer(name, email)
    link = _link_for_token(token)
    if link.used_at is not None:
        raise Conflict("A decision was already made with this link.")
    approval = db.session.get(Approval, link.approval_id)
    if approval.decision == DECISION_PENDING and _is_expired(approval):
        approval.decision = DECISION_EXPIRED
        db.session.commit()
        raise Conflict("This approval request expired. Ask the team for a new one.")
    if approval.decision != DECISION_PENDING:
        raise Conflict(f"This approval is already '{approval.decision}'.")
    deliverable = db.session.get(Deliverable, approval.deliverable_id)
    if deliverable.current_version_id != approval.deliverable_version_id:
        approval.decision = "invalidated"
        db.session.commit()
        raise Conflict("The team changed this content after sharing it. Ask them for a new link.")

    comment = (comment or "").strip()[:MAX_COMMENT] if isinstance(comment, str) else ""
    approval.decision = decision
    approval.decision_comment = comment or None
    approval.decided_by_external_name = name
    approval.decided_by_external_email = email
    approval.decided_at = utcnow()
    link.used_at = utcnow()
    if comment:
        db.session.add(DeliverableComment(organization_id=link.organization_id, deliverable_id=deliverable.id,
                                          deliverable_version_id=approval.deliverable_version_id,
                                          external_author_name=name, review_link_id=link.id, body=comment))
    db.session.flush()
    record_audit_event(link.organization_id, "approval.decided", actor_user_id=None, target_type="approval",
                       target_id=approval.id, metadata={"decision": decision, "via": "review_link",
                                                        "review_link_id": link.id, "external_reviewer": email})
    from app.services.platform_service import notify
    from app.services.webhook_service import emit

    label = {"approved": "approved", "rejected": "rejected", "changes_requested": "asked for changes on"}[decision]
    notify(link.organization_id, "approval.external_decision", f"{name} {label} a {deliverable.deliverable_type.replace('_', ' ')}",
           body=comment or None, link=f"/app/campaigns/{deliverable.campaign_id}/deliverables",
           severity="success" if decision == "approved" else "warning")
    emit(link.organization_id, "approval.decided", {"approval_id": approval.id, "decision": decision, "via": "review_link"})
    db.session.commit()
    return approval


def comment_via_link(token: str, name, body) -> DeliverableComment:
    name = (name or "").strip()[:120] if isinstance(name, str) else ""
    if not name:
        raise ValidationError("Please correct the highlighted fields.", details=[{"field": "name", "issue": "Required"}])
    link = _link_for_token(token)
    approval = db.session.get(Approval, link.approval_id)
    comment = DeliverableComment(organization_id=link.organization_id, deliverable_id=approval.deliverable_id,
                                 deliverable_version_id=approval.deliverable_version_id,
                                 external_author_name=name, review_link_id=link.id, body=_clean_body(body))
    db.session.add(comment)
    db.session.flush()
    record_audit_event(link.organization_id, "comment.added", actor_user_id=None, target_type="deliverable",
                       target_id=approval.deliverable_id, metadata={"via": "review_link", "review_link_id": link.id})
    from app.services.platform_service import notify

    notify(link.organization_id, "comment.external", f"New client comment from {name}", body=comment.body[:300])
    db.session.commit()
    return comment
