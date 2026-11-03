from app.agents.base import AgentStage, StageContext


class CMOPlannerStage(AgentStage):
    """CMO / Campaign Planner: interprets business goals and produces
    strategic direction (deliverable_type = strategy)."""

    task_type = "strategy"
    stage_name = "cmo_planner"

    def build_input_data(self, ctx: StageContext) -> dict:
        return {
            "objective": ctx.campaign.get("objective"),
            "primary_goal": ctx.business_profile.get("primary_goal"),
            "target_audience": ctx.business_profile.get("target_audience")
            or ctx.campaign.get("audience"),
            "constraints": ctx.campaign.get("constraints"),
        }
