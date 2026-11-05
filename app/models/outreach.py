"""Batch-approved email outreach (Phase 2, docs/DECISIONS.md D18).

Contacts come only from lists the client uploads with a stated lawful basis
and source (no scraping). A batch = one template + one list + one sender +
a daily limit, approved as a whole: the approval is bound to a hash of all
of those, and any change invalidates it. The worker re-checks the hash,
kill switch and suppression list before every single email."""

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

LAWFUL_BASES = ("consent", "existing_customer", "legitimate_interest")
CONTACT_ACTIVE, CONTACT_UNSUBSCRIBED, CONTACT_BOUNCED = "active", "unsubscribed", "bounced"

BATCH_DRAFT = "draft"
BATCH_PENDING = "pending_approval"
BATCH_APPROVED = "approved"
BATCH_SENDING = "sending"
BATCH_PAUSED = "paused"
BATCH_COMPLETED = "completed"
BATCH_CANCELLED = "cancelled"

MSG_QUEUED, MSG_SENDING, MSG_SENT, MSG_FAILED, MSG_SKIPPED = "queued", "sending", "sent", "failed", "skipped"


class OutreachList(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "outreach_lists"
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id", name="fk_outreach_lists_org"), nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    lawful_basis = db.Column(db.String(32), nullable=False)
    source_description = db.Column(db.String(500), nullable=False)
    attested_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id", name="fk_outreach_lists_attested_by"), nullable=False)
    attested_at = db.Column(db.DateTime(timezone=True), nullable=False)

    def to_dict(self, counts: dict | None = None) -> dict:
        return {"id": self.id, "name": self.name, "lawful_basis": self.lawful_basis,
                "source_description": self.source_description, "attested_at": self.attested_at.isoformat(),
                "created_at": self.created_at.isoformat(), **(counts or {})}


class OutreachContact(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "outreach_contacts"
    __table_args__ = (db.UniqueConstraint("list_id", "email", name="uq_outreach_contact_list_email"),)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id", name="fk_outreach_contacts_org"), nullable=False, index=True)
    list_id = db.Column(db.String(36), db.ForeignKey("outreach_lists.id", name="fk_outreach_contacts_list"), nullable=False, index=True)
    email = db.Column(db.String(320), nullable=False)  # lower-cased
    first_name = db.Column(db.String(100))
    company = db.Column(db.String(200))
    source = db.Column(db.String(300))
    status = db.Column(db.String(16), default=CONTACT_ACTIVE, nullable=False)

    def to_dict(self) -> dict:
        return {"id": self.id, "email": self.email, "first_name": self.first_name, "company": self.company,
                "source": self.source, "status": self.status}


class OutreachSuppression(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Workspace-wide do-not-email list. Unsubscribes land here and are never removed by the API."""
    __tablename__ = "outreach_suppressions"
    __table_args__ = (db.UniqueConstraint("organization_id", "email", name="uq_outreach_suppression_org_email"),)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id", name="fk_outreach_suppressions_org"), nullable=False, index=True)
    email = db.Column(db.String(320), nullable=False)
    reason = db.Column(db.String(32), nullable=False)  # unsubscribed | bounced | complaint | manual

    def to_dict(self) -> dict:
        return {"email": self.email, "reason": self.reason, "created_at": self.created_at.isoformat()}


class OutreachBatch(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "outreach_batches"
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id", name="fk_outreach_batches_org"), nullable=False, index=True)
    list_id = db.Column(db.String(36), db.ForeignKey("outreach_lists.id", name="fk_outreach_batches_list"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(300), nullable=False)
    body = db.Column(db.Text, nullable=False)
    daily_limit = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(24), default=BATCH_DRAFT, nullable=False)
    source_deliverable_id = db.Column(db.String(36), db.ForeignKey("deliverables.id", name="fk_outreach_batches_deliverable"))
    created_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id", name="fk_outreach_batches_created_by"), nullable=False)
    approval_hash = db.Column(db.String(64))
    approved_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id", name="fk_outreach_batches_approved_by"))
    approved_at = db.Column(db.DateTime(timezone=True))
    started_at = db.Column(db.DateTime(timezone=True))
    completed_at = db.Column(db.DateTime(timezone=True))
    last_error = db.Column(db.String(500))


class OutreachMessage(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "outreach_messages"
    __table_args__ = (db.UniqueConstraint("batch_id", "contact_id", name="uq_outreach_message_batch_contact"),)
    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id", name="fk_outreach_messages_org"), nullable=False, index=True)
    batch_id = db.Column(db.String(36), db.ForeignKey("outreach_batches.id", name="fk_outreach_messages_batch"), nullable=False, index=True)
    contact_id = db.Column(db.String(36), db.ForeignKey("outreach_contacts.id", name="fk_outreach_messages_contact"), nullable=False)
    status = db.Column(db.String(16), default=MSG_QUEUED, nullable=False, index=True)
    provider_message_id = db.Column(db.String(200))
    sent_at = db.Column(db.DateTime(timezone=True), index=True)
    error = db.Column(db.String(500))
    unsubscribe_token_hash = db.Column(db.String(64), unique=True)
