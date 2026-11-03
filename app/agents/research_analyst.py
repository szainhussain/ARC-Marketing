from app.agents.base import AgentStage, StageContext


class ResearchAnalystStage(AgentStage):
    """Market Intelligence Analyst: synthesizes available user-provided
    information. No live web-search provider is configured in this
    milestone, so this stage must label its scope_note accordingly rather
    than fabricate external research or citations."""

    task_type = "research_notes"
    stage_name = "research_analyst"

    def build_input_data(self, ctx: StageContext) -> dict:
        return {
            "industry": ctx.business_profile.get("industry"),
            "differentiators": ctx.business_profile.get("differentiators"),
            "customer_problem": ctx.business_profile.get("customer_problem"),
            "geography": ctx.campaign.get("geography"),
            "note_to_model": (
                "No external research/web-search tool is connected. Base your "
                "notes only on the supplied business facts and clearly set "
                "scope_note to say research is based on user-provided context only."
            ),
        }
