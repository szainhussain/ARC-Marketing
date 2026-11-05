from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

STATE_DISCONNECTED = "disconnected"
STATE_CONNECTING = "connecting"
STATE_CONNECTED = "connected"
STATE_DEGRADED = "degraded"
STATE_REAUTH_REQUIRED = "reauth_required"


class Integration(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """A workspace's connection to an outside provider.

    Credentials are stored only as ciphertext (app/crypto.py) in
    credential_ciphertext and are never included in to_dict(). Live
    connectors exist only for providers the user chose as a pilot
    (WordPress.com first; see docs/DECISIONS.md D17).
    """

    __tablename__ = "integrations"

    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False, index=True
    )
    provider = db.Column(db.String(64), nullable=False)
    account_label = db.Column(db.String(255))
    state = db.Column(db.String(32), default=STATE_DISCONNECTED, nullable=False)
    scopes = db.Column(db.String(500))
    encrypted_credential_ref = db.Column(db.String(255))  # legacy: pointer into a secret manager
    credential_ciphertext = db.Column(db.Text)
    external_account_id = db.Column(db.String(128))
    account_url = db.Column(db.String(500))
    connected_by_user_id = db.Column(db.String(36), db.ForeignKey("users.id", name="fk_integrations_connected_by"))
    connected_at = db.Column(db.DateTime(timezone=True))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "provider": self.provider,
            "account_label": self.account_label,
            "account_url": self.account_url,
            "state": self.state,
            "scopes": self.scopes,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
        }
