import json

from flask import current_app

from app.extensions import db
from app.integrations.export_formats import PLATFORM_FORMATTERS, format_content_pack_for_platform
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
    organization_id: str,
    approval_id: str,
    user_id: str,
    idempotency_key: str,
    target_platform: str | None = None,
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

    from app.services.platform_service import check_entitlement

    check_entitlement(organization_id, "monthly_exports")

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

    if target_platform is not None:
        from app.models.integration import Integration

        disabled = Integration.query.filter_by(
            organization_id=organization_id, provider=f"manual_export:{target_platform}", state="disabled"
        ).first()
        if disabled:
            raise PermissionDenied("This export destination is disabled for the workspace.")

    if target_platform is not None and target_platform not in PLATFORM_FORMATTERS:
        raise ValidationError(
            "Please correct the highlighted fields.",
            details=[{"field": "target_platform", "issue": "Unknown platform"}],
        )

    content = deliverable.current_version.to_dict()["content"]
    action_payload = {"content": content}
    _connector.validate_action(action_payload)
    result = _connector.execute_action(action_payload, idempotency_key)

    # Platform formatting is a presentation/export concern layered on top
    # of the already-approved content, it does not change what was
    # approved (the approval's payload hash covers deliverable content
    # only, not the target platform), and it never calls any external
    # platform API. See app/integrations/export_formats.py.
    if target_platform is not None and deliverable.deliverable_type == "content_pack":
        result["platform_export"] = format_content_pack_for_platform(content, target_platform)

    action = ExternalAction(
        organization_id=organization_id,
        approval_id=approval.id,
        connector=_connector.name,
        idempotency_key=idempotency_key,
        status=STATUS_SUCCEEDED,  # the export package was produced
        publication_status=PUBLICATION_UNVERIFIED,
        target_platform=target_platform,
        response_metadata_json=json.dumps(result, default=str),
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
    _emit_publishing_event(organization_id, action, approval, deliverable, content, result)
    db.session.commit()
    return action


def _emit_publishing_event(organization_id, action, approval, deliverable, content, result) -> int:
    """Send the exact approved content to Zapier/Make/any subscribed webhook.
    Queued here, delivered by the worker; publication stays 'unverified'
    until a person confirms it, whatever the automation does with it."""

    from app.models.campaign import Campaign
    from app.services.webhook_service import emit

    campaign = db.session.get(Campaign, deliverable.campaign_id)
    origin = current_app.config.get("FRONTEND_ORIGIN", "")
    return emit(organization_id, "content.approved_for_publishing", {
        "external_action_id": action.id,
        "approval_id": approval.id,
        "deliverable_id": deliverable.id,
        "deliverable_type": deliverable.deliverable_type,
        "version_number": deliverable.current_version.version_number,
        "campaign": {"id": deliverable.campaign_id, "name": campaign.name if campaign else None},
        "target_platform": action.target_platform,
        "approved_by": approval.decided_by_external_name or ("workspace member" if approval.decided_by_user_id else None),
        "content": content,
        "platform_export": result.get("platform_export"),
        "confirm_publication_url": f"{origin}/app/campaigns/{deliverable.campaign_id}/deliverables",
    })


def get_external_action_or_404(organization_id: str, action_id: str) -> ExternalAction:
    action = ExternalAction.query.filter_by(
        id=action_id, organization_id=organization_id
    ).first()
    if action is None:
        raise NotFound("External action not found.")
    return action


def confirm_manual_publication(organization_id: str, action_id: str, user_id: str) -> ExternalAction:
    """The only way publication_status can become
    'manually_confirmed_published', never automatically, since the
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
