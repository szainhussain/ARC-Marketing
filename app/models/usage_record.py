from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class UsageRecord(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "usage_records"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    workflow_run_id = db.Column(db.String(36), db.ForeignKey("workflow_runs.id"))
    provider = db.Column(db.String(64))
    model = db.Column(db.String(128))
    input_tokens = db.Column(db.Integer, default=0, nullable=False)
    output_tokens = db.Column(db.Integer, default=0, nullable=False)
    estimated_cost_usd = db.Column(db.Float, default=0.0, nullable=False)
    is_actual = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workflow_run_id": self.workflow_run_id,
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "is_actual": self.is_actual,
            "created_at": self.created_at.isoformat(),
        }
