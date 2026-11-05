"""Batch-approved outreach email (docs/DECISIONS.md D18).

Safeguards, all enforced here rather than in the UI:
- contacts only from lists uploaded with a lawful basis, a source and an
  attestation; nothing is scraped
- a batch is approved as a whole; the approval hash covers template, list
  snapshot, sender and daily limit, and the worker recomputes it before
  every email (any drift pauses the batch)
- workspace suppression list (unsubscribes are permanent), kill switch and
  a per-batch daily limit under a workspace-wide daily cap
- every email carries a one-click unsubscribe link + RFC 8058 headers, the
  sender's postal address and why the person is receiving it
- client-owned Brevo/Resend accounts; keys encrypted at rest"""

import csv
import hashlib
import html
import io
import json
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app
from sqlalchemy import func, update

from app.crypto import decrypt_secret, encrypt_secret
from app.extensions import db
from app.integrations import email_providers as ep
from app.models.base import utcnow
from app.models.integration import STATE_CONNECTED, STATE_DISCONNECTED, STATE_REAUTH_REQUIRED, Integration
from app.models.membership import APPROVAL_CAPABLE_ROLES, OPERATOR_ROLES, WORKSPACE_ADMIN_ROLES, Membership
from app.models.organization import Organization
from app.models.outreach import (
    BATCH_APPROVED,
    BATCH_CANCELLED,
    BATCH_COMPLETED,
    BATCH_DRAFT,
    BATCH_PAUSED,
    BATCH_PENDING,
    BATCH_SENDING,
    CONTACT_ACTIVE,
    CONTACT_UNSUBSCRIBED,
    LAWFUL_BASES,
    MSG_FAILED,
    MSG_QUEUED,
    MSG_SENDING,
    MSG_SENT,
    MSG_SKIPPED,
    OutreachBatch,
    OutreachContact,
    OutreachList,
    OutreachMessage,
    OutreachSuppression,
)
from app.services.audit_service import record_audit_event
from app.services.errors import Conflict, NotFound, PermissionDenied, ValidationError

PROVIDER = "outreach_sender"
EMAIL_RE = re.compile(r"^[^@\s<>\"',;]+@[^@\s<>\"',;]+\.[A-Za-z]{2,}$")
MAX_ROWS = 5000
LEASE = timedelta(minutes=10)


def _bad(field, issue):
    return ValidationError("Please correct the highlighted fields.", details=[{"field": field, "issue": issue}])


def _need(m: Membership, roles, what):
    if m.role not in roles:
        raise PermissionDenied(f"Your role does not permit {what}.")


def _cap() -> int:
    return int(current_app.config.get("OUTREACH_DAILY_CAP", 200))


# ---- sender ---------------------------------------------------------------
def _sender(org_id: str) -> Integration | None:
    return Integration.query.filter_by(organization_id=org_id, provider=PROVIDER).first()


def sender_status(org_id: str) -> dict:
    s = _sender(org_id)
    cfg = json.loads(s.settings_json) if s and s.settings_json else {}
    return {"connected": bool(s and s.state == STATE_CONNECTED and s.credential_ciphertext),
            "state": s.state if s else STATE_DISCONNECTED, "provider": cfg.get("provider"),
            "sender_email": cfg.get("sender_email"), "sender_name": cfg.get("sender_name"),
            "postal_address": cfg.get("postal_address"), "reply_to": cfg.get("reply_to"),
            "daily_cap": _cap()}


def connect_sender(m: Membership, data: dict) -> dict:
    _need(m, WORKSPACE_ADMIN_ROLES, "connecting an email sender")
    provider = (data.get("provider") or "").lower()
    if provider not in ep.PROVIDERS:
        raise _bad("provider", "Choose Brevo or Resend")
    key = (data.get("api_key") or "").strip()
    email = (data.get("sender_email") or "").strip().lower()
    name = (data.get("sender_name") or "").strip()[:100]
    postal = (data.get("postal_address") or "").strip()[:300]
    reply_to = (data.get("reply_to") or "").strip().lower()
    if len(key) < 10:
        raise _bad("api_key", "Paste your API key")
    if not EMAIL_RE.match(email):
        raise _bad("sender_email", "Enter the verified sender address")
    if not name:
        raise _bad("sender_name", "Required")
    if len(postal) < 10:
        raise _bad("postal_address", "Marketing email must include your postal address")
    if reply_to and not EMAIL_RE.match(reply_to):
        raise _bad("reply_to", "Enter a valid email")
    try:
        info = ep.PROVIDERS[provider](key).check()
    except ep.EmailProviderError as exc:
        raise _bad("api_key", f"{provider.title()} rejected this key ({exc})") from exc
    s = _sender(m.organization_id) or Integration(organization_id=m.organization_id, provider=PROVIDER)
    s.credential_ciphertext = encrypt_secret(key)
    s.settings_json = json.dumps({"provider": provider, "sender_email": email, "sender_name": name,
                                  "postal_address": postal, "reply_to": reply_to or None})
    s.account_label, s.external_account_id = f"{provider.title()}: {email}", email
    s.state, s.connected_by_user_id, s.connected_at = STATE_CONNECTED, m.user_id, utcnow()
    db.session.add(s)
    db.session.flush()
    _invalidate_approvals(m.organization_id, "sender changed")
    record_audit_event(m.organization_id, "integration.connected", actor_user_id=m.user_id, target_type="integration",
                       target_id=s.id, metadata={"provider": provider, "sender": email, "account": info.get("account")})
    db.session.commit()
    return sender_status(m.organization_id)


def disconnect_sender(m: Membership) -> dict:
    _need(m, WORKSPACE_ADMIN_ROLES, "disconnecting the email sender")
    s = _sender(m.organization_id)
    if s:
        s.credential_ciphertext, s.state = None, STATE_DISCONNECTED
        for b in OutreachBatch.query.filter_by(organization_id=m.organization_id, status=BATCH_SENDING):
            b.status, b.last_error = BATCH_PAUSED, "Paused: the email sender was disconnected."
        record_audit_event(m.organization_id, "integration.disconnected", actor_user_id=m.user_id,
                           target_type="integration", target_id=s.id, metadata={"provider": PROVIDER})
        db.session.commit()
    return sender_status(m.organization_id)


# ---- lists ----------------------------------------------------------------
def _suppressed(org_id: str) -> set[str]:
    return {e for (e,) in db.session.query(OutreachSuppression.email).filter_by(organization_id=org_id)}


def create_list(m: Membership, data: dict) -> dict:
    _need(m, OPERATOR_ROLES, "uploading contact lists")
    name = (data.get("name") or "").strip()[:200]
    basis = data.get("lawful_basis")
    source = (data.get("source_description") or "").strip()[:500]
    if not name:
        raise _bad("name", "Required")
    if basis not in LAWFUL_BASES:
        raise _bad("lawful_basis", "Choose how you are allowed to email these people")
    if len(source) < 10:
        raise _bad("source_description", "Say where these contacts came from")
    if data.get("attest") is not True:
        raise _bad("attest", "Confirm the contacts were collected lawfully and not scraped")
    text = data.get("csv") or ""
    if not text.strip():
        raise _bad("csv", "Upload a CSV with an email column")
    rows = list(csv.DictReader(io.StringIO(text)))
    if len(rows) > MAX_ROWS:
        raise _bad("csv", f"Up to {MAX_ROWS} contacts per list")
    cols = {(c or "").strip().lower(): c for c in (rows[0].keys() if rows else [])}
    if "email" not in cols:
        raise _bad("csv", "The CSV needs an 'email' column")
    pick = lambda r, *names: next(((r.get(cols[n]) or "").strip() for n in names if n in cols and (r.get(cols[n]) or "").strip()), "")  # noqa: E731
    lst = OutreachList(organization_id=m.organization_id, name=name, lawful_basis=basis, source_description=source,
                       attested_by_user_id=m.user_id, attested_at=utcnow())
    db.session.add(lst)
    db.session.flush()
    suppressed, seen = _suppressed(m.organization_id), set()
    stats = {"added": 0, "invalid": 0, "duplicates": 0, "suppressed": 0}
    for r in rows:
        email = pick(r, "email").lower()
        if not EMAIL_RE.match(email):
            stats["invalid"] += 1
            continue
        if email in seen:
            stats["duplicates"] += 1
            continue
        seen.add(email)
        status = CONTACT_ACTIVE
        if email in suppressed:
            stats["suppressed"] += 1
            status = CONTACT_UNSUBSCRIBED
        db.session.add(OutreachContact(organization_id=m.organization_id, list_id=lst.id, email=email,
                                       first_name=pick(r, "first_name", "first name", "name")[:100] or None,
                                       company=pick(r, "company", "organisation", "organization")[:200] or None,
                                       source=pick(r, "source")[:300] or None, status=status))
        stats["added"] += status == CONTACT_ACTIVE
    record_audit_event(m.organization_id, "outreach.list_uploaded", actor_user_id=m.user_id, target_type="outreach_list",
                       target_id=lst.id, metadata={**stats, "lawful_basis": basis, "source": source})
    db.session.commit()
    return {"list": _list_dict(lst), "stats": stats}


def _list_dict(lst: OutreachList) -> dict:
    counts = dict(db.session.query(OutreachContact.status, func.count()).filter_by(list_id=lst.id).group_by(OutreachContact.status).all())
    return lst.to_dict({"active": counts.get(CONTACT_ACTIVE, 0), "unsubscribed": counts.get(CONTACT_UNSUBSCRIBED, 0),
                        "total": sum(counts.values())})


def list_lists(org_id: str) -> list[dict]:
    return [_list_dict(x) for x in OutreachList.query.filter_by(organization_id=org_id).order_by(OutreachList.created_at.desc())]


def list_contacts(org_id: str, list_id: str) -> list[dict]:
    _get(OutreachList, org_id, list_id)
    return [c.to_dict() for c in OutreachContact.query.filter_by(organization_id=org_id, list_id=list_id).order_by(OutreachContact.email).limit(500)]


def list_suppressions(org_id: str) -> list[dict]:
    return [s.to_dict() for s in OutreachSuppression.query.filter_by(organization_id=org_id).order_by(OutreachSuppression.created_at.desc()).limit(1000)]


def suppress(org_id: str, email: str, reason: str, actor: str | None = None) -> None:
    email = (email or "").strip().lower()
    if not EMAIL_RE.match(email):
        raise _bad("email", "Enter a valid email")
    if not OutreachSuppression.query.filter_by(organization_id=org_id, email=email).first():
        db.session.add(OutreachSuppression(organization_id=org_id, email=email, reason=reason))
    OutreachContact.query.filter_by(organization_id=org_id, email=email).update({"status": CONTACT_UNSUBSCRIBED})
    record_audit_event(org_id, "outreach.suppressed", actor_user_id=actor, target_type="outreach_suppression",
                       target_id=None, metadata={"reason": reason, "email_hash": hashlib.sha256(email.encode()).hexdigest()[:16]})


def _get(model, org_id, obj_id):
    obj = model.query.filter_by(id=obj_id, organization_id=org_id).first()
    if obj is None:
        raise NotFound("Not found.")
    return obj


# ---- batches --------------------------------------------------------------
def _validate_template(subject: str, body: str):
    if not subject.strip():
        raise _bad("subject", "Required")
    if len(body.strip()) < 20:
        raise _bad("body", "Write the email")
    unknown = set(re.findall(r"\{\{\s*(\w+)\s*\}\}", subject + body)) - {"first_name", "company"}
    if unknown:
        raise _bad("body", "Only {{first_name}} and {{company}} can be filled in")


def create_batch(m: Membership, data: dict) -> dict:
    _need(m, OPERATOR_ROLES, "creating outreach batches")
    lst = _get(OutreachList, m.organization_id, data.get("list_id") or "")
    subject, body = (data.get("subject") or "")[:300], data.get("body") or ""
    _validate_template(subject, body)
    try:
        limit = int(data.get("daily_limit") or 25)
    except (TypeError, ValueError):
        raise _bad("daily_limit", "Enter a number") from None
    if not 1 <= limit <= _cap():
        raise _bad("daily_limit", f"Between 1 and {_cap()} a day")
    b = OutreachBatch(organization_id=m.organization_id, list_id=lst.id, name=(data.get("name") or lst.name)[:200],
                      subject=subject, body=body, daily_limit=limit, status=BATCH_DRAFT,
                      source_deliverable_id=data.get("source_deliverable_id"), created_by_user_id=m.user_id)
    if b.source_deliverable_id:
        from app.models.deliverable import Deliverable

        _get(Deliverable, m.organization_id, b.source_deliverable_id)
    db.session.add(b)
    db.session.flush()
    record_audit_event(m.organization_id, "outreach.batch_created", actor_user_id=m.user_id, target_type="outreach_batch", target_id=b.id)
    db.session.commit()
    return batch_dict(b)


def update_batch(m: Membership, batch_id: str, data: dict) -> dict:
    _need(m, OPERATOR_ROLES, "editing outreach batches")
    b = _get(OutreachBatch, m.organization_id, batch_id)
    if b.status not in (BATCH_DRAFT, BATCH_PENDING, BATCH_APPROVED):
        raise Conflict("A batch that has started sending can't be edited. Cancel it and create a new one.")
    subject, body = data.get("subject", b.subject)[:300], data.get("body", b.body)
    _validate_template(subject, body)
    limit = int(data.get("daily_limit", b.daily_limit))
    if not 1 <= limit <= _cap():
        raise _bad("daily_limit", f"Between 1 and {_cap()} a day")
    b.subject, b.body, b.daily_limit = subject, body, limit
    b.name = (data.get("name") or b.name)[:200]
    _reset_approval(b)
    db.session.commit()
    return batch_dict(b)


def _reset_approval(b: OutreachBatch):
    if b.status == BATCH_APPROVED:
        OutreachMessage.query.filter_by(batch_id=b.id, status=MSG_QUEUED).delete()
    if b.status in (BATCH_PENDING, BATCH_APPROVED):
        b.status = BATCH_DRAFT
    b.approval_hash, b.approved_by_user_id, b.approved_at = None, None, None


def _invalidate_approvals(org_id: str, why: str):
    for b in OutreachBatch.query.filter(OutreachBatch.organization_id == org_id,
                                        OutreachBatch.status.in_((BATCH_PENDING, BATCH_APPROVED, BATCH_SENDING, BATCH_PAUSED))):
        if b.status in (BATCH_SENDING, BATCH_PAUSED):
            b.status, b.last_error = BATCH_PAUSED, f"Paused: {why}; approve again to continue."
            b.approval_hash = None
        else:
            _reset_approval(b)


def _hash(b: OutreachBatch, contact_ids: list[str], sender: dict) -> str:
    material = json.dumps({"subject": b.subject, "body": b.body, "daily_limit": b.daily_limit, "list": b.list_id,
                           "contacts": sorted(contact_ids), "sender": [sender.get("provider"), sender.get("sender_email"),
                                                                       sender.get("sender_name"), sender.get("postal_address")]},
                          sort_keys=True)
    return hashlib.sha256(material.encode()).hexdigest()


def request_approval(m: Membership, batch_id: str) -> dict:
    _need(m, OPERATOR_ROLES, "requesting approval")
    b = _get(OutreachBatch, m.organization_id, batch_id)
    if b.status != BATCH_DRAFT:
        raise Conflict("Only a draft batch can be sent for approval.")
    b.status = BATCH_PENDING
    from app.services.platform_service import notify

    notify(m.organization_id, "outreach.approval_requested", f"Outreach batch “{b.name}” needs approval", link="/app/outreach")
    db.session.commit()
    return batch_dict(b)


def approve_batch(m: Membership, batch_id: str) -> dict:
    """Approve the exact template + recipients + sender + daily limit. The
    recipient list is frozen now: contacts added later are not emailed."""
    _need(m, APPROVAL_CAPABLE_ROLES, "approving outreach")
    b = _get(OutreachBatch, m.organization_id, batch_id)
    if b.status != BATCH_PENDING:
        raise Conflict("This batch isn't waiting for approval.")
    sender = sender_status(m.organization_id)
    if not sender["connected"]:
        raise Conflict("Connect an email sender (Brevo or Resend) before approving.")
    suppressed = _suppressed(m.organization_id)
    contacts = [c for c in OutreachContact.query.filter_by(organization_id=m.organization_id, list_id=b.list_id, status=CONTACT_ACTIVE)
                if c.email not in suppressed]
    if not contacts:
        raise Conflict("This list has no one left to email.")
    already = {cid for (cid,) in db.session.query(OutreachMessage.contact_id).filter_by(batch_id=b.id)}
    for c in contacts:
        if c.id not in already:
            db.session.add(OutreachMessage(organization_id=m.organization_id, batch_id=b.id, contact_id=c.id, status=MSG_QUEUED))
    db.session.flush()
    b.approval_hash = _hash(b, _snapshot_ids(b), sender)
    b.status, b.approved_by_user_id, b.approved_at = BATCH_APPROVED, m.user_id, utcnow()
    record_audit_event(m.organization_id, "outreach.batch_approved", actor_user_id=m.user_id, target_type="outreach_batch",
                       target_id=b.id, metadata={"recipients": len(contacts), "daily_limit": b.daily_limit,
                                                 "sender": sender["sender_email"], "hash": b.approval_hash})
    db.session.commit()
    return batch_dict(b)


def _snapshot_ids(b: OutreachBatch) -> list[str]:
    return [cid for (cid,) in db.session.query(OutreachMessage.contact_id).filter_by(batch_id=b.id)]


def set_state(m: Membership, batch_id: str, action: str) -> dict:
    b = _get(OutreachBatch, m.organization_id, batch_id)
    if action == "reject":
        _need(m, APPROVAL_CAPABLE_ROLES, "rejecting outreach")
        if b.status != BATCH_PENDING:
            raise Conflict("This batch isn't waiting for approval.")
        _reset_approval(b)
    elif action == "start":
        _need(m, APPROVAL_CAPABLE_ROLES, "starting outreach")
        if b.status not in (BATCH_APPROVED, BATCH_PAUSED) or not b.approval_hash:
            raise Conflict("Approve this batch before sending.")
        org = db.session.get(Organization, m.organization_id)
        if org.kill_switch_enabled or current_app.config.get("KILL_SWITCH_ENABLED"):
            raise PermissionDenied("External actions are currently disabled by the kill switch.")
        b.status, b.last_error = BATCH_SENDING, None
        b.started_at = b.started_at or utcnow()
    elif action == "pause":
        _need(m, OPERATOR_ROLES, "pausing outreach")
        if b.status != BATCH_SENDING:
            raise Conflict("Only a sending batch can be paused.")
        b.status = BATCH_PAUSED
    elif action == "cancel":
        _need(m, OPERATOR_ROLES, "cancelling outreach")
        if b.status in (BATCH_COMPLETED, BATCH_CANCELLED):
            raise Conflict("This batch has already finished.")
        OutreachMessage.query.filter_by(batch_id=b.id, status=MSG_QUEUED).update({"status": MSG_SKIPPED, "error": "Batch cancelled"})
        b.status, b.completed_at = BATCH_CANCELLED, utcnow()
    else:
        raise _bad("action", "Unknown action")
    record_audit_event(m.organization_id, f"outreach.batch_{action}", actor_user_id=m.user_id, target_type="outreach_batch", target_id=b.id)
    db.session.commit()
    return batch_dict(b)


def _sent_today(org_id: str, batch_id: str | None = None) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    q = OutreachMessage.query.filter(OutreachMessage.organization_id == org_id, OutreachMessage.status == MSG_SENT,
                                     OutreachMessage.sent_at >= start)
    if batch_id:
        q = q.filter(OutreachMessage.batch_id == batch_id)
    return q.count()


def batch_dict(b: OutreachBatch) -> dict:
    counts = dict(db.session.query(OutreachMessage.status, func.count()).filter_by(batch_id=b.id).group_by(OutreachMessage.status).all())
    lst = db.session.get(OutreachList, b.list_id)
    return {"id": b.id, "name": b.name, "list_id": b.list_id, "list_name": lst.name if lst else None,
            "subject": b.subject, "body": b.body, "daily_limit": b.daily_limit, "status": b.status,
            "approved_at": b.approved_at.isoformat() if b.approved_at else None, "last_error": b.last_error,
            "counts": {k: counts.get(k, 0) for k in (MSG_QUEUED, MSG_SENDING, MSG_SENT, MSG_FAILED, MSG_SKIPPED)},
            "sent_today": _sent_today(b.organization_id, b.id), "created_at": b.created_at.isoformat()}


def list_batches(org_id: str) -> list[dict]:
    return [batch_dict(b) for b in OutreachBatch.query.filter_by(organization_id=org_id).order_by(OutreachBatch.created_at.desc())]


# ---- rendering ------------------------------------------------------------
def _fill(text: str, contact: OutreachContact) -> str:
    vals = {"first_name": contact.first_name or "there", "company": contact.company or "your business"}
    return re.sub(r"\{\{\s*(first_name|company)\s*\}\}", lambda mm: vals[mm.group(1)], text)


def render(b: OutreachBatch, contact: OutreachContact, sender: dict, unsub_url: str, reason: str) -> dict:
    subject = _fill(b.subject, contact).replace("\r", " ").replace("\n", " ")[:300]
    body = _fill(b.body, contact)
    footer = (f"You're receiving this because {reason}.\n"
              f"{sender['sender_name']}, {sender['postal_address']}\n"
              f"Unsubscribe: {unsub_url}")
    text = f"{body}\n\n--\n{footer}"
    paras = "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in body.split("\n\n") if p.strip())
    html_body = (f"{paras}<hr><p style=\"font-size:12px;color:#666\">You're receiving this because {html.escape(reason)}.<br>"
                 f"{html.escape(sender['sender_name'])}, {html.escape(sender['postal_address'])}<br>"
                 f"<a href=\"{html.escape(unsub_url)}\">Unsubscribe</a></p>")
    return {"subject": subject, "text": text, "html": html_body}


def preview(org_id: str, batch_id: str) -> dict:
    b = _get(OutreachBatch, org_id, batch_id)
    c = OutreachContact.query.filter_by(list_id=b.list_id, status=CONTACT_ACTIVE).first() or \
        OutreachContact(first_name="Alex", company="Example Ltd", email="alex@example.com")
    sender = sender_status(org_id)
    if not sender["connected"]:
        sender = {**sender, "sender_name": sender.get("sender_name") or "Your business", "postal_address": sender.get("postal_address") or "Your postal address"}
    lst = db.session.get(OutreachList, b.list_id)
    return {"to": c.email, **render(b, c, sender, "https://…/unsubscribe", _reason(lst, c))}


def _reason(lst: OutreachList | None, c: OutreachContact) -> str:
    """Finishes the sentence "You're receiving this because ..."."""
    if c.source:
        return c.source[:200]
    if lst is None:
        return "you're on our contact list"
    return {"consent": "you signed up to hear from us",
            "existing_customer": "you're a customer of ours"}.get(lst.lawful_basis, lst.source_description)[:200]


# ---- worker ---------------------------------------------------------------
def _pause(b: OutreachBatch, why: str):
    b.status, b.last_error = BATCH_PAUSED, why[:500]
    from app.services.platform_service import notify

    notify(b.organization_id, "outreach.paused", f"Outreach batch “{b.name}” paused", body=why[:300], link="/app/outreach", severity="warning")


def process_next_outreach() -> bool:
    now = utcnow()
    # Uncertain attempts: Resend dedupes by idempotency key, so retry; otherwise never risk a double email.
    for msg in OutreachMessage.query.filter(OutreachMessage.status == MSG_SENDING, OutreachMessage.updated_at < now - LEASE).limit(50):
        s = sender_status(msg.organization_id)
        if s.get("provider") == "resend":
            msg.status = MSG_QUEUED
        else:
            msg.status, msg.error = MSG_FAILED, "Interrupted mid-send; not retried to avoid a duplicate email."
    db.session.commit()
    gap = timedelta(seconds=float(current_app.config.get("OUTREACH_SECONDS_BETWEEN", 4)))
    for b in OutreachBatch.query.filter_by(status=BATCH_SENDING).order_by(OutreachBatch.started_at):
        org = db.session.get(Organization, b.organization_id)
        if org.kill_switch_enabled or current_app.config.get("KILL_SWITCH_ENABLED"):
            continue
        if _sent_today(b.organization_id, b.id) >= b.daily_limit or _sent_today(b.organization_id) >= _cap():
            continue
        last = db.session.query(func.max(OutreachMessage.sent_at)).filter(OutreachMessage.batch_id == b.id).scalar()
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        if last is not None and last > now - gap:
            continue
        sender = sender_status(b.organization_id)
        integ = _sender(b.organization_id)
        if not sender["connected"] or integ is None:
            _pause(b, "The email sender is not connected.")
            db.session.commit()
            return True
        if _hash(b, _snapshot_ids(b), sender) != b.approval_hash:
            _pause(b, "The batch changed after approval; approve it again to continue.")
            db.session.commit()
            return True
        msg = OutreachMessage.query.filter_by(batch_id=b.id, status=MSG_QUEUED).order_by(OutreachMessage.created_at).first()
        if msg is None:
            b.status, b.completed_at = BATCH_COMPLETED, now
            from app.services.platform_service import notify

            notify(b.organization_id, "outreach.completed", f"Outreach batch “{b.name}” finished", link="/app/outreach")
            db.session.commit()
            return True
        claimed = db.session.execute(update(OutreachMessage).where(OutreachMessage.id == msg.id, OutreachMessage.status == MSG_QUEUED)
                                     .values(status=MSG_SENDING, updated_at=now))
        db.session.commit()
        if claimed.rowcount != 1:
            return True
        msg = db.session.get(OutreachMessage, msg.id)
        contact = db.session.get(OutreachContact, msg.contact_id)
        if contact.status != CONTACT_ACTIVE or OutreachSuppression.query.filter_by(organization_id=b.organization_id, email=contact.email).first():
            msg.status, msg.error = MSG_SKIPPED, "Unsubscribed or suppressed"
            db.session.commit()
            return True
        token = secrets.token_urlsafe(24)
        msg.unsubscribe_token_hash = hashlib.sha256(token.encode()).hexdigest()
        origin = current_app.config.get("FRONTEND_ORIGIN", "").rstrip("/")
        page_url, one_click = f"{origin}/unsubscribe/{token}", f"{origin}/api/v1/outreach/unsubscribe/{token}"
        content = render(b, contact, sender, page_url, _reason(db.session.get(OutreachList, b.list_id), contact))
        key = decrypt_secret(integ.credential_ciphertext or "")
        try:
            pid = ep.PROVIDERS[sender["provider"]](key or "").send(
                sender_email=sender["sender_email"], sender_name=sender["sender_name"], to_email=contact.email,
                to_name=contact.first_name, subject=content["subject"], html=content["html"], text=content["text"],
                headers={"List-Unsubscribe": f"<{one_click}>", "List-Unsubscribe-Post": "List-Unsubscribe=One-Click"},
                reply_to=sender.get("reply_to"), idempotency_key=f"arc-{msg.id}")
        except ep.EmailProviderError as exc:
            if exc.status in (401, 403):
                integ.state = STATE_REAUTH_REQUIRED
                msg.status, msg.error = MSG_QUEUED, None
                _pause(b, "Your email provider rejected ARC's key. Reconnect the sender in Outreach.")
            elif exc.retryable:
                msg.status, msg.error = MSG_QUEUED, str(exc)[:500]
            else:
                msg.status, msg.error = MSG_FAILED, str(exc)[:500]
            db.session.commit()
            return True
        msg.status, msg.provider_message_id, msg.sent_at, msg.error = MSG_SENT, (pid or "")[:200], utcnow(), None
        db.session.commit()
        return True
    return False


# ---- unsubscribe ----------------------------------------------------------
def unsubscribe(token: str) -> dict:
    h = hashlib.sha256((token or "").encode()).hexdigest()
    msg = OutreachMessage.query.filter_by(unsubscribe_token_hash=h).first()
    if msg is None:
        raise NotFound("This unsubscribe link isn't valid.")
    contact = db.session.get(OutreachContact, msg.contact_id)
    suppress(msg.organization_id, contact.email, "unsubscribed")
    db.session.commit()
    org = db.session.get(Organization, msg.organization_id)
    sender = sender_status(msg.organization_id)
    return {"unsubscribed": True, "from": sender.get("sender_name") or (org.name if org else "this sender")}

