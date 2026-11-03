from app.agents.base import AgentStage, StageContext


class QualityReviewerStage(AgentStage):
    """Quality Reviewer / Marketing Operations: checks schema validity,
    completeness, brand constraints, and unsupported claims across the
    outputs produced by earlier stages (deliverable_type = qa_report)."""

    task_type = "qa_report"
    stage_name = "quality_reviewer"

    def build_input_data(self, ctx: StageContext) -> dict:
        return {
            "strategy": ctx.upstream_outputs.get("cmo_planner"),
            "research_notes": ctx.upstream_outputs.get("research_analyst"),
            "campaign_plan": ctx.upstream_outputs.get("marketing_manager"),
            "content_pack": ctx.upstream_outputs.get("content_creator"),
            "prohibited_phrases": ctx.business_profile.get("prohibited_phrases"),
        }
