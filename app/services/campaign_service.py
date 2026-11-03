from app.extensions import db
from app.models.campaign import Campaign, VALID_STATUSES
from app.services.audit_service import record_audit_event
from app.services.errors import Conflict, NotFound, ValidationError


REQUIRED_FIELDS = ("name", "objective")


def validate_campaign_payload(payload: dict) -> list[dict]:
    errors = []
    for field in REQUIRED_FIELDS:
        if not (payload.get(field) or "").strip():
            errors.append({"field": field, "issue": "Required"})
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
        start_date=payload.get("start_date"),
        end_date=payload.get("end_date"),
        budget_guidance=payload.get("budget_guidance"),
        constraints=payload.get("constraints"),
        success_metrics=payload.get("success_metrics"),
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
            setattr(campaign, field, payload[field])

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
