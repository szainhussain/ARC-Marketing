import json
import uuid

from app.extensions import db
from app.models.audit_event import AuditEvent


def record_audit_event(
    organization_id: str,
    action: str,
    actor_user_id: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    outcome: str = "success",
    metadata: dict | None = None,
    correlation_id: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        outcome=outcome,
        correlation_id=correlation_id or str(uuid.uuid4()),
        metadata_json=json.dumps(metadata or {}, default=str),
    )
    db.session.add(event)
    db.session.flush()
    return event
