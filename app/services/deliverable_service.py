import hashlib
import json

from app.extensions import db
from app.models.approval import Approval, DECISION_INVALIDATED, DECISION_PENDING
from app.models.deliverable import (
    REVIEW_DRAFT,
    Deliverable,
    DeliverableVersion,
)
from app.services.audit_service import record_audit_event
from app.services.errors import NotFound


def create_deliverable_with_first_version(
    organization_id: str,
    campaign_id: str,
    workflow_run_id: str,
    deliverable_type: str,
    content: dict,
    created_by_run_id: str | None = None,
) -> Deliverable:
    deliverable = Deliverable(
        organization_id=organization_id,
        campaign_id=campaign_id,
        workflow_run_id=workflow_run_id,
        deliverable_type=deliverable_type,
        review_status=REVIEW_DRAFT,
    )
    db.session.add(deliverable)
    db.session.flush()

    version = DeliverableVersion.build(
        deliverable_id=deliverable.id,
        version_number=1,
        content=content,
        created_by_run_id=created_by_run_id,
    )
    db.session.add(version)
    db.session.flush()

    deliverable.current_version_id = version.id
    db.session.flush()
    return deliverable


def get_deliverable_or_404(organization_id: str, deliverable_id: str) -> Deliverable:
    deliverable = Deliverable.query.filter_by(
        id=deliverable_id, organization_id=organization_id
    ).first()
    if deliverable is None:
        raise NotFound("Deliverable not found.")
    return deliverable


def add_new_version(
    organization_id: str,
    deliverable_id: str,
    content: dict,
    user_id: str,
    revision_reason: str | None = None,
) -> Deliverable:
    """Editing never mutates a version; it always creates a new one and
    invalidates any approval tied to the previous version."""

    deliverable = get_deliverable_or_404(organization_id, deliverable_id)
    next_number = max((v.version_number for v in deliverable.versions), default=0) + 1

    version = DeliverableVersion.build(
        deliverable_id=deliverable.id,
        version_number=next_number,
        content=content,
        created_by_user_id=user_id,
        revision_reason=revision_reason,
    )
    db.session.add(version)
    db.session.flush()

    previous_version_id = deliverable.current_version_id
    deliverable.current_version_id = version.id
    deliverable.review_status = REVIEW_DRAFT

    # A material change invalidates any pending approval tied to the
    # previous version.
    if previous_version_id:
        stale = Approval.query.filter_by(
            deliverable_id=deliverable.id,
            deliverable_version_id=previous_version_id,
            decision=DECISION_PENDING,
        ).all()
        for approval in stale:
            approval.decision = DECISION_INVALIDATED

    db.session.flush()
    record_audit_event(
        organization_id,
        "deliverable.version_created",
        actor_user_id=user_id,
        target_type="deliverable",
        target_id=deliverable.id,
        metadata={"version_number": next_number},
    )
    db.session.commit()
    return deliverable


def compute_action_payload_hash(action_payload: dict) -> str:
    serialized = json.dumps(action_payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
