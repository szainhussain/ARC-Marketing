from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

STATUS_CREATED = "created"
STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_NEEDS_INPUT = "needs_input"
STATUS_AWAITING_APPROVAL = "awaiting_approval"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

VALID_RUN_STATUSES = (
    STATUS_CREATED,
    STATUS_QUEUED,
    STATUS_RUNNING,
    STATUS_NEEDS_INPUT,
    STATUS_AWAITING_APPROVAL,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_CANCELLED,
)

RUN_TRANSITIONS = {
    STATUS_CREATED: {STATUS_QUEUED, STATUS_CANCELLED},
    STATUS_QUEUED: {STATUS_RUNNING, STATUS_CANCELLED},
    STATUS_RUNNING: {
        STATUS_NEEDS_INPUT,
        STATUS_AWAITING_APPROVAL,
        STATUS_COMPLETED,
        STATUS_FAILED,
        STATUS_CANCELLED,
    },
    STATUS_NEEDS_INPUT: {STATUS_QUEUED, STATUS_CANCELLED},
    STATUS_AWAITING_APPROVAL: {STATUS_COMPLETED, STATUS_CANCELLED},
    STATUS_FAILED: set(),
    STATUS_COMPLETED: set(),
    STATUS_CANCELLED: set(),
}


class WorkflowRun(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        db.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_run_org_idempotency"
        ),
    )

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    campaign_id = db.Column(db.String(36), db.ForeignKey("campaigns.id"), nullable=False)
    started_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)

    workflow_type = db.Column(db.String(64), default="campaign_pack_v1", nullable=False)
    status = db.Column(db.String(32), default=STATUS_CREATED, nullable=False)
    idempotency_key = db.Column(db.String(255), nullable=False)
    error_summary = db.Column(db.Text)
    estimated_cost_usd = db.Column(db.Float, default=0.0, nullable=False)
    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))

    campaign = db.relationship("Campaign", back_populates="workflow_runs")
    tasks = db.relationship("Task", back_populates="workflow_run")
    deliverables = db.relationship("Deliverable", back_populates="workflow_run")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "workflow_type": self.workflow_type,
            "status": self.status,
            "error_summary": self.error_summary,
            "estimated_cost_usd": self.estimated_cost_usd,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tasks": [t.to_dict() for t in sorted(self.tasks, key=lambda t: t.sequence_index)],
        }
