"""Review collaboration: comments on deliverables, and expiring review links
that let a client approve one exact version without a workspace account."""

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


def _iso(v):
    return v.isoformat() if v else None


class DeliverableComment(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "deliverable_comments"

    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True)
    deliverable_id = db.Column(db.String(36), db.ForeignKey("deliverables.id"), nullable=False, index=True)
    # The version the comment was written against (versions are immutable).
    deliverable_version_id = db.Column(db.String(36), db.ForeignKey("deliverable_versions.id"))
    author_user_id = db.Column(db.String(36), db.ForeignKey("users.id"))
    # Set when the comment came through a review link (no ARC account).
    external_author_name = db.Column(db.String(120))
    review_link_id = db.Column(db.String(36), db.ForeignKey("review_links.id"))
    body = db.Column(db.Text, nullable=False)

    def to_dict(self, author_name: str | None = None) -> dict:
        return {"id": self.id, "deliverable_id": self.deliverable_id,
                "deliverable_version_id": self.deliverable_version_id,
                "author_name": author_name or self.external_author_name or "Workspace member",
                "is_external": self.review_link_id is not None,
                "body": self.body, "created_at": _iso(self.created_at)}


class ReviewLink(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """A secret link for one pending approval. Only a hash of the token is
    stored. It can decide the approval once, then becomes read-only."""

    __tablename__ = "review_links"

    organization_id = db.Column(db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True)
    approval_id = db.Column(db.String(36), db.ForeignKey("approvals.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), unique=True, nullable=False)
    label = db.Column(db.String(120))  # who it was sent to, for the team's reference
    created_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    revoked_at = db.Column(db.DateTime(timezone=True))
    used_at = db.Column(db.DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {"id": self.id, "approval_id": self.approval_id, "label": self.label,
                "expires_at": _iso(self.expires_at), "revoked_at": _iso(self.revoked_at),
                "used_at": _iso(self.used_at), "created_at": _iso(self.created_at)}
