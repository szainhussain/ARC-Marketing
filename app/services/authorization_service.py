from flask_login import current_user

from app.models.membership import Membership
from app.services.errors import AuthenticationError, PermissionDenied


def require_authenticated_user():
    if not current_user.is_authenticated:
        raise AuthenticationError("Sign in required.")
    return current_user


def get_membership_or_403(organization_id: str) -> Membership:
    """The server-side tenant boundary. Every route that touches
    organization-scoped data must call this (or active_membership) instead
    of trusting an organization_id supplied by the client in any other way.
    """
    user = require_authenticated_user()
    membership = next(
        (m for m in user.memberships if m.organization_id == organization_id), None
    )
    if membership is None:
        # Deliberately identical to a generic 403 — do not reveal whether
        # the organization exists.
        raise PermissionDenied("You do not have access to this organization.")
    return membership


def require_role(membership: Membership, allowed_roles: tuple[str, ...]) -> None:
    if membership.role not in allowed_roles:
        raise PermissionDenied("Your role does not permit this action.")
