"""Human-approved ad launching with a hard daily cap (Phase 2, D19).

Agents still can never spend: an ad is launched only by a person, from an
approved paid-media plan, after a second approval that re-types the daily
budget. The worker re-checks everything before launching and keeps checking
while ads run (kill switch, workspace cap, end date)."""

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

AD_PENDING = "pending_approval"
AD_APPROVED = "approved"  # queued for the worker to launch
AD_ACTIVE = "active"
AD_PAUSED = "paused"
AD_STOPPED = "stopped"
AD_REJECTED = "rejected"
AD_FAILED = "failed"
LIVE_STATES = (AD_APPROVED, AD_ACTIVE, AD_PAUSED)


class AdGuardrail(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "ad_guardrails"
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id", name="fk_ad_guardrails_org"), nullable=False, unique=True)
    max_daily_budget = db.Column(db.Float, nullable=False, default=0.0)  # 0 = launching off
    currency = db.Column(db.String(3), nullable=False, default="USD")
    updated_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id", name="fk_ad_guardrails_updated_by"))


class AdLaunch(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "ad_launches"
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id", name="fk_ad_launches_org"), nullable=False, index=True)
    deliverable_id = db.Column(db.String(36), db.ForeignKey("deliverables.id", name="fk_ad_launches_deliverable"), nullable=False)
    deliverable_version_id = db.Column(db.String(36), db.ForeignKey("deliverable_versions.id", name="fk_ad_launches_version"), nullable=False)
    item_index = db.Column(db.Integer, nullable=False)
    platform = db.Column(db.String(32), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    channel = db.Column(db.String(64))
    objective = db.Column(db.String(200))
    audience = db.Column(db.Text)
    daily_budget = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(24), nullable=False, default=AD_PENDING, index=True)
    approval_hash = db.Column(db.String(64), nullable=False)
    requested_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id", name="fk_ad_launches_requested_by"), nullable=False)
    approved_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id", name="fk_ad_launches_approved_by"))
    approved_at = db.Column(db.DateTime(timezone=True))
    external_id = db.Column(db.String(128))
    launched_at = db.Column(db.DateTime(timezone=True))
    stopped_at = db.Column(db.DateTime(timezone=True))
    stop_reason = db.Column(db.String(300))
    desired_state = db.Column(db.String(16))  # what a person asked for: active | paused | stopped
    spend_today = db.Column(db.Float, default=0.0, nullable=False)
    spend_total = db.Column(db.Float, default=0.0, nullable=False)
    last_checked_at = db.Column(db.DateTime(timezone=True))
    last_error = db.Column(db.String(500))

    def to_dict(self) -> dict:
        return {"id": self.id, "deliverable_id": self.deliverable_id, "item_index": self.item_index, "platform": self.platform,
                "name": self.name, "channel": self.channel, "objective": self.objective, "audience": self.audience,
                "daily_budget": self.daily_budget, "currency": self.currency, "end_date": self.end_date.isoformat(),
                "status": self.status, "approved_at": self.approved_at.isoformat() if self.approved_at else None,
                "launched_at": self.launched_at.isoformat() if self.launched_at else None,
                "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None, "stop_reason": self.stop_reason,
                "spend_today": round(self.spend_today or 0, 2), "spend_total": round(self.spend_total or 0, 2),
                "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
                "last_error": self.last_error, "created_at": self.created_at.isoformat()}


class SandboxAdCampaign(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """State of ARC's built-in *test* ad platform. No real money, no outside
    calls: spend accrues on a clock so the guardrails can be exercised."""
    __tablename__ = "sandbox_ad_campaigns"
    idempotency_key = db.Column(db.String(128), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    daily_budget = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(16), nullable=False)  # ACTIVE | PAUSED | ARCHIVED
    active_since = db.Column(db.DateTime(timezone=True))
    accrued_before = db.Column(db.Float, default=0.0, nullable=False)
