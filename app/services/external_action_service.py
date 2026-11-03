from flask import current_app

from app.extensions import db
from app.integrations.manual_handoff import ManualHandoffConnector
from app.models.approval import DECISION_APPROVED
from app.models.base import utcnow
from app.models.deliverable import Deliverable
from app.models.external_action import (
    PUBLICATION_MANUALLY_CONFIRMED,
    PUBLICATION_UNVERIFIED,
    STATUS_SUCCEEDED,
    ExternalAction,
)
from app.models.organization import Organization
from app.services.approval_service import get_approval_or_404
from app.services.audit_service import record_audit_event
from app.services.errors import Conflict, NotFound, PermissionDenied, ValidationError

_connector = ManualHandoffConnector()


def execute_manual_handoff(
    organization_id: str, approval_id: str, user_id: str, idempotency_key: str
) -> ExternalAction:
    """Revalidates everything immediately before "executing" (packaging)
    the approved content, per the non-negotiable governance rules: kill
    switch, approval decision, and content-version match are all rechecked
    here rather than trusted from an earlier screen."""

    if not idempotency_key:
        raise ValidationError("An idempotency key is required.")

    existing = ExternalAction.query.filter_by(
        organization_id=organization_id, idempotency_key=idempotency_key
    ).first()
    if existing:
        return existing

    org = db.session.get(Organization, organization_id)
    if org is None:
        raise NotFound("Organization not found.")
    if org.kill_switch_enabled or current_app.config.get("KILL_SWITCH_ENABLED"):
        raise PermissionDenied("External actions are currently disabled by the kill switch.")

    approval = get_approval_or_404(organization_id, approval_id)
    if approval.decision != DECISION_APPROVED:
        raise Conflict("This action has not been approved.")

    deliverable = Deliverable.query.filter_by(
        id=approval.deliverable_id, organization_id=organization_id
    ).first()
    if deliverable is None or deliverable.current_version_id != approval.deliverable_version_id:
        raise Conflict(
            "The deliverable has changed since approval; this action can no longer execute."
        )

    content = deliverable.current_version.to_dict()["content"]
    action_payload = {"content": content}
    _connector.validate_action(action_payload)
    result = _connector.execute_action(action_payload, idempotency_key)

    action = ExternalAction(
        organization_id=organization_id,
        approval_id=approval.id,
        connector=_connector.name,
        idempotency_key=idempotency_key,
        status=STATUS_SUCCEEDED,  # the export package was produced
        publication_status=PUBLICATION_UNVERIFIED,
    )
    db.session.add(action)
    db.session.flush()
    record_audit_event(
        organization_id,
        "external_action.handed_off",
        actor_user_id=user_id,
        target_type="external_action",
        target_id=action.id,
        metadata={"result": result},
    )
    db.session.commit()
    return action


def get_external_action_or_404(organization_id: str, action_id: str) -> ExternalAction:
    action = ExternalAction.query.filter_by(
        id=action_id, organization_id=organization_id
    ).first()
    if action is None:
        raise NotFound("External action not found.")
    return action


def confirm_manual_publication(organization_id: str, action_id: str, user_id: str) -> ExternalAction:
    """The only way publication_status can become
    'manually_confirmed_published' — never automatically, since the
    manual-handoff connector has no way to verify a human actually posted
    the content."""

    action = get_external_action_or_404(organization_id, action_id)
    action.publication_status = PUBLICATION_MANUALLY_CONFIRMED
    action.publication_confirmed_by_user_id = user_id
    action.publication_confirmed_at = utcnow()
    db.session.flush()
    record_audit_event(
        organization_id,
        "external_action.publication_confirmed",
        actor_user_id=user_id,
        target_type="external_action",
        target_id=action.id,
    )
    db.session.commit()
    return action
