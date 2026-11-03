from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

STATUS_PENDING = "pending"
STATUS_READY = "ready"
STATUS_RUNNING = "running"
STATUS_NEEDS_INPUT = "needs_input"
STATUS_AWAITING_APPROVAL = "awaiting_approval"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

VALID_TASK_STATUSES = (
    STATUS_PENDING,
    STATUS_READY,
    STATUS_RUNNING,
    STATUS_NEEDS_INPUT,
    STATUS_AWAITING_APPROVAL,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_CANCELLED,
)

# Allowed transitions for the Task state machine (see docs/ARCHITECTURE.md).
TASK_TRANSITIONS = {
    STATUS_PENDING: {STATUS_READY, STATUS_CANCELLED},
    STATUS_READY: {STATUS_RUNNING, STATUS_CANCELLED},
    STATUS_RUNNING: {
        STATUS_NEEDS_INPUT,
        STATUS_AWAITING_APPROVAL,
        STATUS_COMPLETED,
        STATUS_FAILED,
        STATUS_CANCELLED,
    },
    STATUS_NEEDS_INPUT: {STATUS_READY, STATUS_CANCELLED},
    STATUS_AWAITING_APPROVAL: {STATUS_COMPLETED, STATUS_CANCELLED},
    STATUS_FAILED: {STATUS_READY, STATUS_CANCELLED},
    STATUS_COMPLETED: set(),
    STATUS_CANCELLED: set(),
}


class Task(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "tasks"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    campaign_id = db.Column(db.String(36), db.ForeignKey("campaigns.id"), nullable=False)
    workflow_run_id = db.Column(db.String(36), db.ForeignKey("workflow_runs.id"))

    stage = db.Column(db.String(64), nullable=False)  # e.g. cmo_planner, research_analyst
    status = db.Column(db.String(32), default=STATUS_PENDING, nullable=False)
    sequence_index = db.Column(db.Integer, nullable=False, default=0)
    attempt_count = db.Column(db.Integer, default=0, nullable=False)
    error_summary = db.Column(db.Text)
    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))

    campaign = db.relationship("Campaign", back_populates="tasks")
    workflow_run = db.relationship("WorkflowRun", back_populates="tasks")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "workflow_run_id": self.workflow_run_id,
            "stage": self.stage,
            "status": self.status,
            "sequence_index": self.sequence_index,
            "attempt_count": self.attempt_count,
            "error_summary": self.error_summary,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
