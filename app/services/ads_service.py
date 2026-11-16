"""Human-approved ad launching under a hard workspace daily cap (D19).

- Agents have no code path here; every launch starts from a person.
- Launching is off until an owner/admin sets a daily cap.
- A launch comes from one ad in an approved, current paid-media plan, with a
  daily budget and an end date, and needs an approver who re-types the
  budget. The approval is a hash of exactly what will launch.
- The worker re-checks kill switch, cap, plan approval and hash before
  launching, then keeps checking live ads: kill switch on -> pause all;
  workspace spend over the cap -> pause all; end date passed -> stop."""

import hashlib
import json
from datetime import date, datetime, timedelta, timezone

from flask import current_app

from app.extensions import db
from app.integrations.ads_platforms import PLATFORMS, AdPlatformError
from app.models.ads import (
    AD_ACTIVE,
    AD_APPROVED,
    AD_FAILED,
    AD_PAUSED,
    AD_PENDING,
    AD_REJECTED,
    AD_STOPPED,
    LIVE_STATES,
    AdGuardrail,
    AdLaunch,
)
from app.models.approval import DECISION_APPROVED, Approval
from app.models.base import utcnow
from app.models.deliverable import Deliverable
from app.models.membership import APPROVAL_CAPABLE_ROLES, OPERATOR_ROLES, WORKSPACE_ADMIN_ROLES, Membership
from app.models.organization import Organization
from app.services.audit_service import record_audit_event
from app.services.errors import Conflict, NotFound, PermissionDenied, ValidationError

CHECK_EVERY = timedelta(seconds=60)


def _bad(field, issue):
    return ValidationError("Please correct the highlighted fields.", details=[{"field": field, "issue": issue}])


def _need(m: Membership, roles, what):
    if m.role not in roles:
        raise PermissionDenied(f"Your role does not permit {what}.")


def _kill(org: Organization) -> bool:
    return bool(org.kill_switch_enabled or current_app.config.get("KILL_SWITCH_ENABLED"))


def _limit() -> float:
    return float(current_app.config.get("ADS_MAX_DAILY_CAP", 1000))


# ---- guardrails ------------------------------------------------------------
def guardrail(org_id: str) -> AdGuardrail:
    g = AdGuardrail.query.filter_by(organization_id=org_id).first()
    if g is None:
        g = AdGuardrail(organization_id=org_id, max_daily_budget=0.0, currency="USD")
        db.session.add(g)
        db.session.flush()
    return g


def committed_budget(org_id: str, exclude_id: str | None = None) -> float:
    q = AdLaunch.query.filter(AdLaunch.organization_id == org_id, AdLaunch.status.in_(LIVE_STATES + (AD_PENDING,)))
    return sum(a.daily_budget for a in q if a.id != exclude_id)


def overview(org_id: str) -> dict:
    g = guardrail(org_id)
    launches = AdLaunch.query.filter_by(organization_id=org_id).order_by(AdLaunch.created_at.desc()).all()
    db.session.commit()
    spend_today = sum(a.spend_today or 0 for a in launches if a.status in LIVE_STATES or a.status == AD_STOPPED and a.stopped_at and a.stopped_at.date() == utcnow().date())
    return {"guardrail": {"max_daily_budget": g.max_daily_budget, "currency": g.currency, "limit": _limit(),
                          "committed": round(committed_budget(org_id), 2), "spend_today": round(spend_today, 2)},
            "platforms": [{"key": k, "label": v.label, "available": True} for k, v in PLATFORMS.items()],
            "launches": [a.to_dict() for a in launches]}


def set_guardrail(m: Membership, data: dict) -> dict:
    _need(m, WORKSPACE_ADMIN_ROLES, "changing the ad spend cap")
    try:
        cap = round(float(data.get("max_daily_budget")), 2)
    except (TypeError, ValueError):
        raise _bad("max_daily_budget", "Enter an amount") from None
    if not 0 <= cap <= _limit():
        raise _bad("max_daily_budget", f"Between 0 and {_limit():.0f} a day")
    currency = "USD"  # ARC works in US dollars everywhere
    if (data.get("currency") or "USD").upper() != "USD":
        raise _bad("currency", "ARC works in US dollars (USD)")
    g = guardrail(m.organization_id)
    if cap < committed_budget(m.organization_id):
        raise _bad("max_daily_budget", "Lower than the daily budgets already approved or running. Pause or stop some ads first.")
    old = g.max_daily_budget
    g.max_daily_budget, g.currency, g.updated_by_user_id = cap, currency, m.user_id
    record_audit_event(m.organization_id, "ads.cap_changed", actor_user_id=m.user_id, target_type="ad_guardrail",
                       target_id=g.id, metadata={"from": old, "to": cap, "currency": currency})
    db.session.commit()
    return overview(m.organization_id)


# ---- launch requests ---------------------------------------------------------
def _approved_plan(org_id: str, deliverable_id: str) -> Deliverable:
    d = Deliverable.query.filter_by(id=deliverable_id, organization_id=org_id).first()
    if d is None or d.deliverable_type != "paid_media_plan" or not d.current_version:
        raise NotFound("Paid media plan not found.")
    ok = Approval.query.filter_by(organization_id=org_id, deliverable_id=d.id, deliverable_version_id=d.current_version_id,
                                  decision=DECISION_APPROVED).first()
    if ok is None:
        raise Conflict("Approve the current version of this paid media plan first.")
    return d


def _hash(a: AdLaunch) -> str:
    return hashlib.sha256(json.dumps({"v": a.deliverable_version_id, "i": a.item_index, "p": a.platform, "n": a.name,
                                      "b": round(a.daily_budget, 2), "c": a.currency, "e": a.end_date.isoformat()},
                                     sort_keys=True).encode()).hexdigest()


def request_launch(m: Membership, data: dict) -> dict:
    _need(m, OPERATOR_ROLES, "requesting ad launches")
    org_id = m.organization_id
    g = guardrail(org_id)
    if g.max_daily_budget <= 0:
        raise Conflict("Set a workspace daily ad spend cap first (owner or admin).")
    platform = data.get("platform") or "sandbox"
    if platform not in PLATFORMS:
        raise _bad("platform", "That ad platform isn't connected yet")
    d = _approved_plan(org_id, data.get("deliverable_id") or "")
    items = d.current_version.to_dict()["content"].get("campaign_structure") or []
    idx = data.get("item_index", 0)
    if not isinstance(idx, int) or not 0 <= idx < len(items):
        raise _bad("item_index", "Choose an ad campaign from the plan")
    try:
        budget = round(float(data.get("daily_budget")), 2)
    except (TypeError, ValueError):
        raise _bad("daily_budget", "Enter a daily budget") from None
    remaining = g.max_daily_budget - committed_budget(org_id)
    if budget <= 0:
        raise _bad("daily_budget", "Must be more than 0")
    if budget > remaining + 1e-9:
        raise _bad("daily_budget", f"Only {remaining:.2f} {g.currency} a day is left under your cap")
    try:
        end = date.fromisoformat(data.get("end_date") or "")
    except ValueError:
        raise _bad("end_date", "Choose an end date") from None
    today = utcnow().date()
    if not today < end <= today + timedelta(days=90):
        raise _bad("end_date", "Between tomorrow and 90 days from now")
    item = items[idx]
    a = AdLaunch(organization_id=org_id, deliverable_id=d.id, deliverable_version_id=d.current_version_id, item_index=idx,
                 platform=platform, name=(item.get("name") or "Ad campaign")[:200], channel=item.get("channel"),
                 objective=item.get("objective"), audience=item.get("audience"), daily_budget=budget,
                 currency=g.currency, end_date=end, status=AD_PENDING, requested_by_user_id=m.user_id, approval_hash="")
    a.approval_hash = _hash(a)
    db.session.add(a)
    db.session.flush()
    from app.services.platform_service import notify

    notify(org_id, "ads.approval_requested", f"Ad launch “{a.name}” needs approval",
           body=f"{budget:.2f} {g.currency} a day until {end.isoformat()}", link="/app/ads")
    record_audit_event(org_id, "ads.launch_requested", actor_user_id=m.user_id, target_type="ad_launch", target_id=a.id,
                       metadata={"daily_budget": budget, "currency": g.currency, "end_date": end.isoformat(), "platform": platform})
    db.session.commit()
    return a.to_dict()


def decide(m: Membership, launch_id: str, data: dict) -> dict:
    _need(m, APPROVAL_CAPABLE_ROLES, "approving ad spend")
    a = _get(m.organization_id, launch_id)
    if a.status != AD_PENDING:
        raise Conflict("This launch isn't waiting for approval.")
    if data.get("decision") == "reject":
        a.status, a.stop_reason = AD_REJECTED, "Rejected"
    elif data.get("decision") == "approve":
        try:
            typed = round(float(data.get("confirm_daily_budget")), 2)
        except (TypeError, ValueError):
            typed = None
        if typed != round(a.daily_budget, 2):
            raise _bad("confirm_daily_budget", f"Type the daily budget ({a.daily_budget:.2f}) to confirm")
        if _hash(a) != a.approval_hash:
            raise Conflict("This launch changed after it was requested. Request it again.")
        a.status, a.approved_by_user_id, a.approved_at, a.desired_state = AD_APPROVED, m.user_id, utcnow(), "active"
    else:
        raise _bad("decision", "approve or reject")
    record_audit_event(m.organization_id, f"ads.launch_{data['decision']}d", actor_user_id=m.user_id, target_type="ad_launch",
                       target_id=a.id, metadata={"daily_budget": a.daily_budget, "currency": a.currency})
    db.session.commit()
    return a.to_dict()


def control(m: Membership, launch_id: str, action: str) -> dict:
    a = _get(m.organization_id, launch_id)
    if action == "resume":
        _need(m, APPROVAL_CAPABLE_ROLES, "resuming ad spend")
        if a.status != AD_PAUSED:
            raise Conflict("Only a paused ad can be resumed.")
        org = db.session.get(Organization, m.organization_id)
        if _kill(org):
            raise PermissionDenied("External actions are currently disabled by the kill switch.")
        g = guardrail(m.organization_id)
        if committed_budget(m.organization_id) > g.max_daily_budget + 1e-9:
            raise Conflict("Resuming would go over your daily cap.")
        a.desired_state = "active"
    elif action in ("pause", "stop"):
        _need(m, OPERATOR_ROLES, "pausing or stopping ads")  # anyone who can operate can stop spend
        if a.status not in LIVE_STATES:
            raise Conflict("This ad isn't running.")
        a.desired_state = "paused" if action == "pause" else "stopped"
        if a.status == AD_APPROVED and action == "stop":
            a.status, a.stopped_at, a.stop_reason = AD_STOPPED, utcnow(), "Stopped before launch"
    else:
        raise _bad("action", "Unknown action")
    record_audit_event(m.organization_id, f"ads.{action}", actor_user_id=m.user_id, target_type="ad_launch", target_id=a.id)
    db.session.commit()
    return a.to_dict()


def stop_all(m: Membership) -> dict:
    _need(m, OPERATOR_ROLES, "stopping ads")
    n = 0
    for a in AdLaunch.query.filter(AdLaunch.organization_id == m.organization_id, AdLaunch.status.in_(LIVE_STATES)):
        a.desired_state = "paused"
        n += 1
    record_audit_event(m.organization_id, "ads.stop_all", actor_user_id=m.user_id, target_type="organization",
                       target_id=m.organization_id, metadata={"ads": n})
    db.session.commit()
    return overview(m.organization_id)


def _get(org_id: str, launch_id: str) -> AdLaunch:
    a = AdLaunch.query.filter_by(id=launch_id, organization_id=org_id).first()
    if a is None:
        raise NotFound("Ad launch not found.")
    return a


# ---- worker --------------------------------------------------------------------
def _notify(a: AdLaunch, title: str, body: str, severity="warning"):
    from app.services.platform_service import notify

    notify(a.organization_id, "ads.guardrail", title, body=body, link="/app/ads", severity=severity)


def _pause(a: AdLaunch, platform, reason: str):
    if a.external_id and a.status == AD_ACTIVE:
        platform.pause(a.external_id)
    a.status, a.stop_reason = AD_PAUSED, reason[:300]
    record_audit_event(a.organization_id, "ads.paused_by_guardrail" if a.desired_state == "active" else "ads.paused",
                       target_type="ad_launch", target_id=a.id, metadata={"reason": reason})


def process_ads() -> bool:
    """Launch approved ads, apply requested pauses/stops, and enforce the kill
    switch, workspace cap and end dates on everything live."""
    now = utcnow()
    live = AdLaunch.query.filter(AdLaunch.status.in_(LIVE_STATES)).order_by(AdLaunch.created_at).all()
    by_org: dict[str, list[AdLaunch]] = {}
    for a in live:
        by_org.setdefault(a.organization_id, []).append(a)
    for org_id, ads in by_org.items():
        org = db.session.get(Organization, org_id)
        g = guardrail(org_id)
        for a in ads:
            platform = PLATFORMS[a.platform]()
            try:
                # 1) safety first: kill switch and end date
                if _kill(org):
                    if a.status == AD_ACTIVE:
                        _pause(a, platform, "Kill switch is on")
                        _notify(a, "Ads paused by the kill switch", a.name)
                    continue
                if a.end_date < now.date() and a.status != AD_STOPPED:
                    if a.external_id:
                        platform.archive(a.external_id)
                    a.status, a.stopped_at, a.stop_reason = AD_STOPPED, now, "End date reached"
                    continue
                # 2) what a person asked for
                if a.desired_state == "stopped":
                    if a.external_id:
                        platform.archive(a.external_id)
                    a.status, a.stopped_at, a.stop_reason = AD_STOPPED, now, "Stopped by a person"
                    record_audit_event(org_id, "ads.stopped", target_type="ad_launch", target_id=a.id)
                    continue
                if a.desired_state == "paused" and a.status in (AD_ACTIVE, AD_APPROVED):
                    if a.status == AD_APPROVED:
                        a.status, a.stop_reason = AD_PAUSED, "Paused before launch"
                    else:
                        _pause(a, platform, "Paused by a person")
                    continue
                # 3) launch an approved ad (re-checking everything)
                if a.status == AD_APPROVED:
                    if _hash(a) != a.approval_hash:
                        a.status, a.last_error = AD_FAILED, "Changed after approval; not launched."
                    elif g.max_daily_budget <= 0 or committed_budget(org_id) > g.max_daily_budget + 1e-9:
                        a.status, a.last_error = AD_FAILED, "Would exceed the workspace daily cap; not launched."
                    else:
                        try:
                            _approved_plan(org_id, a.deliverable_id)
                        except (Conflict, NotFound):
                            a.status, a.last_error = AD_FAILED, "The paid media plan changed or lost its approval; not launched."
                        else:
                            a.external_id = platform.create(name=a.name, daily_budget=a.daily_budget, idempotency_key=f"arc-{a.id}")
                            a.status, a.launched_at, a.last_error = AD_ACTIVE, now, None
                            record_audit_event(org_id, "ads.launched", target_type="ad_launch", target_id=a.id,
                                               metadata={"platform": a.platform, "external_id": a.external_id, "daily_budget": a.daily_budget})
                            _notify(a, "Ad launched", f"{a.name}: {a.daily_budget:.2f} {a.currency} a day", severity="info")
                    continue
                if a.status == AD_PAUSED and a.desired_state == "active":
                    if committed_budget(org_id) <= g.max_daily_budget + 1e-9:
                        if a.external_id:
                            platform.resume(a.external_id)
                            a.status, a.stop_reason = AD_ACTIVE, None
                        else:
                            a.status = AD_APPROVED  # paused before it ever launched
                    continue
                # 4) monitor live spend
                if a.status == AD_ACTIVE and a.external_id and (a.last_checked_at is None or _aware(a.last_checked_at) < now - CHECK_EVERY):
                    st = platform.status(a.external_id)
                    a.spend_today, a.spend_total, a.last_checked_at = st["spend_today"], st["spend_total"], now
            except AdPlatformError as exc:
                a.last_error = str(exc)[:500]
                if not exc.retryable and a.status == AD_APPROVED:
                    a.status = AD_FAILED
        # 5) workspace cap across all live ads
        today_spend = sum(x.spend_today or 0 for x in ads if x.status == AD_ACTIVE)
        if g.max_daily_budget > 0 and today_spend > g.max_daily_budget + 1e-9:
            for x in ads:
                if x.status == AD_ACTIVE:
                    _pause(x, PLATFORMS[x.platform](), "Workspace daily cap reached")
            _notify(ads[0], "Ads paused: daily cap reached", f"Spent {today_spend:.2f} of {g.max_daily_budget:.2f} {g.currency} today")
    db.session.commit()
    # A side job that runs every worker iteration; returning False lets the
    # worker carry on with agent tasks in the same iteration.
    return False


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
