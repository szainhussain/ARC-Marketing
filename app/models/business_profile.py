from app.extensions import db
from app.models.base import TimestampMixin, UUIDPrimaryKeyMixin


class BusinessProfile(UUIDPrimaryKeyMixin, TimestampMixin, db.Model):
    """One structured business/brand profile per organization.

    Fields map to the onboarding steps in the UI/UX spec (business basics,
    offer & audience, brand). All fields are optional at the database level;
    the API layer enforces which fields are required before a campaign
    workflow may run, so users can skip and return later without losing
    progress.
    """

    __tablename__ = "business_profiles"

    organization_id = db.Column(
        db.String(36),
        db.ForeignKey("organizations.id"),
        unique=True,
        nullable=False,
    )

    business_name = db.Column(db.String(255))
    website = db.Column(db.String(500))
    industry = db.Column(db.String(255))
    regions_served = db.Column(db.String(500))
    business_type = db.Column(db.String(32))  # b2b | b2c | both | nonprofit | other

    products_services = db.Column(db.Text)
    target_audience = db.Column(db.Text)
    customer_problem = db.Column(db.Text)
    differentiators = db.Column(db.Text)
    primary_goal = db.Column(db.String(255))

    tone_of_voice = db.Column(db.Text)
    preferred_phrases = db.Column(db.Text)
    prohibited_phrases = db.Column(db.Text)
    constraints = db.Column(db.Text)

    # Extended onboarding (brief §12)
    business_description = db.Column(db.Text)
    competitors = db.Column(db.Text)
    channels = db.Column(db.Text)
    budget_range = db.Column(db.String(64))
    existing_systems = db.Column(db.Text)
    reporting_expectations = db.Column(db.Text)
    timezone = db.Column(db.String(64))
    language = db.Column(db.String(64))
    onboarding_step = db.Column(db.Integer, default=0, nullable=False)

    onboarding_completed = db.Column(db.Boolean, default=False, nullable=False)

    organization = db.relationship("Organization", back_populates="business_profile")

    def completeness_warnings(self) -> list[str]:
        """Fields that materially affect campaign quality if missing.

        Used by the workflow to decide between generating output and
        returning a needs_input/clarification state, per the governance
        requirement to never silently invent business facts.
        """
        required = {
            "business_name": self.business_name,
            "industry": self.industry,
            "products_services": self.products_services,
            "target_audience": self.target_audience,
            "primary_goal": self.primary_goal,
        }
        return [field for field, value in required.items() if not value]

    def to_dict(self) -> dict:
        return {
            "organization_id": self.organization_id,
            "business_name": self.business_name,
            "website": self.website,
            "industry": self.industry,
            "regions_served": self.regions_served,
            "business_type": self.business_type,
            "products_services": self.products_services,
            "target_audience": self.target_audience,
            "customer_problem": self.customer_problem,
            "differentiators": self.differentiators,
            "primary_goal": self.primary_goal,
            "tone_of_voice": self.tone_of_voice,
            "preferred_phrases": self.preferred_phrases,
            "prohibited_phrases": self.prohibited_phrases,
            "constraints": self.constraints,
            "business_description": self.business_description,
            "competitors": self.competitors,
            "channels": self.channels,
            "budget_range": self.budget_range,
            "existing_systems": self.existing_systems,
            "reporting_expectations": self.reporting_expectations,
            "timezone": self.timezone,
            "language": self.language,
            "onboarding_step": self.onboarding_step,
            "completeness_warnings": self.completeness_warnings(),
            "onboarding_completed": self.onboarding_completed,
        }
