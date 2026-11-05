"""Always-on campaigns: a campaign set to repeat monthly gets a new department
run on its chosen day. The run goes through the normal enqueue path, so plan
limits, budgets, pause and approval rules all still apply; nothing is
published without approval. One run per campaign per month (idempotency key)."""

import logging
from datetime import datetime, timezone

from app.extensions import db
from app.models.base import utcnow
from app.models.campaign import STATUS_ARCHIVED, Campaign
from app.models.organization import Organization
from app.services.audit_service import record_audit_event
from app.services.errors import AppError, ValidationError

log = logging.getLogger(__name__)


def next_occurrence(day: int, after: datetime) -> datetime:
    """The next `day` of a month at 09:00 UTC strictly after `after`."""

    after = after if after.tzinfo else after.replace(tzinfo=timezone.utc)
    year, month = after.year, after.month
    candidate = datetime(year, month, day, 9, 0, tzinfo=timezone.utc)
    if candidate <= after:
        month += 1
        if month == 13:
            year, month = year + 1, 1
        candidate = datetime(year, month, day, 9, 0, tzinfo=timezone.utc)
    return candidate


def set_recurrence(campaign: Campaign, user_id: str, recurrence: str, day) -> Campaign:
    if recurrence not in ("none", "monthly"):
        raise ValidationError("Please correct the highlighted fields.",
                              details=[{"field": "recurrence", "issue": "Use 'none' or 'monthly'"}])
    if recurrence == "monthly":
        try:
            day = int(day)
        except (TypeError, ValueError):
            day = 0
        if not 1 <= day <= 28:
            raise ValidationError("Please correct the highlighted fields.",
                                  details=[{"field": "recurrence_day", "issue": "Choose a day from 1 to 28"}])
        campaign.recurrence, campaign.recurrence_day = "monthly", day
        campaign.next_run_at = next_occurrence(day, utcnow())
        campaign.recurrence_set_by_user_id = user_id
    else:
        campaign.recurrence, campaign.recurrence_day, campaign.next_run_at = "none", None, None
    record_audit_event(campaign.organization_id, "campaign.recurrence_set", actor_user_id=user_id,
                       target_type="campaign", target_id=campaign.id,
                       metadata={"recurrence": recurrence, "day": campaign.recurrence_day})
    db.session.commit()
    return campaign


def run_due_recurrences(now: datetime | None = None) -> int:
    from app.services.platform_service import notify
    from app.workflows.engine import enqueue_campaign_run

    now = now or utcnow()
    due_ids = [c.id for c in Campaign.query.filter(Campaign.recurrence == "monthly", Campaign.next_run_at <= now,
                                                   Campaign.status != STATUS_ARCHIVED).all()]
    started = 0
    for cid in due_ids:
        c = db.session.get(Campaign, cid)
        org = db.session.get(Organization, c.organization_id)
        key = f"recur-{c.id}-{now:%Y-%m}"
        org_id, name, day = c.organization_id, c.name, c.recurrence_day or 1
        owner = c.recurrence_set_by_user_id or c.created_by_user_id
        if org is None or org.status != "active":
            c.next_run_at = next_occurrence(day, now)
            db.session.commit()
            continue
        try:
            enqueue_campaign_run(org_id, cid, owner, key)
            notify(org_id, "campaign.recurring_run", f"Monthly run started for {name}",
                   body="Your marketing department is preparing this month's work. Drafts will wait for your approval.",
                   link=f"/app/campaigns/{cid}/workflow", severity="info")
            started += 1
        except AppError as exc:
            db.session.rollback()
            notify(org_id, "campaign.recurring_run_blocked", f"Monthly run for {name} could not start",
                   body=exc.message, link="/app/billing", severity="warning")
        c = db.session.get(Campaign, cid)
        c.next_run_at = next_occurrence(day, now)
        db.session.commit()
    if started:
        log.warning("Started %s recurring campaign run(s)", started)
    return started
