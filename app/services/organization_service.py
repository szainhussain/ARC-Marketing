import re

from app.extensions import db
from app.models.membership import ROLE_OWNER, Membership
from app.models.organization import Organization
from app.services.audit_service import record_audit_event
from app.services.errors import ValidationError


def slugify(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return base or "workspace"


def create_organization_with_owner(name: str, owner_user_id: str) -> Organization:
    name = (name or "").strip()
    if not name:
        raise ValidationError(
            "Please correct the highlighted fields.",
            details=[{"field": "name", "issue": "Required"}],
        )

    base_slug = slugify(name)
    slug = base_slug
    suffix = 1
    while Organization.query.filter_by(slug=slug).first() is not None:
        suffix += 1
        slug = f"{base_slug}-{suffix}"

    organization = Organization(name=name, slug=slug)
    db.session.add(organization)
    db.session.flush()

    membership = Membership(
        user_id=owner_user_id, organization_id=organization.id, role=ROLE_OWNER
    )
    db.session.add(membership)
    db.session.flush()

    record_audit_event(
        organization.id, "organization.created", actor_user_id=owner_user_id,
        target_type="organization", target_id=organization.id,
    )
    db.session.commit()
    return organization
