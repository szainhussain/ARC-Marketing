from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Document(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Metadata for an uploaded brand/business file.

    Only metadata lives in the database. The actual bytes live in
    UPLOAD_DIR locally (private object storage in production) and are never
    served by a public, unauthenticated URL.
    """

    __tablename__ = "documents"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    uploaded_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)

    original_filename = db.Column(db.String(500), nullable=False)
    storage_key = db.Column(db.String(500), nullable=False)
    content_type = db.Column(db.String(255), nullable=False)
    size_bytes = db.Column(db.Integer, nullable=False)
    checksum_sha256 = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(32), default="stored", nullable=False)  # stored|rejected

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "organization_id": self.organization_id,
            "original_filename": self.original_filename,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
        }
