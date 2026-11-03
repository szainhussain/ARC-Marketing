from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

STATUS_PREPARED = "prepared"
STATUS_AWAITING_APPROVAL = "awaiting_approval"
STATUS_APPROVED = "approved"
STATUS_EXECUTING = "executing"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
STATUS_VERIFICATION_REQUIRED = "verification_required"
STATUS_CANCELLED = "cancelled"

# Publication is tracked separately from handoff/export status — exporting
# or copying content must never be reported as "published".
PUBLICATION_NOT_APPLICABLE = "not_applicable"
PUBLICATION_UNVERIFIED = "unverified"
PUBLICATION_MANUALLY_CONFIRMED = "manually_confirmed_published"


class ExternalAction(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "external_actions"
    __table_args__ = (
        db.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_external_action_org_idempotency"
        ),
    )

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    approval_id = db.Column(db.String(36), db.ForeignKey("approvals.id"), nullable=False)
    connector = db.Column(db.String(64), default="manual_handoff", nullable=False)
    idempotency_key = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(32), default=STATUS_PREPARED, nullable=False)
    response_metadata_json = db.Column(db.Text)

    publication_status = db.Column(
        db.String(32), default=PUBLICATION_NOT_APPLICABLE, nullable=False
    )
    publication_confirmed_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"))
    publication_confirmed_at = db.Column(db.DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "approval_id": self.approval_id,
            "connector": self.connector,
            "status": self.status,
            "publication_status": self.publication_status,
            "publication_confirmed_at": (
                self.publication_confirmed_at.isoformat()
                if self.publication_confirmed_at
                else None
            ),
            "created_at": self.created_at.isoformat(),
        }
