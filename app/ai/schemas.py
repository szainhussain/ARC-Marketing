from marshmallow import Schema, fields, validate


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


SCHEMAS_BY_TASK_TYPE = {
    "strategy": StrategySchema,
    "research_notes": ResearchNotesSchema,
    "campaign_plan": CampaignPlanSchema,
    "content_pack": ContentPackSchema,
    "qa_report": QAReportSchema,
}
