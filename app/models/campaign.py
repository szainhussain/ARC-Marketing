from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

STATUS_DRAFT = "draft"
STATUS_ACTIVE = "active"
STATUS_ARCHIVED = "archived"

VALID_STATUSES = (STATUS_DRAFT, STATUS_ACTIVE, STATUS_ARCHIVED)


class Campaign(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "campaigns"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    created_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)

    name = db.Column(db.String(255), nullable=False)
    objective = db.Column(db.Text, nullable=False)
    audience = db.Column(db.Text)
    offer = db.Column(db.Text)
    geography = db.Column(db.String(255))
    channels = db.Column(db.String(500))  # comma-separated for MVP
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    budget_guidance = db.Column(db.String(255))
    constraints = db.Column(db.Text)
    success_metrics = db.Column(db.Text)

    status = db.Column(db.String(32), default=STATUS_DRAFT, nullable=False)
    idempotency_key = db.Column(db.String(255), index=True)

    __table_args__ = (
        db.UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_campaign_org_idempotency"
        ),
    )

    tasks = db.relationship("Task", back_populates="campaign", cascade="all, delete-orphan")
    workflow_runs = db.relationship(
        "WorkflowRun", back_populates="campaign", cascade="all, delete-orphan"
    )
    deliverables = db.relationship(
        "Deliverable", back_populates="campaign", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "name": self.name,
            "objective": self.objective,
            "audience": self.audience,
            "offer": self.offer,
            "geography": self.geography,
            "channels": self.channels,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "budget_guidance": self.budget_guidance,
            "constraints": self.constraints,
            "success_metrics": self.success_metrics,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
