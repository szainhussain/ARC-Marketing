from app.extensions import db
from app.models.business_profile import BusinessProfile
from app.services.audit_service import record_audit_event

EDITABLE_FIELDS = (
    "business_name", "website", "industry", "regions_served", "business_type",
    "products_services", "target_audience", "customer_problem", "differentiators",
    "primary_goal", "tone_of_voice", "preferred_phrases", "prohibited_phrases",
    "constraints",
)


def get_or_create_profile(organization_id: str) -> BusinessProfile:
    profile = BusinessProfile.query.filter_by(organization_id=organization_id).first()
    if profile is None:
        profile = BusinessProfile(organization_id=organization_id)
        db.session.add(profile)
        db.session.commit()
    return profile


def update_profile(organization_id: str, user_id: str, payload: dict) -> BusinessProfile:
    profile = get_or_create_profile(organization_id)
    for field in EDITABLE_FIELDS:
        if field in payload:
            setattr(profile, field, payload[field])
    if payload.get("mark_onboarding_completed"):
        profile.onboarding_completed = True
    db.session.flush()
    record_audit_event(
        organization_id, "business_profile.updated", actor_user_id=user_id,
        target_type="business_profile", target_id=profile.id,
    )
    db.session.commit()
    return profile
