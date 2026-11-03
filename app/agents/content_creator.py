from app.agents.base import AgentStage, StageContext


class ContentCreatorStage(AgentStage):
    """Creative & Content Specialist: campaign copy, channel variants, and
    a creative brief (deliverable_type = content_pack)."""

    task_type = "content_pack"
    stage_name = "content_creator"

    def build_input_data(self, ctx: StageContext) -> dict:
        return {
            "campaign_plan": ctx.upstream_outputs.get("marketing_manager"),
            "tone_of_voice": ctx.business_profile.get("tone_of_voice"),
            "preferred_phrases": ctx.business_profile.get("preferred_phrases"),
            "prohibited_phrases": ctx.business_profile.get("prohibited_phrases"),
            "channels": ctx.campaign.get("channels"),
        }
