from app.extensions import db
from app.models.campaign import Campaign, VALID_STATUSES
from app.services.audit_service import record_audit_event
from app.services.errors import Conflict, NotFound, ValidationError


REQUIRED_FIELDS = ("name", "objective")


def _parse_date(value):
    from datetime import date

    if value in (None, ""):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


MAX_RESEARCH_URLS = 5


def normalise_research_urls(raw) -> str | None:
    """Accepts a list or newline/space-separated text; returns newline-joined https URLs."""

    from app.services.website_import import ImportFailed, normalise_url

    if raw in (None, "", []):
        return None
    items = raw if isinstance(raw, list) else str(raw).replace(",", "\n").split()
    items = [str(i).strip() for i in items if str(i).strip()]
    if len(items) > MAX_RESEARCH_URLS:
        raise ValueError(f"Add up to {MAX_RESEARCH_URLS} pages")
    out = []
    for i in items:
        try:
            out.append(normalise_url(i))
        except ImportFailed:
            raise ValueError(f"Not a web address: {i[:60]}")
    return "\n".join(dict.fromkeys(out)) or None


def validate_campaign_payload(payload: dict) -> list[dict]:
    errors = []
    parsed = {}
    for field in ("start_date", "end_date"):
        try:
            parsed[field] = _parse_date(payload.get(field))
        except ValueError:
            errors.append({"field": field, "issue": "Use YYYY-MM-DD"})
    if parsed.get("start_date") and parsed.get("end_date") and parsed["end_date"] < parsed["start_date"]:
        errors.append({"field": "end_date", "issue": "Must be on or after the start date"})
    for field, limit in (("name", 255), ("geography", 255), ("channels", 500), ("budget_guidance", 255)):
        if payload.get(field) and len(str(payload[field])) > limit:
            errors.append({"field": field, "issue": f"Must be {limit} characters or fewer"})
    for field in REQUIRED_FIELDS:
        if not (payload.get(field) or "").strip():
            errors.append({"field": field, "issue": "Required"})
    if "research_urls" in payload:
        try:
            normalise_research_urls(payload.get("research_urls"))
        except ValueError as exc:
            errors.append({"field": "research_urls", "issue": str(exc)})
    status = payload.get("status")
    if status is not None and status not in VALID_STATUSES:
        errors.append({"field": "status", "issue": "Invalid status"})
    return errors


def create_campaign(organization_id: str, user_id: str, payload: dict) -> Campaign:
    idempotency_key = payload.get("idempotency_key")
    if idempotency_key:
        existing = Campaign.query.filter_by(
            organization_id=organization_id, idempotency_key=idempotency_key
        ).first()
        if existing:
            return existing

    errors = validate_campaign_payload(payload)
    if errors:
        raise ValidationError("Please correct the highlighted fields.", details=errors)

    campaign = Campaign(
        organization_id=organization_id,
        created_by_user_id=user_id,
        name=payload["name"].strip(),
        objective=payload["objective"].strip(),
        audience=payload.get("audience"),
        offer=payload.get("offer"),
        geography=payload.get("geography"),
        channels=payload.get("channels"),
        start_date=_parse_date(payload.get("start_date")),
        end_date=_parse_date(payload.get("end_date")),
        budget_guidance=payload.get("budget_guidance"),
        constraints=payload.get("constraints"),
        success_metrics=payload.get("success_metrics"),
        research_urls=normalise_research_urls(payload.get("research_urls")),
        idempotency_key=idempotency_key,
    )
    db.session.add(campaign)
    db.session.flush()
    record_audit_event(
        organization_id, "campaign.created", actor_user_id=user_id,
        target_type="campaign", target_id=campaign.id,
    )
    db.session.commit()
    return campaign


def get_campaign_or_404(organization_id: str, campaign_id: str) -> Campaign:
    campaign = Campaign.query.filter_by(
        id=campaign_id, organization_id=organization_id
    ).first()
    if campaign is None:
        raise NotFound("Campaign not found.")
    return campaign


def list_campaigns(organization_id: str) -> list[Campaign]:
    return (
        Campaign.query.filter_by(organization_id=organization_id)
        .order_by(Campaign.created_at.desc())
        .all()
    )


def update_campaign(organization_id: str, campaign_id: str, user_id: str, payload: dict) -> Campaign:
    campaign = get_campaign_or_404(organization_id, campaign_id)
    merged = {**campaign.to_dict(), **payload}
    errors = validate_campaign_payload(merged)
    if errors:
        raise ValidationError("Please correct the highlighted fields.", details=errors)

    for field in (
        "name", "objective", "audience", "offer", "geography", "channels",
        "start_date", "end_date", "budget_guidance", "constraints", "success_metrics",
    ):
        if field in payload:
            value = payload[field]
            setattr(campaign, field, _parse_date(value) if field.endswith("_date") else value)
    if "research_urls" in payload:
        campaign.research_urls = normalise_research_urls(payload["research_urls"])

    db.session.flush()
    record_audit_event(
        organization_id, "campaign.updated", actor_user_id=user_id,
        target_type="campaign", target_id=campaign.id,
    )
    db.session.commit()
    return campaign


def archive_campaign(organization_id: str, campaign_id: str, user_id: str) -> Campaign:
    campaign = get_campaign_or_404(organization_id, campaign_id)
    campaign.status = "archived"
    db.session.flush()
    record_audit_event(
        organization_id, "campaign.archived", actor_user_id=user_id,
        target_type="campaign", target_id=campaign.id,
    )
    db.session.commit()
    return campaign
