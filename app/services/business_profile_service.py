import re

from app.extensions import db
from app.models.business_profile import BusinessProfile
from app.models.document import Document
from app.services.audit_service import record_audit_event
from app.services.errors import ValidationError

_HEX = re.compile(r"^#?[0-9a-fA-F]{6}$")
MAX_BRAND_COLORS = 8

EDITABLE_FIELDS = (
    "business_name", "website", "industry", "regions_served", "business_type",
    "products_services", "target_audience", "customer_problem", "differentiators",
    "primary_goal", "tone_of_voice", "preferred_phrases", "prohibited_phrases",
    "constraints", "business_description", "competitors", "channels", "budget_range",
    "existing_systems", "reporting_expectations", "timezone", "language", "onboarding_step",
    "brand_persona", "brand_fonts", "visual_guidelines",
)


def normalise_brand_colors(raw) -> str | None:
    """'#0A2540, 635bff' -> '#0A2540,#635BFF'. Rejects anything that isn't a 6-digit hex."""

    if raw in (None, ""):
        return None
    parts = [p.strip() for p in re.split(r"[,\s]+", str(raw)) if p.strip()]
    bad = [p for p in parts if not _HEX.match(p)]
    if bad or len(parts) > MAX_BRAND_COLORS:
        raise ValidationError("Please correct the highlighted fields.", details=[{
            "field": "brand_colors",
            "issue": f"Use up to {MAX_BRAND_COLORS} hex colours like #0A2540" + (f" (not: {', '.join(bad[:3])})" if bad else ""),
        }])
    return ",".join("#" + p.lstrip("#").upper() for p in parts)


def brand_palette(profile) -> list[str]:
    return [c for c in (profile.brand_colors or "").split(",") if c] if profile else []



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
    if "brand_colors" in payload:
        profile.brand_colors = normalise_brand_colors(payload["brand_colors"])
    if "logo_document_id" in payload:
        doc_id = payload["logo_document_id"] or None
        if doc_id:
            doc = Document.query.filter_by(id=doc_id, organization_id=organization_id, status="stored").first()
            if doc is None or not (doc.content_type or "").startswith("image/"):
                raise ValidationError("Please correct the highlighted fields.", details=[
                    {"field": "logo_document_id", "issue": "Choose an image uploaded to this workspace's Assets"}])
        profile.logo_document_id = doc_id
    if payload.get("mark_onboarding_completed"):
        profile.onboarding_completed = True
    db.session.flush()
    record_audit_event(
        organization_id, "business_profile.updated", actor_user_id=user_id,
        target_type="business_profile", target_id=profile.id,
    )
    db.session.commit()
    return profile
