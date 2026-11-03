import hashlib
import json

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin, new_uuid, utcnow

TYPE_STRATEGY = "strategy"
TYPE_RESEARCH_NOTES = "research_notes"
TYPE_CAMPAIGN_PLAN = "campaign_plan"
TYPE_CONTENT_PACK = "content_pack"
TYPE_QA_REPORT = "qa_report"

VALID_DELIVERABLE_TYPES = (
    TYPE_STRATEGY,
    TYPE_RESEARCH_NOTES,
    TYPE_CAMPAIGN_PLAN,
    TYPE_CONTENT_PACK,
    TYPE_QA_REPORT,
)

REVIEW_DRAFT = "draft"
REVIEW_CHANGES_REQUESTED = "changes_requested"
REVIEW_APPROVED = "approved"
REVIEW_REJECTED = "rejected"


class Deliverable(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """A logical deliverable slot (e.g. "campaign plan for campaign X").

    The current content always lives in `current_version`; editing never
    mutates a version in place, it creates a new DeliverableVersion and
    repoints current_version_id (see services/deliverable_service.py).
    """

    __tablename__ = "deliverables"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    campaign_id = db.Column(db.String(36), db.ForeignKey("campaigns.id"), nullable=False)
    workflow_run_id = db.Column(db.String(36), db.ForeignKey("workflow_runs.id"))
    deliverable_type = db.Column(db.String(64), nullable=False)
    current_version_id = db.Column(
        db.String(36),
        db.ForeignKey("deliverable_versions.id", use_alter=True, name="fk_deliverable_current_version"),
    )
    review_status = db.Column(db.String(32), default=REVIEW_DRAFT, nullable=False)

    campaign = db.relationship("Campaign", back_populates="deliverables")
    workflow_run = db.relationship("WorkflowRun", back_populates="deliverables")
    current_version = db.relationship(
        "DeliverableVersion", foreign_keys=[current_version_id], post_update=True
    )
    versions = db.relationship(
        "DeliverableVersion",
        back_populates="deliverable",
        foreign_keys="DeliverableVersion.deliverable_id",
        order_by="DeliverableVersion.version_number",
    )

    def to_dict(self, include_versions: bool = False) -> dict:
        data = {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "workflow_run_id": self.workflow_run_id,
            "deliverable_type": self.deliverable_type,
            "review_status": self.review_status,
            "current_version": self.current_version.to_dict() if self.current_version else None,
        }
        if include_versions:
            data["versions"] = [v.to_dict() for v in self.versions]
        return data


class DeliverableVersion(UUIDPrimaryKeyMixin, db.Model):
    """Immutable content snapshot. Never update fields in place after create."""

    __tablename__ = "deliverable_versions"

    deliverable_id = db.Column(
        db.String(36), db.ForeignKey("deliverables.id"), nullable=False, index=True
    )
    version_number = db.Column(db.Integer, nullable=False)
    content_json = db.Column(db.Text, nullable=False)
    schema_version = db.Column(db.String(32), default="v1", nullable=False)
    content_hash = db.Column(db.String(64), nullable=False)
    created_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"))
    created_by_run_id = db.Column(db.String(36), db.ForeignKey("workflow_runs.id"))
    revision_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    deliverable = db.relationship(
        "Deliverable", back_populates="versions", foreign_keys=[deliverable_id]
    )

    @staticmethod
    def compute_hash(content_json: str) -> str:
        return hashlib.sha256(content_json.encode("utf-8")).hexdigest()

    @classmethod
    def build(
        cls,
        deliverable_id: str,
        version_number: int,
        content: dict,
        created_by_user_id: str | None = None,
        created_by_run_id: str | None = None,
        revision_reason: str | None = None,
    ) -> "DeliverableVersion":
        content_json = json.dumps(content, sort_keys=True)
        return cls(
            id=new_uuid(),
            deliverable_id=deliverable_id,
            version_number=version_number,
            content_json=content_json,
            content_hash=cls.compute_hash(content_json),
            created_by_user_id=created_by_user_id,
            created_by_run_id=created_by_run_id,
            revision_reason=revision_reason,
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "deliverable_id": self.deliverable_id,
            "version_number": self.version_number,
            "content": json.loads(self.content_json),
            "schema_version": self.schema_version,
            "content_hash": self.content_hash,
            "revision_reason": self.revision_reason,
            "created_at": self.created_at.isoformat(),
        }
