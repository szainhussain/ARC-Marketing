from app.extensions import db
from app.models.approval import (
    ACTION_MANUAL_HANDOFF,
    DECISION_APPROVED,
    DECISION_CHANGES_REQUESTED,
    DECISION_PENDING,
    DECISION_REJECTED,
    Approval,
)
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

    approval = Approval(
        organization_id=organization_id,
        deliverable_id=deliverable.id,
        deliverable_version_id=deliverable.current_version_id,
        action_type=action_type,
        action_payload_hash=compute_action_payload_hash(payload),
        requested_by_user_id=requested_by_user_id,
    )
    db.session.add(approval)
    db.session.flush()
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
    db.session.commit()
    return approval
