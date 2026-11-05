"""Live publishing to a connected WordPress.com site.

Flow: a workspace admin connects a site (OAuth2) -> an approver asks to
publish one blog article from an approved, current deliverable version ->
an ExternalAction is queued -> the worker re-checks the kill switch, the
approval, the exact version and the connection immediately before posting
(rule 3 in CLAUDE.md), posts once (deterministic slug, so retries never
duplicate), then reads the post back from WordPress.com. Only that read-back
can mark it 'platform_verified_published'."""

import logging
import secrets
from datetime import timedelta

from flask import current_app, session
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import or_, update

from app.crypto import decrypt_secret, encrypt_secret
from app.extensions import db
from app.integrations import wordpress_com as wp
from app.models.approval import DECISION_APPROVED
from app.models.base import utcnow
from app.models.deliverable import Deliverable
from app.models.external_action import (
    PUBLICATION_DRAFT_CREATED,
    PUBLICATION_NOT_APPLICABLE,
    PUBLICATION_PLATFORM_VERIFIED,
    PUBLICATION_REMOVED,
    PUBLICATION_UNVERIFIED,
    STATUS_EXECUTING,
    STATUS_FAILED,
    STATUS_QUEUED,
    STATUS_SUCCEEDED,
    ExternalAction,
)
from app.models.integration import STATE_CONNECTED, STATE_DISCONNECTED, STATE_REAUTH_REQUIRED, Integration
from app.models.membership import APPROVAL_CAPABLE_ROLES, WORKSPACE_ADMIN_ROLES, Membership
from app.models.organization import Organization
from app.services.approval_service import get_approval_or_404
from app.services.audit_service import record_audit_event
from app.services.errors import Conflict, NotFound, PermissionDenied, ServiceUnavailable, ValidationError

log = logging.getLogger(__name__)
PROVIDER = "wordpress_com"
MAX_ATTEMPTS = 5
LEASE = timedelta(minutes=10)
_STATE_SALT = "wordpress-oauth-state"


# ---- configuration -------------------------------------------------------
def _cfg():
    c = current_app.config
    redirect = c.get("WORDPRESS_REDIRECT_URI") or f"{c.get('FRONTEND_ORIGIN', '').rstrip('/')}/api/v1/integrations/wordpress/callback"
    return c.get("WORDPRESS_CLIENT_ID"), c.get("WORDPRESS_CLIENT_SECRET"), redirect


def is_configured() -> bool:
    cid, secret, _ = _cfg()
    return bool(cid and secret)


def get_connection(organization_id: str) -> Integration | None:
    return Integration.query.filter_by(organization_id=organization_id, provider=PROVIDER).first()


def connection_status(organization_id: str) -> dict:
    integ = get_connection(organization_id)
    connected = bool(integ and integ.state == STATE_CONNECTED and integ.credential_ciphertext)
    return {"configured": is_configured(), "connected": connected,
            "state": integ.state if integ else STATE_DISCONNECTED,
            "site_url": integ.account_url if integ else None,
            "site_name": integ.account_label if integ else None,
            "connected_at": integ.connected_at.isoformat() if integ and integ.connected_at else None}


# ---- connect / disconnect -----------------------------------------------
def start_connect(membership: Membership) -> str:
    if membership.role not in WORKSPACE_ADMIN_ROLES:
        raise PermissionDenied("Only a workspace owner or admin can connect WordPress.")
    cid, _, redirect = _cfg()
    if not is_configured():
        raise ServiceUnavailable("WordPress publishing isn't set up on this ARC server yet.")
    nonce = secrets.token_urlsafe(16)
    session["wp_oauth_nonce"] = nonce
    state = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=_STATE_SALT).dumps(
        {"org": membership.organization_id, "user": membership.user_id, "nonce": nonce})
    return wp.authorize_url(cid, redirect, state)


def complete_connect(user, code: str, state: str) -> str:
    """Returns the organization id. The state is signed, expires after 10
    minutes, must belong to the signed-in user and match this browser's
    session nonce, and the user must still be an admin of that workspace."""
    try:
        data = URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=_STATE_SALT).loads(state, max_age=600)
    except (BadSignature, SignatureExpired) as exc:
        raise PermissionDenied("This WordPress connection link has expired. Please try again.") from exc
    nonce = session.pop("wp_oauth_nonce", None)
    if data.get("user") != user.id or not nonce or not secrets.compare_digest(nonce, data.get("nonce", "")):
        raise PermissionDenied("This WordPress connection was started in a different session.")
    org_id = data["org"]
    membership = Membership.query.filter_by(organization_id=org_id, user_id=user.id).first()
    if membership is None or membership.role not in WORKSPACE_ADMIN_ROLES:
        raise PermissionDenied("Only a workspace owner or admin can connect WordPress.")
    if not code:
        raise ValidationError("WordPress.com did not return an authorisation code.")
    cid, secret_, redirect = _cfg()
    try:
        tok = wp.exchange_code(cid, secret_, redirect, code)
    except wp.WordPressError as exc:
        raise ServiceUnavailable(f"Could not connect to WordPress.com: {exc}") from exc
    integ = get_connection(org_id) or Integration(organization_id=org_id, provider=PROVIDER)
    integ.credential_ciphertext = encrypt_secret(tok["access_token"])
    integ.external_account_id = str(tok["blog_id"])
    integ.account_url = (tok.get("blog_url") or "")[:500]
    integ.account_label = (tok.get("blog_url") or "WordPress.com site").replace("https://", "").replace("http://", "")[:255]
    integ.scopes = (tok.get("scope") or "")[:500]
    integ.state = STATE_CONNECTED
    integ.connected_by_user_id = user.id
    integ.connected_at = utcnow()
    db.session.add(integ)
    db.session.flush()
    record_audit_event(org_id, "integration.connected", actor_user_id=user.id, target_type="integration",
                       target_id=integ.id, metadata={"provider": PROVIDER, "site": integ.account_url})
    db.session.commit()
    return org_id


def disconnect(membership: Membership) -> None:
    if membership.role not in WORKSPACE_ADMIN_ROLES:
        raise PermissionDenied("Only a workspace owner or admin can disconnect WordPress.")
    integ = get_connection(membership.organization_id)
    if integ is None:
        return
    integ.credential_ciphertext = None
    integ.state = STATE_DISCONNECTED
    record_audit_event(membership.organization_id, "integration.disconnected", actor_user_id=membership.user_id,
                       target_type="integration", target_id=integ.id, metadata={"provider": PROVIDER})
    db.session.commit()


# ---- request a publication -------------------------------------------------
def _article(deliverable: Deliverable, index: int) -> dict:
    content = deliverable.current_version.to_dict()["content"]
    articles = content.get("blog_articles") or []
    if not isinstance(index, int) or not 0 <= index < len(articles):
        raise ValidationError("Please correct the highlighted fields.",
                              details=[{"field": "article_index", "issue": "No such article in this deliverable"}])
    return articles[index]


def _kill_switch_on(org: Organization) -> bool:
    return bool(org.kill_switch_enabled or current_app.config.get("KILL_SWITCH_ENABLED"))


def _check_approved_current(organization_id: str, approval_id: str):
    approval = get_approval_or_404(organization_id, approval_id)
    if approval.decision != DECISION_APPROVED:
        raise Conflict("This deliverable has not been approved.")
    deliverable = Deliverable.query.filter_by(id=approval.deliverable_id, organization_id=organization_id).first()
    if deliverable is None or deliverable.current_version_id != approval.deliverable_version_id:
        raise Conflict("The deliverable has changed since approval; approve the new version to publish it.")
    return approval, deliverable


def request_publish(membership: Membership, approval_id: str, article_index, idempotency_key: str,
                    mode: str = "publish") -> ExternalAction:
    org_id = membership.organization_id
    if membership.role not in APPROVAL_CAPABLE_ROLES:
        raise PermissionDenied("Your role does not permit publishing.")
    if not idempotency_key:
        raise ValidationError("An idempotency key is required.")
    existing = ExternalAction.query.filter_by(organization_id=org_id, idempotency_key=idempotency_key).first()
    if existing:
        return existing
    if mode not in ("publish", "draft"):
        raise ValidationError("Please correct the highlighted fields.", details=[{"field": "mode", "issue": "publish or draft"}])
    org = db.session.get(Organization, org_id)
    if _kill_switch_on(org):
        raise PermissionDenied("External actions are currently disabled by the kill switch.")
    status = connection_status(org_id)
    if not status["connected"]:
        raise Conflict("Connect a WordPress.com site in Integrations first.")
    from app.services.platform_service import check_entitlement

    check_entitlement(org_id, "monthly_exports")
    approval, deliverable = _check_approved_current(org_id, approval_id)
    article = _article(deliverable, article_index)
    wp.WordPressComConnector("x", "x").validate_action({**article, "status": mode})
    already = ExternalAction.query.filter(ExternalAction.organization_id == org_id,
                                          ExternalAction.approval_id == approval.id,
                                          ExternalAction.connector == PROVIDER,
                                          ExternalAction.item_index == article_index,
                                          ExternalAction.status.in_((STATUS_QUEUED, STATUS_EXECUTING, STATUS_SUCCEEDED)),
                                          ExternalAction.publication_status != PUBLICATION_REMOVED).first()
    if already:
        return already  # one live post per approved article version
    action = ExternalAction(organization_id=org_id, approval_id=approval.id, connector=PROVIDER,
                            idempotency_key=idempotency_key, status=STATUS_QUEUED, item_index=article_index,
                            publish_mode=mode, requested_by_user_id=membership.user_id, next_attempt_at=utcnow(),
                            publication_status=PUBLICATION_NOT_APPLICABLE, target_platform="wordpress_com")
    db.session.add(action)
    db.session.flush()
    record_audit_event(org_id, "external_action.publish_requested", actor_user_id=membership.user_id,
                       target_type="external_action", target_id=action.id,
                       metadata={"provider": PROVIDER, "article_index": article_index, "mode": mode,
                                 "deliverable_version_id": approval.deliverable_version_id})
    db.session.commit()
    return action


def list_publications(organization_id: str, deliverable_id: str) -> list[dict]:
    from app.models.approval import Approval

    approval_ids = [a.id for a in Approval.query.filter_by(organization_id=organization_id, deliverable_id=deliverable_id)]
    if not approval_ids:
        return []
    rows = ExternalAction.query.filter(ExternalAction.organization_id == organization_id,
                                       ExternalAction.connector == PROVIDER,
                                       ExternalAction.approval_id.in_(approval_ids)).order_by(ExternalAction.created_at.desc())
    return [r.to_dict() for r in rows]


# ---- worker step -------------------------------------------------------------
def _fail(action: ExternalAction, message: str) -> None:
    action.status, action.last_error = STATUS_FAILED, message[:500]
    from app.services.platform_service import notify

    notify(action.organization_id, "publish.failed", "A WordPress post could not be published",
           body=message[:300], link="/app/integrations", severity="warning")
    record_audit_event(action.organization_id, "external_action.publish_failed", target_type="external_action",
                       target_id=action.id, metadata={"error": message[:300]})


def process_next_publication() -> bool:
    now = utcnow()
    # Recover a crashed attempt: the slug lookup makes re-running it safe.
    db.session.execute(update(ExternalAction).where(ExternalAction.connector == PROVIDER,
                                                    ExternalAction.status == STATUS_EXECUTING,
                                                    ExternalAction.updated_at < now - LEASE)
                       .values(status=STATUS_QUEUED, next_attempt_at=now))
    cand = (ExternalAction.query.filter(ExternalAction.connector == PROVIDER, ExternalAction.status == STATUS_QUEUED,
                                        or_(ExternalAction.next_attempt_at.is_(None), ExternalAction.next_attempt_at <= now))
            .order_by(ExternalAction.created_at).first())
    if cand is None:
        db.session.commit()
        return False
    claimed = db.session.execute(update(ExternalAction).where(ExternalAction.id == cand.id,
                                                              ExternalAction.status == STATUS_QUEUED)
                                 .values(status=STATUS_EXECUTING, attempts=ExternalAction.attempts + 1, updated_at=now))
    db.session.commit()
    if claimed.rowcount != 1:
        return True
    action = db.session.get(ExternalAction, cand.id)
    org = db.session.get(Organization, action.organization_id)
    # Re-check everything immediately before acting (never trust the request-time check).
    if _kill_switch_on(org):
        action.status, action.next_attempt_at, action.last_error = STATUS_QUEUED, now + timedelta(minutes=5), "Paused: kill switch is on."
        db.session.commit()
        return True
    try:
        approval, deliverable = _check_approved_current(action.organization_id, action.approval_id)
        article = _article(deliverable, action.item_index)
    except (Conflict, ValidationError, NotFound) as exc:
        _fail(action, str(exc.message if hasattr(exc, "message") else exc))
        db.session.commit()
        return True
    integ = get_connection(action.organization_id)
    token = decrypt_secret(integ.credential_ciphertext) if integ and integ.state == STATE_CONNECTED and integ.credential_ciphertext else None
    if not token:
        _fail(action, "WordPress.com is not connected. Reconnect it in Integrations and try again.")
        db.session.commit()
        return True
    conn = wp.WordPressComConnector(token, integ.external_account_id)
    slug = wp.slug_for(article.get("title"), action.id)
    try:
        result = conn.execute_action({**article, "status": action.publish_mode or "publish"}, slug)
        verified = conn.verify_action(result["post_id"])
    except wp.WordPressError as exc:
        if exc.status in (401, 403):
            integ.state = STATE_REAUTH_REQUIRED
            _fail(action, "WordPress.com rejected ARC's access. Reconnect the site in Integrations.")
        elif exc.retryable and action.attempts < MAX_ATTEMPTS:
            action.status, action.last_error = STATUS_QUEUED, str(exc)[:500]
            action.next_attempt_at = now + timedelta(seconds=30 * 2 ** (action.attempts - 1))
        else:
            _fail(action, str(exc))
        db.session.commit()
        return True
    except ValueError as exc:
        _fail(action, str(exc))
        db.session.commit()
        return True
    action.status, action.last_error = STATUS_SUCCEEDED, None
    action.external_reference = result["post_id"]
    action.external_url = (verified.get("url") or result.get("url") or "")[:1000]
    if verified.get("status") == "publish" and action.external_url:
        action.publication_status = PUBLICATION_PLATFORM_VERIFIED
        action.publication_confirmed_at = utcnow()
    elif verified.get("status") == "draft":
        action.publication_status = PUBLICATION_DRAFT_CREATED
    else:
        action.publication_status = PUBLICATION_UNVERIFIED
    import json as _json

    action.response_metadata_json = _json.dumps({"wordpress": {**result, "verified": verified}})
    record_audit_event(action.organization_id, "external_action.published", target_type="external_action",
                       target_id=action.id, metadata={"provider": PROVIDER, "url": action.external_url,
                                                      "publication_status": action.publication_status,
                                                      "deliverable_version_id": approval.deliverable_version_id})
    from app.services.platform_service import notify

    notify(action.organization_id, "publish.succeeded",
           "Blog post published on WordPress" if action.publication_status == PUBLICATION_PLATFORM_VERIFIED
           else "Blog draft created on WordPress", body=article.get("title"), link=action.external_url or None)
    db.session.commit()
    return True


def unpublish(membership: Membership, action_id: str) -> ExternalAction:
    """Take a post down from the connected site (moves it to WordPress's
    trash). Allowed even with the kill switch on: it only removes content."""
    if membership.role not in APPROVAL_CAPABLE_ROLES:
        raise PermissionDenied("Your role does not permit unpublishing.")
    action = ExternalAction.query.filter_by(id=action_id, organization_id=membership.organization_id,
                                            connector=PROVIDER).first()
    if action is None:
        raise NotFound("Publication not found.")
    if action.status != STATUS_SUCCEEDED or not action.external_reference:
        raise Conflict("This article hasn't been posted to WordPress.")
    if action.publication_status == PUBLICATION_REMOVED:
        return action
    integ = get_connection(membership.organization_id)
    token = decrypt_secret(integ.credential_ciphertext) if integ and integ.state == STATE_CONNECTED and integ.credential_ciphertext else None
    if not token:
        raise Conflict("Reconnect WordPress.com in Integrations to unpublish this post.")
    conn = wp.WordPressComConnector(token, integ.external_account_id)
    try:
        result = conn.unpublish(action.external_reference)
    except wp.WordPressError as exc:
        if exc.status == 404:
            result = {"status": "missing"}  # already deleted in WordPress
        elif exc.status in (401, 403):
            integ.state = STATE_REAUTH_REQUIRED
            db.session.commit()
            raise Conflict("WordPress.com rejected ARC's access. Reconnect the site in Integrations.") from exc
        else:
            raise ServiceUnavailable(f"Could not unpublish: {exc}") from exc
    action.publication_status = PUBLICATION_REMOVED
    record_audit_event(membership.organization_id, "external_action.unpublished", actor_user_id=membership.user_id,
                       target_type="external_action", target_id=action.id,
                       metadata={"provider": PROVIDER, "url": action.external_url, "wordpress_status": result.get("status")})
    db.session.commit()
    return action
