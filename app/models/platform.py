"""Commercial, collaboration and knowledge models added for the MaaS brief
(plans/entitlements, notifications, invitations, password resets, action
policies, knowledge library, content calendar, public enquiries)."""

import json

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


def _iso(value):
    return value.isoformat() if value else None


class Plan(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """A subscription plan. Prices and limits are data, so they can change
    without code changes (see docs/BILLING_AND_PLANS.md). Every seeded price
    is marked provisional until commercial terms are approved."""

    __tablename__ = "plans"

    code = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    tagline = db.Column(db.String(255))
    monthly_price_usd = db.Column(db.Float)  # None = custom / contact sales
    price_is_provisional = db.Column(db.Boolean, default=True, nullable=False)
    is_public = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    # {"monthly_workflow_runs": 20, "seats": 3, ...}; null value = unlimited
    entitlements_json = db.Column(db.Text, nullable=False, default="{}")
    features_json = db.Column(db.Text, nullable=False, default="[]")
    overage_note = db.Column(db.String(500))
    # Payment-provider price id (e.g. Stripe price_...); null until configured.
    stripe_price_ref = db.Column(db.String(255))

    @property
    def entitlements(self) -> dict:
        return json.loads(self.entitlements_json or "{}")

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "name": self.name,
            "tagline": self.tagline,
            "monthly_price_usd": self.monthly_price_usd,
            "price_is_provisional": self.price_is_provisional,
            "entitlements": self.entitlements,
            "features": json.loads(self.features_json or "[]"),
            "overage_note": self.overage_note,
        }


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "subscriptions"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), unique=True, nullable=False
    )
    plan_id = db.Column(db.String(36), db.ForeignKey("plans.id"), nullable=False)
    status = db.Column(db.String(32), default="trialing", nullable=False)  # trialing|active|cancelled
    # No payment processor is connected; this stays null until one is.
    billing_provider_ref = db.Column(db.String(255))
    current_period_start = db.Column(db.DateTime(timezone=True))
    current_period_end = db.Column(db.DateTime(timezone=True))

    plan = db.relationship("Plan")

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "plan": self.plan.to_dict() if self.plan else None,
            "billing_connected": bool(self.billing_provider_ref),
            "current_period_start": _iso(self.current_period_start),
            "current_period_end": _iso(self.current_period_end),
        }


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "notifications"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"))  # null = whole workspace
    kind = db.Column(db.String(64), nullable=False)
    severity = db.Column(db.String(16), default="info", nullable=False)  # info|success|warning|error
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text)
    link = db.Column(db.String(500))
    read_at = db.Column(db.DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "severity": self.severity,
            "title": self.title,
            "body": self.body,
            "link": self.link,
            "read": self.read_at is not None,
            "created_at": _iso(self.created_at),
        }


class Invitation(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "invitations"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    email = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    invited_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    accepted_at = db.Column(db.DateTime(timezone=True))
    revoked_at = db.Column(db.DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "expires_at": _iso(self.expires_at),
            "accepted": self.accepted_at is not None,
            "revoked": self.revoked_at is not None,
            "created_at": _iso(self.created_at),
        }


class PasswordResetToken(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "password_reset_tokens"

    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True))


# Action types a workspace can see. `locked` ones are platform boundaries
# the workspace cannot loosen (CLAUDE.md non-negotiables); others are
# editable and enforced in code where noted.
ACTION_POLICY_DEFAULTS = {
    "agent_drafting": {"mode": "auto", "locked": False,
                       "label": "Agents research, plan and draft deliverables",
                       "enforced_by": "engine: 'require_approval' holds new runs until an approver starts them"},
    "knowledge_update": {"mode": "require_approval", "locked": False,
                         "label": "Record Keeper adds learnings to the knowledge library",
                         "enforced_by": "engine: 'auto' approves proposed entries; otherwise they wait for review"},
    "external_handoff": {"mode": "require_approval", "locked": True,
                         "label": "Export or hand off content outside the workspace",
                         "enforced_by": "approval bound to exact version + payload hash"},
    "live_publish": {"mode": "require_approval", "locked": True,
                     "label": "Publish approved content to a connected site (WordPress.com)",
                     "enforced_by": "worker re-checks approval, exact version and kill switch before posting"},
    "outreach_email": {"mode": "require_approval", "locked": True,
                       "label": "Send outreach emails to an uploaded contact list",
                       "enforced_by": "batch approval hash (template, recipients, sender, daily limit) re-checked before every email"},
    "public_reply": {"mode": "require_approval", "locked": True,
                     "label": "Public replies to complaints, crises, legal or safety issues",
                     "enforced_by": "no agent can send messages; drafts only"},
    "spend_change": {"mode": "blocked", "locked": True,
                     "label": "Create, increase or change ad spend",
                     "enforced_by": "no code path lets an agent change spend"},
    "commitments": {"mode": "blocked", "locked": True,
                    "label": "Payments, contracts, partner commitments",
                    "enforced_by": "no code path; human-only outside the platform"},
}
POLICY_MODES = ("auto", "require_approval", "blocked")


class ActionPolicy(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "action_policies"
    __table_args__ = (
        db.UniqueConstraint("organization_id", "action_type", name="uq_action_policy_org_type"),
    )

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    action_type = db.Column(db.String(64), nullable=False)
    mode = db.Column(db.String(32), nullable=False)
    updated_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"))


KNOWLEDGE_KINDS = ("note", "product", "faq", "url", "brand_rule", "campaign_learning")
KNOWLEDGE_STATUSES = ("proposed", "approved", "archived")


class KnowledgeEntry(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Tenant-scoped, versioned knowledge. Agents only ever receive
    `approved` entries, and always as untrusted data, never instructions."""

    __tablename__ = "knowledge_entries"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    kind = db.Column(db.String(32), default="note", nullable=False)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=False)
    source_url = db.Column(db.String(1000))
    status = db.Column(db.String(32), default="approved", nullable=False, index=True)
    version = db.Column(db.Integer, default=1, nullable=False)
    # Provenance: which deliverable/run produced it, or which user wrote it.
    source_deliverable_id = db.Column(db.String(36), db.ForeignKey("deliverables.id"))
    source_run_id = db.Column(db.String(36), db.ForeignKey("workflow_runs.id"))
    created_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"))
    approved_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "body": self.body,
            "source_url": self.source_url,
            "status": self.status,
            "version": self.version,
            "source_deliverable_id": self.source_deliverable_id,
            "source_run_id": self.source_run_id,
            "created_by": "agent:record_keeper" if self.source_run_id else "user",
            "created_at": _iso(self.created_at),
            "updated_at": _iso(self.updated_at),
        }


CALENDAR_STATUSES = ("planned", "ready", "published_confirmed", "skipped")


class CalendarEntry(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """A scheduled piece of content. `published_confirmed` is only ever set
    by a person saying they posted it — nothing here posts anything."""

    __tablename__ = "calendar_entries"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    campaign_id = db.Column(db.String(36), db.ForeignKey("campaigns.id"), index=True)
    deliverable_id = db.Column(db.String(36), db.ForeignKey("deliverables.id"))
    scheduled_date = db.Column(db.Date, nullable=False, index=True)
    channel = db.Column(db.String(64), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text)
    status = db.Column(db.String(32), default="planned", nullable=False)
    created_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "campaign_id": self.campaign_id,
            "deliverable_id": self.deliverable_id,
            "scheduled_date": self.scheduled_date.isoformat(),
            "channel": self.channel,
            "title": self.title,
            "body": self.body,
            "status": self.status,
        }


class ContactEnquiry(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Public contact/sales form submissions (not tenant data)."""

    __tablename__ = "contact_enquiries"

    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255))
    topic = db.Column(db.String(64), default="sales", nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), default="new", nullable=False)
