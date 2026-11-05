"""Ask ARC: the workspace assistant's conversation messages."""

import json

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

MSG_PENDING = "pending"
MSG_ANSWERED = "answered"
MSG_FAILED = "failed"


class AssistantMessage(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """One message in a member's conversation with the workspace assistant.
    Assistant replies are written by the worker; a reply starts `pending`."""

    __tablename__ = "assistant_messages"

    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    role = db.Column(db.String(16), nullable=False)  # user | assistant
    content = db.Column(db.Text, nullable=False, default="")
    status = db.Column(db.String(16), default=MSG_ANSWERED, nullable=False, index=True)
    reply_to_id = db.Column(db.String(36), db.ForeignKey("assistant_messages.id"))
    sources_json = db.Column(db.Text)  # [{"kind", "title", "link"}]
    action_json = db.Column(db.Text)  # {"type", "label", "link"} suggested next step
    error_summary = db.Column(db.Text)
    expert_advice = db.Column(db.Text)
    retrieval_mode = db.Column(db.String(16))  # semantic | keyword

    def to_dict(self) -> dict:
        return {"id": self.id, "role": self.role, "content": self.content, "status": self.status,
                "sources": json.loads(self.sources_json) if self.sources_json else [],
                "action": json.loads(self.action_json) if self.action_json else None,
                "error_summary": self.error_summary,
                "expert_advice": self.expert_advice or None,
                "retrieval_mode": self.retrieval_mode,
                "created_at": self.created_at.isoformat() if self.created_at else None}
