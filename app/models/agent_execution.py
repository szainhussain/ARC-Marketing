import json

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

EXEC_RUNNING = "running"
EXEC_SUCCEEDED = "succeeded"
EXEC_FAILED = "failed"


class AgentExecution(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """One attempt by one agent at one task. Records which agent *version*
    produced an output, so a later registry change never makes an old
    deliverable look like it came from the new instructions."""

    __tablename__ = "agent_executions"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    task_id = db.Column(db.String(36), db.ForeignKey("tasks.id"), nullable=False, index=True)
    workflow_run_id = db.Column(db.String(36), db.ForeignKey("workflow_runs.id"), index=True)
    agent_id = db.Column(db.String(64), nullable=False, index=True)
    agent_version = db.Column(db.String(32), nullable=False)
    attempt_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(32), default=EXEC_RUNNING, nullable=False)
    provider = db.Column(db.String(64))
    model = db.Column(db.String(128))
    input_tokens = db.Column(db.Integer, default=0, nullable=False)
    output_tokens = db.Column(db.Integer, default=0, nullable=False)
    cached_input_tokens = db.Column(db.Integer, default=0, server_default="0", nullable=False)
    estimated_cost_usd = db.Column(db.Float, default=0.0, nullable=False)
    error_code = db.Column(db.String(64))
    error_summary = db.Column(db.Text)
    summary = db.Column(db.Text)
    # JSON list of {"check", "passed", "detail"} from app/workflows/evaluation.py.
    evaluation_json = db.Column(db.Text)
    correlation_id = db.Column(db.String(36))
    started_at = db.Column(db.DateTime(timezone=True))
    finished_at = db.Column(db.DateTime(timezone=True))

    def to_dict(self) -> dict:
        duration_ms = None
        if self.started_at and self.finished_at:
            duration_ms = int((self.finished_at - self.started_at).total_seconds() * 1000)
        return {
            "id": self.id,
            "task_id": self.task_id,
            "workflow_run_id": self.workflow_run_id,
            "agent_id": self.agent_id,
            "agent_version": self.agent_version,
            "attempt_number": self.attempt_number,
            "status": self.status,
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "error_code": self.error_code,
            "error_summary": self.error_summary,
            "summary": self.summary,
            "evaluation": json.loads(self.evaluation_json) if self.evaluation_json else [],
            "correlation_id": self.correlation_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_ms": duration_ms,
        }


class AgentSetting(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Per-workspace override for one agent. Absence of a row means the
    registry defaults apply (enabled, not paused, no extra budget cap)."""

    __tablename__ = "agent_settings"
    __table_args__ = (
        db.UniqueConstraint("organization_id", "agent_id", name="uq_agent_setting_org_agent"),
    )

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    agent_id = db.Column(db.String(64), nullable=False)
    is_paused = db.Column(db.Boolean, default=False, nullable=False)
    monthly_budget_usd = db.Column(db.Float)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "is_paused": self.is_paused,
            "monthly_budget_usd": self.monthly_budget_usd,
        }
