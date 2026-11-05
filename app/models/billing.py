"""Billing events (payment-provider webhooks) and outbound webhooks."""

import json

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


def _iso(v):
    return v.isoformat() if v else None


class BillingEvent(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """A verified payment-provider event. The unique (provider, event_id)
    pair makes webhook processing idempotent: a replayed or retried event is
    recognised and ignored. Doubles as billing history."""

    __tablename__ = "billing_events"
    __table_args__ = (db.UniqueConstraint("provider", "event_id", name="uq_billing_event_provider_id"),)

    provider = db.Column(db.String(32), nullable=False)
    event_id = db.Column(db.String(255), nullable=False)
    event_type = db.Column(db.String(128), nullable=False)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), index=True)
    amount_usd = db.Column(db.Float)
    is_test = db.Column(db.Boolean, default=False, nullable=False)
    payload_json = db.Column(db.Text, nullable=False)
    outcome = db.Column(db.String(64), default="processed", nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "event_type": self.event_type,
            "amount_usd": self.amount_usd,
            "is_test": self.is_test,
            "outcome": self.outcome,
            "created_at": _iso(self.created_at),
        }


WEBHOOK_EVENTS = ("content.approved_for_publishing", "run.completed", "run.failed", "approval.requested",
                  "approval.decided", "deliverable.created", "budget.threshold")


class WebhookEndpoint(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "webhook_endpoints"

    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True)
    url = db.Column(db.String(1000), nullable=False)
    # Shown to the admin once at creation; used to sign every delivery.
    secret = db.Column(db.String(128), nullable=False)
    events_json = db.Column(db.Text, nullable=False, default="[]")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    description = db.Column(db.String(255))

    @property
    def events(self) -> list[str]:
        return json.loads(self.events_json or "[]")

    def to_dict(self) -> dict:
        return {"id": self.id, "url": self.url, "events": self.events, "is_active": self.is_active,
                "description": self.description, "created_at": _iso(self.created_at)}


class WebhookDelivery(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (db.UniqueConstraint("endpoint_id", "event_id", name="uq_webhook_delivery_endpoint_event"),)

    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True)
    endpoint_id = db.Column(db.String(36), db.ForeignKey("webhook_endpoints.id"), nullable=False, index=True)
    event_id = db.Column(db.String(64), nullable=False)
    event_type = db.Column(db.String(64), nullable=False)
    payload_json = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), default="pending", nullable=False, index=True)  # pending|delivered|failed
    attempts = db.Column(db.Integer, default=0, nullable=False)
    next_attempt_at = db.Column(db.DateTime(timezone=True))
    last_response_code = db.Column(db.Integer)
    last_error = db.Column(db.String(500))

    def to_dict(self) -> dict:
        return {"id": self.id, "event_id": self.event_id, "event_type": self.event_type,
                "status": self.status, "attempts": self.attempts,
                "last_response_code": self.last_response_code, "last_error": self.last_error,
                "next_attempt_at": _iso(self.next_attempt_at), "created_at": _iso(self.created_at)}
