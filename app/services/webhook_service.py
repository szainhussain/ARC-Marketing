"""Outbound webhooks to customer endpoints.

Security (docs/API.md "Webhooks"):
- Signed: `ARC-Signature: t=<unix>,v1=<hex hmac-sha256(secret, "t.body")>`.
  Receivers should reject timestamps older than 5 minutes (replay window)
  and dedupe on `ARC-Event-Id`.
- Versioned: `ARC-Event-Version` header and `version` field.
- SSRF-safe: HTTPS only; the hostname is resolved and every address must
  be public (no loopback/private/link-local/reserved); redirects are not
  followed; 10s timeout; response body is ignored.
- Retries: up to 6 attempts with exponential backoff (30s doubling); one
  delivery per (endpoint, event) so retries never duplicate events.
"""

import ipaddress
import json
import secrets
import socket
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import timedelta

from flask import current_app

from app.billing.providers import sign_payload
from app.extensions import db
from app.models.base import utcnow
from app.models.billing import WEBHOOK_EVENTS, WebhookDelivery, WebhookEndpoint
from app.services.errors import ValidationError

EVENT_VERSION = "2026-11-01"
MAX_ATTEMPTS = 6


class UnsafeURL(Exception):
    pass


def _allow_private() -> bool:
    return bool(current_app.config.get("WEBHOOK_ALLOW_PRIVATE_TARGETS"))


def validate_target_url(url: str, resolve: bool = True) -> None:
    parsed = urllib.parse.urlparse(url or "")
    if parsed.scheme != "https" and not (_allow_private() and parsed.scheme == "http"):
        raise UnsafeURL("Webhook URLs must use https://")
    if not parsed.hostname or parsed.username or parsed.password:
        raise UnsafeURL("Webhook URL must have a host and no embedded credentials.")
    if _allow_private() or not resolve:
        return
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise UnsafeURL("Webhook host could not be resolved.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global or ip.is_multicast:
            raise UnsafeURL("Webhook host resolves to a private or reserved address.")


def create_endpoint(organization_id: str, url: str, events: list[str], description: str | None):
    bad = [e for e in events or [] if e not in WEBHOOK_EVENTS]
    if not events or bad:
        raise ValidationError("Please correct the highlighted fields.",
                              details=[{"field": "events", "issue": f"Choose from: {', '.join(WEBHOOK_EVENTS)}"}])
    try:
        validate_target_url(url, resolve=False)
    except UnsafeURL as exc:
        raise ValidationError("Please correct the highlighted fields.", details=[{"field": "url", "issue": str(exc)}])
    endpoint = WebhookEndpoint(organization_id=organization_id, url=url[:1000], secret=f"whsec_{secrets.token_hex(24)}",
                               events_json=json.dumps(events), description=(description or "")[:255])
    db.session.add(endpoint)
    db.session.flush()
    return endpoint


def emit(organization_id: str, event_type: str, data: dict) -> int:
    """Queue an event for every active endpoint subscribed to it. Delivery
    happens in the worker, never in the request."""

    endpoints = WebhookEndpoint.query.filter_by(organization_id=organization_id, is_active=True).all()
    event_id = f"evt_{uuid.uuid4().hex}"
    count = 0
    for ep in endpoints:
        if event_type not in ep.events:
            continue
        body = {"id": event_id, "type": event_type, "version": EVENT_VERSION,
                "created_at": utcnow().isoformat(), "workspace_id": organization_id, "data": data}
        db.session.add(WebhookDelivery(organization_id=organization_id, endpoint_id=ep.id, event_id=event_id,
                                       event_type=event_type, payload_json=json.dumps(body), next_attempt_at=utcnow()))
        count += 1
    return count


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _send(url: str, body: bytes, headers: dict) -> int:
    opener = urllib.request.build_opener(_NoRedirect)
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with opener.open(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def deliver_due(limit: int = 20) -> int:
    now = utcnow()
    due = (WebhookDelivery.query.filter(WebhookDelivery.status == "pending",
                                        WebhookDelivery.next_attempt_at <= now)
           .order_by(WebhookDelivery.next_attempt_at).limit(limit).all())
    for d in due:
        ep = db.session.get(WebhookEndpoint, d.endpoint_id)
        d.attempts += 1
        if ep is None or not ep.is_active:
            d.status, d.last_error = "failed", "Endpoint disabled or removed."
            continue
        body = d.payload_json.encode()
        headers = {"Content-Type": "application/json", "User-Agent": "ARC-Webhooks/1",
                   "ARC-Event-Id": d.event_id, "ARC-Event-Type": d.event_type,
                   "ARC-Event-Version": EVENT_VERSION, "ARC-Signature": sign_payload(body, ep.secret)}
        try:
            validate_target_url(ep.url)
            code = _send(ep.url, body, headers)
            d.last_response_code = code
            ok = 200 <= code < 300
            d.last_error = None if ok else f"HTTP {code}"
        except UnsafeURL as exc:
            d.status, d.last_error = "failed", str(exc)[:500]
            continue
        except Exception as exc:  # noqa: BLE001 - network errors are retried
            ok, d.last_error = False, type(exc).__name__
        if ok:
            d.status = "delivered"
        elif d.attempts >= MAX_ATTEMPTS:
            d.status = "failed"
        else:
            d.next_attempt_at = now + timedelta(seconds=30 * 2 ** (d.attempts - 1))
    if due:
        db.session.commit()
    return len(due)
