from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

STATE_DISCONNECTED = "disconnected"
STATE_CONNECTING = "connecting"
STATE_CONNECTED = "connected"
STATE_DEGRADED = "degraded"
STATE_REAUTH_REQUIRED = "reauth_required"


class Integration(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """Integration connection metadata. Never store plaintext secrets here.

    No live connectors are implemented yet (see docs/DECISIONS.md — M11 is
    deferred until a pilot channel is selected and API access verified).
    This table exists so the API can report an honest, empty integrations
    list rather than omitting the capability's shape entirely.
    """

    __tablename__ = "integrations"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    provider = db.Column(db.String(64), nullable=False)
    account_label = db.Column(db.String(255))
    state = db.Column(db.String(32), default=STATE_DISCONNECTED, nullable=False)
    scopes = db.Column(db.String(500))
    encrypted_credential_ref = db.Column(db.String(255))  # pointer into a secret manager

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "account_label": self.account_label,
            "state": self.state,
            "scopes": self.scopes,
        }
