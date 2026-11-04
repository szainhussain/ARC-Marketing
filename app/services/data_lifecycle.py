"""Workspace data export and permanent deletion (after the grace period).

Deletion order follows foreign keys: children first. Audit events are
deleted last with the workspace, since they are tenant data too; the
purge itself is logged to the server log (not to tenant tables)."""

import json
import logging

from app.extensions import db
from app.models.agent_execution import AgentExecution, AgentSetting
from app.models.approval import Approval
from app.models.audit_event import AuditEvent
from app.models.base import utcnow
from app.models.billing import BillingEvent, WebhookDelivery, WebhookEndpoint
from app.models.business_profile import BusinessProfile
from app.models.campaign import Campaign
from app.models.deliverable import Deliverable, DeliverableVersion
from app.models.document import Document
from app.models.external_action import ExternalAction
from app.models.integration import Integration
from app.models.membership import Membership
from app.models.organization import Organization
from app.models.platform import (
    ActionPolicy,
    CalendarEntry,
    Invitation,
    KnowledgeEntry,
    Notification,
    Subscription,
)
from app.models.task import Task, TaskDependency
from app.models.usage_record import UsageRecord
from app.models.workflow_run import WorkflowRun

log = logging.getLogger(__name__)


def _rows(model, org_id):
    return [_serialize(r) for r in model.query.filter_by(organization_id=org_id).all()]


def _serialize(row):
    out = {}
    for col in row.__table__.columns:
        if col.name in ("secret", "token_hash", "password_hash", "encrypted_credential_ref", "storage_key"):
            continue  # never export secrets or internal storage paths
        value = getattr(row, col.name)
        out[col.name] = value.isoformat() if hasattr(value, "isoformat") else value
    if "content_json" in out:
        out["content"] = json.loads(out.pop("content_json"))
    return out


def export_workspace(org_id: str) -> dict:
    org = db.session.get(Organization, org_id)
    deliverable_ids = [d.id for d in Deliverable.query.filter_by(organization_id=org_id)]
    return {
        "format": "arc-workspace-export/1",
        "exported_at": utcnow().isoformat(),
        "workspace": _serialize(org),
        "business_profile": [_serialize(p) for p in BusinessProfile.query.filter_by(organization_id=org_id)],
        "members": [{"email": m.user.email, "full_name": m.user.full_name, "role": m.role}
                    for m in Membership.query.filter_by(organization_id=org_id)],
        "campaigns": _rows(Campaign, org_id),
        "workflow_runs": _rows(WorkflowRun, org_id),
        "tasks": _rows(Task, org_id),
        "agent_executions": _rows(AgentExecution, org_id),
        "deliverables": _rows(Deliverable, org_id),
        "deliverable_versions": [_serialize(v) for v in DeliverableVersion.query.filter(
            DeliverableVersion.deliverable_id.in_(deliverable_ids))] if deliverable_ids else [],
        "approvals": _rows(Approval, org_id),
        "external_actions": _rows(ExternalAction, org_id),
        "knowledge": _rows(KnowledgeEntry, org_id),
        "calendar": _rows(CalendarEntry, org_id),
        "documents": _rows(Document, org_id),
        "usage": _rows(UsageRecord, org_id),
        "audit_events": _rows(AuditEvent, org_id),
    }


def purge_workspace(org_id: str) -> None:
    from app.storage import get_storage

    task_ids = [t.id for t in Task.query.filter_by(organization_id=org_id)]
    deliverable_ids = [d.id for d in Deliverable.query.filter_by(organization_id=org_id)]
    storage = get_storage()
    for doc in Document.query.filter_by(organization_id=org_id):
        storage.delete(doc.storage_key)
    if task_ids:
        TaskDependency.query.filter(TaskDependency.task_id.in_(task_ids)).delete(synchronize_session=False)
    for model in (WebhookDelivery, WebhookEndpoint, Notification, Invitation, ActionPolicy, CalendarEntry,
                  KnowledgeEntry, ExternalAction, Approval, AgentExecution, UsageRecord, AgentSetting,
                  Integration, Document):
        model.query.filter_by(organization_id=org_id).delete(synchronize_session=False)
    Task.query.filter_by(organization_id=org_id).update({"deliverable_id": None}, synchronize_session=False)
    if deliverable_ids:
        Deliverable.query.filter(Deliverable.id.in_(deliverable_ids)).update(
            {"current_version_id": None}, synchronize_session=False)
        DeliverableVersion.query.filter(DeliverableVersion.deliverable_id.in_(deliverable_ids)).delete(
            synchronize_session=False)
    for model in (Deliverable, Task, WorkflowRun, Campaign, BusinessProfile, Subscription, Membership, AuditEvent):
        model.query.filter_by(organization_id=org_id).delete(synchronize_session=False)
    BillingEvent.query.filter_by(organization_id=org_id).update({"organization_id": None}, synchronize_session=False)
    Organization.query.filter_by(id=org_id).delete(synchronize_session=False)
    db.session.commit()
    log.warning("Purged workspace %s", org_id)


def purge_due_workspaces() -> int:
    due = Organization.query.filter(Organization.status == "deletion_scheduled",
                                    Organization.deletion_scheduled_at <= utcnow()).all()
    for org in due:
        purge_workspace(org.id)
    return len(due)
