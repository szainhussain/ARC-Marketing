from app.extensions import db
from app.models.base import UUIDPrimaryKeyMixin, utcnow


class AuditEvent(UUIDPrimaryKeyMixin, db.Model):
    """Append-only audit trail. Application code must never update or
    delete rows in this table; only inserts are permitted."""

    __tablename__ = "audit_events"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    actor_user_id = db.Column(db.String(36), db.ForeignKey("users.id"))
    action = db.Column(db.String(128), nullable=False)
    target_type = db.Column(db.String(64))
    target_id = db.Column(db.String(36))
    correlation_id = db.Column(db.String(36))
    outcome = db.Column(db.String(32), default="success", nullable=False)
    metadata_json = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "actor_user_id": self.actor_user_id,
            "action": self.action,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "correlation_id": self.correlation_id,
            "outcome": self.outcome,
            "created_at": self.created_at.isoformat(),
        }
