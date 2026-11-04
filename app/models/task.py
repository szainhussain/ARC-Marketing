from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

STATUS_QUEUED = "queued"
STATUS_WAITING_FOR_DEPENDENCY = "waiting_for_dependency"
STATUS_READY = "ready"
STATUS_RUNNING = "running"
STATUS_RETRYING = "retrying"
STATUS_WAITING_FOR_APPROVAL = "waiting_for_approval"
STATUS_SCHEDULED = "scheduled"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
STATUS_CANCELLED = "cancelled"

VALID_TASK_STATUSES = (
    STATUS_QUEUED,
    STATUS_WAITING_FOR_DEPENDENCY,
    STATUS_READY,
    STATUS_RUNNING,
    STATUS_RETRYING,
    STATUS_WAITING_FOR_APPROVAL,
    STATUS_SCHEDULED,
    STATUS_SUCCEEDED,
    STATUS_FAILED,
    STATUS_CANCELLED,
)

TERMINAL_TASK_STATUSES = (STATUS_SUCCEEDED, STATUS_FAILED, STATUS_CANCELLED)
CLAIMABLE_TASK_STATUSES = (STATUS_READY, STATUS_RETRYING)

# Allowed transitions, enforced by app/workflows/state_machine.apply_transition.
TASK_TRANSITIONS = {
    STATUS_QUEUED: {STATUS_WAITING_FOR_DEPENDENCY, STATUS_READY, STATUS_SCHEDULED, STATUS_CANCELLED},
    STATUS_WAITING_FOR_DEPENDENCY: {STATUS_READY, STATUS_CANCELLED},
    STATUS_SCHEDULED: {STATUS_READY, STATUS_CANCELLED},
    STATUS_READY: {STATUS_RUNNING, STATUS_CANCELLED},
    STATUS_RETRYING: {STATUS_RUNNING, STATUS_CANCELLED},
    STATUS_RUNNING: {
        STATUS_SUCCEEDED,
        STATUS_FAILED,
        STATUS_RETRYING,
        STATUS_WAITING_FOR_APPROVAL,
        STATUS_CANCELLED,
    },
    STATUS_WAITING_FOR_APPROVAL: {STATUS_SUCCEEDED, STATUS_CANCELLED},
    # A failed task may be retried by a person (resets attempts); nothing
    # retries a terminal failure automatically.
    STATUS_FAILED: {STATUS_READY, STATUS_CANCELLED},
    STATUS_SUCCEEDED: set(),
    STATUS_CANCELLED: set(),
}


class TaskDependency(db.Model):
    __tablename__ = "task_dependencies"

    task_id = db.Column(db.String(36), db.ForeignKey("tasks.id"), primary_key=True)
    depends_on_task_id = db.Column(db.String(36), db.ForeignKey("tasks.id"), primary_key=True)


class Task(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "tasks"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    campaign_id = db.Column(db.String(36), db.ForeignKey("campaigns.id"), nullable=False)
    workflow_run_id = db.Column(db.String(36), db.ForeignKey("workflow_runs.id"), index=True)

    agent_id = db.Column(db.String(64), index=True)
    task_type = db.Column(db.String(64))
    title = db.Column(db.String(255))
    # Kept for compatibility with earlier records; equals agent_id for new tasks.
    stage = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(32), default=STATUS_QUEUED, nullable=False, index=True)
    priority = db.Column(db.Integer, default=100, nullable=False)
    sequence_index = db.Column(db.Integer, nullable=False, default=0)
    attempt_count = db.Column(db.Integer, default=0, nullable=False)
    max_attempts = db.Column(db.Integer, default=4, nullable=False)
    next_attempt_at = db.Column(db.DateTime(timezone=True))
    lease_expires_at = db.Column(db.DateTime(timezone=True))
    last_error_code = db.Column(db.String(64))
    error_summary = db.Column(db.Text)
    deliverable_id = db.Column(
        db.String(36),
        db.ForeignKey("deliverables.id", use_alter=True, name="fk_task_deliverable"),
    )
    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))

    campaign = db.relationship("Campaign", back_populates="tasks")
    workflow_run = db.relationship("WorkflowRun", back_populates="tasks")
    dependencies = db.relationship(
        "Task",
        secondary="task_dependencies",
        primaryjoin="Task.id == TaskDependency.task_id",
        secondaryjoin="Task.id == TaskDependency.depends_on_task_id",
        lazy="selectin",
    )

    def to_dict(self) -> dict:
        from app.agents.registry import get_agent

        spec = get_agent(self.agent_id) if self.agent_id else None
        return {
            "id": self.id,
            "agent_name": spec.name if spec else self.stage,
            "agent_number": spec.number if spec else None,
            "campaign_id": self.campaign_id,
            "workflow_run_id": self.workflow_run_id,
            "agent_id": self.agent_id or self.stage,
            "task_type": self.task_type,
            "title": self.title,
            "stage": self.stage,
            "status": self.status,
            "priority": self.priority,
            "sequence_index": self.sequence_index,
            "attempt_count": self.attempt_count,
            "max_attempts": self.max_attempts,
            "next_attempt_at": self.next_attempt_at.isoformat() if self.next_attempt_at else None,
            "last_error_code": self.last_error_code,
            "error_summary": self.error_summary,
            "deliverable_id": self.deliverable_id,
            "depends_on": [d.id for d in self.dependencies],
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
