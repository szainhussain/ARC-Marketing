import json

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
# Set only by a live connector after it reads the item back from the
# platform itself (e.g. WordPress.com reports the post as published at a
# URL). Never set from a request, a webhook or an agent (docs/DECISIONS.md D17).
PUBLICATION_PLATFORM_VERIFIED = "platform_verified_published"
PUBLICATION_DRAFT_CREATED = "draft_created"

STATUS_QUEUED = "queued"


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
    # Optional: one of app.integrations.export_formats.PLATFORM_FORMATTERS'
    # keys, when this handoff was formatted for a specific ad/social
    # platform's composer. Null for a generic (platform-agnostic) export.
    target_platform = db.Column(db.String(32))
    response_metadata_json = db.Column(db.Text)
    # Live connectors (queued -> executing -> succeeded/failed, run by the worker)
    item_index = db.Column(db.Integer)
    attempts = db.Column(db.Integer, default=0, nullable=False, server_default="0")
    next_attempt_at = db.Column(db.DateTime(timezone=True))
    last_error = db.Column(db.String(500))
    external_reference = db.Column(db.String(128))
    external_url = db.Column(db.String(1000))
    publish_mode = db.Column(db.String(16))  # "publish" | "draft"
    requested_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id", name="fk_external_actions_requested_by"))

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
            "target_platform": self.target_platform,
            "platform_export": (
                json.loads(self.response_metadata_json).get("platform_export")
                if self.response_metadata_json
                else None
            ),
            "publication_status": self.publication_status,
            "publication_confirmed_at": (
                self.publication_confirmed_at.isoformat()
                if self.publication_confirmed_at
                else None
            ),
            "item_index": self.item_index,
            "external_url": self.external_url,
            "publish_mode": self.publish_mode,
            "last_error": self.last_error,
            "attempts": self.attempts,
            "created_at": self.created_at.isoformat(),
        }
