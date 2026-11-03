from app.agents.base import AgentStage, StageContext


class MarketingManagerStage(AgentStage):
    """Marketing Manager: converts strategy + research into a structured,
    actionable campaign plan (deliverable_type = campaign_plan)."""

    task_type = "campaign_plan"
    stage_name = "marketing_manager"

    def build_input_data(self, ctx: StageContext) -> dict:
        return {
            "strategy": ctx.upstream_outputs.get("cmo_planner"),
            "research_notes": ctx.upstream_outputs.get("research_analyst"),
            "channels": ctx.campaign.get("channels"),
            "start_date": ctx.campaign.get("start_date"),
            "end_date": ctx.campaign.get("end_date"),
            "success_metrics": ctx.campaign.get("success_metrics"),
        }
