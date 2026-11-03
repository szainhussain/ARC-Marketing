from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class Organization(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "organizations"

    name = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False, index=True)
    status = db.Column(db.String(32), default="active", nullable=False)
    monthly_workflow_limit = db.Column(db.Integer, default=20, nullable=False)
    kill_switch_enabled = db.Column(db.Boolean, default=False, nullable=False)

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
