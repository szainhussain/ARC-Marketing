from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "organizations"

    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)
    status = db.Column(db.String(32), default="active", nullable=False)
    monthly_workflow_limit = db.Column(db.Integer, default=20, nullable=False)
    kill_switch_enabled = db.Column(db.Boolean, default=False, nullable=False)
    # Stops the worker from starting any new agent task in this workspace
    # (distinct from kill_switch_enabled, which blocks external actions).
    automation_paused = db.Column(db.Boolean, default=False, nullable=False)
    # Workspace-level execution limits enforced by the engine.
    default_run_budget_usd = db.Column(db.Float)  # null = platform default
    max_concurrent_tasks = db.Column(db.Integer, default=2, nullable=False)
    timezone = db.Column(db.String(64), default="UTC", nullable=False)
    # Workspace default accent for the app UI: an ACCENT_PRESETS name or "brand"
    # (the Brand Kit's primary colour). Null means ARC's default. Display only.
    accent_color = db.Column(db.String(16))
    deletion_scheduled_at = db.Column(db.DateTime(timezone=True))

    memberships = db.relationship(
        "Membership", back_populates="organization", cascade="all, delete-orphan"
    )
    business_profile = db.relationship(
        "BusinessProfile",
        back_populates="organization",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "status": self.status,
        }


ACCENT_PRESETS = ("arc", "indigo", "emerald", "amber", "rose", "violet")
ACCENT_CHOICES = ACCENT_PRESETS + ("brand",)
