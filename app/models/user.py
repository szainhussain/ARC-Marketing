from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, UserMixin, db.Model):
    __tablename__ = "users"

    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    is_active_account = db.Column(db.Boolean, default=True, nullable=False)
    # Bumped to sign out every existing session (password reset, "sign out
    # everywhere"). It is part of the Flask-Login session id, see get_id().
    session_version = db.Column(db.Integer, default=1, nullable=False)
    email_verified_at = db.Column(db.DateTime(timezone=True))
    # Which version of the Terms/Privacy Policy the user accepted, and when.
    terms_version = db.Column(db.String(32))
    terms_accepted_at = db.Column(db.DateTime(timezone=True))

    memberships = db.relationship(
        "Membership", back_populates="user", cascade="all, delete-orphan"
    )

    def get_id(self) -> str:
        return f"{self.id}:{self.session_version or 1}"

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def to_public_dict(self) -> dict:
        return {"id": self.id, "email": self.email, "full_name": self.full_name,
                "email_verified": self.email_verified_at is not None}
