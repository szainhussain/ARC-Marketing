from marshmallow import Schema, ValidationError, fields, pre_load, validate, validates_schema


class StrategySchema(Schema):
    strategic_direction = fields.String(required=True)
    key_objectives = fields.List(fields.String(), required=True)
    assumptions = fields.List(fields.String(), load_default=list)
    sources = fields.List(fields.String(), load_default=list)


class ResearchNotesSchema(Schema):
    audience_hypotheses = fields.List(fields.String(), required=True)
    competitor_notes = fields.List(fields.String(), load_default=list)
    assumptions = fields.List(fields.String(), load_default=list)
    sources = fields.List(fields.String(), load_default=list)
    scope_note = fields.String(load_default="")


class TimelinePhaseSchema(Schema):
    phase = fields.String(required=True)
    activities = fields.List(fields.String(), load_default=list)


class CampaignPlanSchema(Schema):
    summary = fields.String(required=True)
    channels = fields.List(fields.String(), required=True)
    timeline = fields.List(fields.Nested(TimelinePhaseSchema), load_default=list)
    success_metrics = fields.List(fields.String(), load_default=list)
    assumptions = fields.List(fields.String(), load_default=list)


class ContentVariantSchema(Schema):
    channel = fields.String(required=True)
    headline = fields.String(required=True)
    body = fields.String(required=True)


class ContentPackSchema(Schema):
    creative_brief = fields.String(required=True)
    variants = fields.List(fields.Nested(ContentVariantSchema), required=True)
    calendar_notes = fields.String(load_default="")


class QAReportSchema(Schema):
    passed = fields.Boolean(required=True)
    issues = fields.List(fields.String(), load_default=list)
    checked = fields.List(
        fields.String(),
        load_default=list,
        validate=validate.Length(min=0),
    )


class SocialPostSchema(Schema):
    day = fields.String(required=True)
    channel = fields.String(required=True)
    caption = fields.String(required=True)
    hashtags = fields.List(fields.String(), load_default=list)
    cta = fields.String(load_default="")


class SocialCalendarSchema(Schema):
    channels = fields.List(fields.String(), required=True)
    calendar_entries = fields.List(fields.Nested(SocialPostSchema), required=True)
    community_guidelines = fields.List(fields.String(), load_default=list)
    escalation_triggers = fields.List(fields.String(), load_default=list)
    assumptions = fields.List(fields.String(), load_default=list)


class TargetProfileSchema(Schema):
    target_type = fields.String(required=True)
    fit_criteria = fields.String(required=True)
    why_relevant = fields.String(required=True)


class OutreachDraftSchema(Schema):
    target_type = fields.String(required=True)
    channel = fields.String(required=True)
    subject = fields.String(load_default="")
    message = fields.String(required=True)


class OutreachPlanSchema(Schema):
    target_profiles = fields.List(fields.Nested(TargetProfileSchema), required=True)
    outreach_drafts = fields.List(fields.Nested(OutreachDraftSchema), load_default=list)
    event_ideas = fields.List(fields.String(), load_default=list)
    assumptions = fields.List(fields.String(), load_default=list)


class AdCampaignSchema(Schema):
    name = fields.String(required=True)
    channel = fields.String(required=True)
    objective = fields.String(required=True)
    audience = fields.String(required=True)


class BudgetShareSchema(Schema):
    channel = fields.String(required=True)
    share_percent = fields.Float(required=True)
    rationale = fields.String(required=True)


class PaidMediaPlanSchema(Schema):
    campaign_structure = fields.List(fields.Nested(AdCampaignSchema), required=True)
    budget_allocation_recommendation = fields.List(fields.Nested(BudgetShareSchema), load_default=list)
    bid_strategy = fields.String(load_default="")
    experiments = fields.List(fields.String(), load_default=list)
    kpi_targets = fields.List(fields.String(), load_default=list)
    assumptions = fields.List(fields.String(), load_default=list)


class KeywordThemeSchema(Schema):
    theme = fields.String(required=True)
    search_intent = fields.String(required=True)
    priority = fields.String(required=True)


class MetadataDraftSchema(Schema):
    page = fields.String(required=True)
    title = fields.String(required=True)
    meta_description = fields.String(required=True)


class SiteOptimizationSchema(Schema):
    keyword_themes = fields.List(fields.Nested(KeywordThemeSchema), required=True)
    landing_page_recommendations = fields.List(fields.String(), load_default=list)
    metadata_drafts = fields.List(fields.Nested(MetadataDraftSchema), load_default=list)
    conversion_experiments = fields.List(fields.String(), load_default=list)
    assumptions = fields.List(fields.String(), load_default=list)


class CustomerThemeSchema(Schema):
    theme = fields.String(required=True)
    evidence_basis = fields.String(required=True)
    implication = fields.String(required=True)


class ResponseTemplateSchema(Schema):
    situation = fields.String(required=True)
    draft_response = fields.String(required=True)
    escalate_to_human = fields.Boolean(required=True)


class CustomerInsightsSchema(Schema):
    data_note = fields.String(required=True)
    themes = fields.List(fields.Nested(CustomerThemeSchema), required=True)
    likely_objections = fields.List(fields.String(), load_default=list)
    response_templates = fields.List(fields.Nested(ResponseTemplateSchema), load_default=list)
    assumptions = fields.List(fields.String(), load_default=list)


class AccountSegmentSchema(Schema):
    segment = fields.String(required=True)
    opportunity = fields.String(required=True)
    priority = fields.String(required=True)


class AccountPlanSchema(Schema):
    account_segments = fields.List(fields.Nested(AccountSegmentSchema), required=True)
    enablement_materials = fields.List(fields.String(), load_default=list)
    co_marketing_ideas = fields.List(fields.String(), load_default=list)
    assumptions = fields.List(fields.String(), load_default=list)


class ActionItemSchema(Schema):
    item = fields.String(required=True)
    owner_agent = fields.String(required=True)
    due = fields.String(load_default="")


class CampaignRecordSchema(Schema):
    summary = fields.String(required=True)
    key_decisions = fields.List(fields.String(), load_default=list)
    action_items = fields.List(fields.Nested(ActionItemSchema), load_default=list)
    knowledge_updates = fields.List(fields.String(), load_default=list)
    open_questions = fields.List(fields.String(), load_default=list)


SCHEMAS_BY_TASK_TYPE = {
    "strategy": StrategySchema,
    "research_notes": ResearchNotesSchema,
    "campaign_plan": CampaignPlanSchema,
    "content_pack": ContentPackSchema,
    "qa_report": QAReportSchema,
    "social_calendar": SocialCalendarSchema,
    "outreach_plan": OutreachPlanSchema,
    "paid_media_plan": PaidMediaPlanSchema,
    "site_optimization_plan": SiteOptimizationSchema,
    "customer_insights": CustomerInsightsSchema,
    "account_plan": AccountPlanSchema,
    "campaign_record": CampaignRecordSchema,
}


# ---- Ask ARC (workspace assistant) -------------------------------------------
# Not a deliverable type, so it is deliberately not in SCHEMAS_BY_TASK_TYPE.

ASSISTANT_ACTIONS = ("none", "create_campaign", "open_approvals", "record_results", "open_reports",
                     "open_brand", "open_knowledge", "contact_team")


class AssistantActionSchema(Schema):
    type = fields.String(required=True, validate=validate.OneOf(ASSISTANT_ACTIONS))
    label = fields.String(load_default="")


class AssistantAnswerSchema(Schema):
    # What the workspace data says (may be empty for a purely general question).
    answer = fields.String(load_default="")
    # General senior-consultant advice; never presented as the client's facts.
    expert_advice = fields.String(load_default="")
    source_ids = fields.List(fields.String(), load_default=list)
    suggested_action = fields.Nested(AssistantActionSchema, load_default=lambda: {"type": "none", "label": ""})

    @pre_load
    def _tolerate_shapes(self, data, **kwargs):
        """Weaker models send the action as a bare string or ids as numbers;
        normalise those shapes (the answer itself is still required)."""

        if not isinstance(data, dict):
            return data
        data = dict(data)
        action = data.get("suggested_action")
        if action is None or action == "":
            data.pop("suggested_action", None)
        elif isinstance(action, str):
            data["suggested_action"] = {"type": action if action in ASSISTANT_ACTIONS else "none", "label": ""}
        elif isinstance(action, dict) and action.get("type") not in ASSISTANT_ACTIONS:
            data["suggested_action"] = {"type": "none", "label": str(action.get("label") or "")}
        for text_field in ("answer", "expert_advice"):
            if data.get(text_field) is None:
                data.pop(text_field, None)
        ids = data.get("source_ids")
        if isinstance(ids, (str, int)):
            ids = [ids]
        if isinstance(ids, list):
            data["source_ids"] = [str(i) for i in ids if isinstance(i, (str, int))]
        return data

    @validates_schema
    def _needs_some_content(self, data, **kwargs):
        if not (data.get("answer") or "").strip() and not (data.get("expert_advice") or "").strip():
            raise ValidationError("answer or expert_advice is required", field_name="answer")
