from app.extensions import db
from app.models.approval import (
    ACTION_MANUAL_HANDOFF,
    DECISION_APPROVED,
    DECISION_CHANGES_REQUESTED,
    DECISION_PENDING,
    DECISION_REJECTED,
    Approval,
)
from app.models.approval import DECISION_EXPIRED, DECISION_REVOKED
from app.models.membership import Membership
from app.services.audit_service import record_audit_event
from app.services.deliverable_service import compute_action_payload_hash, get_deliverable_or_404
from app.services.errors import Conflict, NotFound, PermissionDenied, ValidationError

VALID_DECISION_INPUTS = (DECISION_APPROVED, DECISION_REJECTED, DECISION_CHANGES_REQUESTED)


def request_approval(
    organization_id: str,
    deliverable_id: str,
    requested_by_user_id: str,
    action_type: str = ACTION_MANUAL_HANDOFF,
    action_payload: dict | None = None,
) -> Approval:
    deliverable = get_deliverable_or_404(organization_id, deliverable_id)
    if deliverable.current_version_id is None:
        raise ValidationError("Deliverable has no content version to approve yet.")

    payload = {
        "action_type": action_type,
        "deliverable_id": deliverable.id,
        "version_id": deliverable.current_version_id,
        **(action_payload or {}),
    }

    existing = Approval.query.filter_by(
        organization_id=organization_id, deliverable_version_id=deliverable.current_version_id,
        action_type=action_type, decision=DECISION_PENDING,
    ).first()
    if existing:
        return existing  # one pending decision per exact version + action

    context = _approval_context(organization_id, deliverable)
    approval = Approval(
        organization_id=organization_id,
        deliverable_id=deliverable.id,
        deliverable_version_id=deliverable.current_version_id,
        action_type=action_type,
        action_payload_hash=compute_action_payload_hash(payload),
        requested_by_user_id=requested_by_user_id,
        **context,
    )
    db.session.add(approval)
    db.session.flush()
    from app.services.webhook_service import emit

    emit(organization_id, "approval.requested", {"approval_id": approval.id, "deliverable_id": deliverable.id,
                                                 "deliverable_type": deliverable.deliverable_type})
    record_audit_event(
        organization_id,
        "approval.requested",
        actor_user_id=requested_by_user_id,
        target_type="approval",
        target_id=approval.id,
    )
    db.session.commit()
    return approval


def get_approval_or_404(organization_id: str, approval_id: str) -> Approval:
    approval = Approval.query.filter_by(id=approval_id, organization_id=organization_id).first()
    if approval is None:
        raise NotFound("Approval not found.")
    return approval


def decide_approval(
    organization_id: str,
    approval_id: str,
    membership: Membership,
    decision: str,
    comment: str | None = None,
) -> Approval:
    if decision not in VALID_DECISION_INPUTS:
        raise ValidationError("Invalid decision.")

    if not membership.can_approve_external_actions():
        raise PermissionDenied("Your role does not permit approval decisions.")

    approval = get_approval_or_404(organization_id, approval_id)
    if approval.decision == DECISION_PENDING and _is_expired(approval):
        approval.decision = DECISION_EXPIRED
        db.session.commit()
        raise Conflict("This approval request expired. Request a new approval.")
    if approval.decision != DECISION_PENDING:
        raise Conflict(
            f"This approval is '{approval.decision}' and can no longer be decided.",
            details=[{"field": "decision", "issue": "stale_or_already_decided"}],
        )

    # Re-check the content version has not changed since the request (even
    # though add_new_version() already invalidates stale approvals, this is
    # a defense-in-depth re-check immediately before the decision is saved).
    deliverable = get_deliverable_or_404(organization_id, approval.deliverable_id)
    if deliverable.current_version_id != approval.deliverable_version_id:
        approval.decision = "invalidated"
        db.session.commit()
        raise Conflict("The deliverable changed after this approval was requested.")

    approval.decision = decision
    approval.decision_comment = comment
    approval.decided_by_user_id = membership.user_id
    from app.models.base import utcnow

    approval.decided_at = utcnow()
    db.session.flush()
    record_audit_event(
        organization_id,
        "approval.decided",
        actor_user_id=membership.user_id,
        target_type="approval",
        target_id=approval.id,
        metadata={"decision": decision},
    )
    from app.services.webhook_service import emit

    emit(organization_id, "approval.decided", {"approval_id": approval.id, "decision": decision})
    db.session.commit()
    return approval


# Deliverable types whose content is meant to be seen outside the company.
_EXTERNAL_FACING = {"content_pack", "social_calendar", "outreach_plan", "paid_media_plan",
                    "site_optimization_plan", "customer_insights"}


def _approval_context(organization_id: str, deliverable) -> dict:
    import json
    from datetime import timedelta

    from flask import current_app

    from app.models.agent_execution import AgentExecution
    from app.models.base import utcnow
    from app.models.task import Task

    task = Task.query.filter_by(organization_id=organization_id, deliverable_id=deliverable.id).first()
    checks = []
    if task:
        execution = (
            AgentExecution.query.filter_by(task_id=task.id, status="succeeded")
            .order_by(AgentExecution.finished_at.desc()).first()
        )
        if execution and execution.evaluation_json:
            checks = json.loads(execution.evaluation_json)
    failed = [c for c in checks if not c.get("passed")]
    external = deliverable.deliverable_type in _EXTERNAL_FACING
    risk = "high" if failed else ("medium" if external else "low")
    checks.append({"check": "version_bound", "passed": True,
                   "detail": "Approval is tied to this exact version; any edit invalidates it."})
    checks.append({"check": "no_auto_publish", "passed": True,
                   "detail": "Approving does not publish. It allows a manual export only."})
    return {
        "requesting_agent_id": task.agent_id if task else None,
        "expected_outcome": (
            "An export package is generated for you to copy into the destination platform yourself. "
            "Nothing is posted, sent or spent by ARC."
        ),
        "risk_level": risk,
        "risk_notes": json.dumps(checks),
        "expires_at": utcnow() + timedelta(days=current_app.config.get("APPROVAL_TTL_DAYS", 14)),
    }


def _is_expired(approval) -> bool:
    from datetime import timezone

    from app.models.base import utcnow

    if approval.expires_at is None:
        return False
    expires = approval.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    return expires < utcnow()


def revoke_approval(organization_id: str, approval_id: str, membership: Membership) -> Approval:
    """Withdraw an approval that hasn't been used yet."""

    from app.models.external_action import ExternalAction

    if not membership.can_approve_external_actions():
        raise PermissionDenied("Your role does not permit approval decisions.")
    approval = get_approval_or_404(organization_id, approval_id)
    if approval.decision != DECISION_APPROVED:
        raise Conflict("Only an approved, unused approval can be revoked.")
    if ExternalAction.query.filter_by(organization_id=organization_id, approval_id=approval.id).first():
        raise Conflict("This approval was already used for a handoff and can't be revoked.")
    approval.decision = DECISION_REVOKED
    record_audit_event(organization_id, "approval.revoked", actor_user_id=membership.user_id,
                       target_type="approval", target_id=approval.id)
    db.session.commit()
    return approval
