from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

DECISION_PENDING = "pending"
DECISION_APPROVED = "approved"
DECISION_REJECTED = "rejected"
DECISION_CHANGES_REQUESTED = "changes_requested"
DECISION_INVALIDATED = "invalidated"  # content changed after approval was requested

VALID_DECISIONS = (
    DECISION_PENDING,
    DECISION_APPROVED,
    DECISION_REJECTED,
    DECISION_CHANGES_REQUESTED,
    DECISION_INVALIDATED,
)

ACTION_MANUAL_HANDOFF = "manual_handoff"


class Approval(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """An approval request tied to an exact deliverable version and action.

    Per governance rules: approval is tied to content_version_id + the
    action_payload_hash together. If the deliverable's current version
    changes after the approval is requested, the approval becomes invalid
    (see services/approval_service.py) and cannot be used to execute.
    """

    __tablename__ = "approvals"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    deliverable_id = db.Column(db.String(36), db.ForeignKey("deliverables.id"), nullable=False)
    deliverable_version_id = db.Column(
        db.String(36), db.ForeignKey("deliverable_versions.id"), nullable=False
    )
    action_type = db.Column(db.String(64), default=ACTION_MANUAL_HANDOFF, nullable=False)
    action_payload_hash = db.Column(db.String(64), nullable=False)

    requested_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    decided_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"))
    decision = db.Column(db.String(32), default=DECISION_PENDING, nullable=False)
    decision_comment = db.Column(db.Text)
    decided_at = db.Column(db.DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "deliverable_id": self.deliverable_id,
            "deliverable_version_id": self.deliverable_version_id,
            "action_type": self.action_type,
            "action_payload_hash": self.action_payload_hash,
            "decision": self.decision,
            "decision_comment": self.decision_comment,
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "created_at": self.created_at.isoformat(),
        }
