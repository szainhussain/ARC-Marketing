"""Campaign results recorded by the team (until analytics connectors exist).
Every row is labelled with its source so reports never present manual
numbers as if they came from a platform."""

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

METRIC_FIELDS = ("spend", "impressions", "clicks", "leads", "conversions", "revenue")


class CampaignResult(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "campaign_results"

    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True)
    campaign_id = db.Column(db.String(36), db.ForeignKey("campaigns.id"), nullable=False, index=True)
    channel = db.Column(db.String(64), nullable=False)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    spend = db.Column(db.Float)
    impressions = db.Column(db.Float)
    clicks = db.Column(db.Float)
    leads = db.Column(db.Float)
    conversions = db.Column(db.Float)
    revenue = db.Column(db.Float)
    notes = db.Column(db.Text)
    source = db.Column(db.String(32), default="manual", nullable=False)
    entered_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"))

    def to_dict(self) -> dict:
        return {"id": self.id, "campaign_id": self.campaign_id, "channel": self.channel,
                "period_start": self.period_start.isoformat(), "period_end": self.period_end.isoformat(),
                **{f: getattr(self, f) for f in METRIC_FIELDS}, "notes": self.notes, "source": self.source,
                "created_at": self.created_at.isoformat() if self.created_at else None}
