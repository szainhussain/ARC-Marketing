from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin

ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MARKETING_LEAD = "marketing_lead"
ROLE_CONTRIBUTOR = "contributor"
ROLE_VIEWER = "viewer"
ROLE_APPROVER = "approver"
ROLE_ANALYST = "analyst"

VALID_ROLES = (
    ROLE_OWNER,
    ROLE_ADMIN,
    ROLE_MARKETING_LEAD,
    ROLE_APPROVER,
    ROLE_CONTRIBUTOR,
    ROLE_ANALYST,
    ROLE_VIEWER,
)

# Roles permitted to approve Level 2 external actions by default.
APPROVAL_CAPABLE_ROLES = (ROLE_OWNER, ROLE_ADMIN, ROLE_MARKETING_LEAD, ROLE_APPROVER)
# Roles that can run/steer agent work (start runs, pause/retry, edit drafts).
OPERATOR_ROLES = (ROLE_OWNER, ROLE_ADMIN, ROLE_MARKETING_LEAD)
WORKSPACE_ADMIN_ROLES = (ROLE_OWNER, ROLE_ADMIN)
ROLE_LABELS = {
    ROLE_OWNER: "Workspace Owner",
    ROLE_ADMIN: "Administrator",
    ROLE_MARKETING_LEAD: "Marketing Manager",
    ROLE_APPROVER: "Approver",
    ROLE_CONTRIBUTOR: "Contributor",
    ROLE_ANALYST: "Analyst",
    ROLE_VIEWER: "Viewer",
}


class Membership(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    __tablename__ = "memberships"
    __table_args__ = (
        db.UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),
    )

    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    organization_id = db.Column(
        db.String(36), db.ForeignKey("organizations.id"), nullable=False
    )
    role = db.Column(db.String(32), default=ROLE_VIEWER, nullable=False)

    user = db.relationship("User", back_populates="memberships")
    organization = db.relationship("Organization", back_populates="memberships")

    def can_approve_external_actions(self) -> bool:
        return self.role in APPROVAL_CAPABLE_ROLES

    def to_public_dict(self) -> dict:
        return {
            "organization_id": self.organization_id,
            "organization_name": self.organization.name if self.organization else None,
            "role": self.role,
        }
