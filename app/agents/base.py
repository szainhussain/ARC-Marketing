from dataclasses import dataclass
from typing import Any

from app.ai.base import AIProvider, AIResult
from app.ai.schemas import SCHEMAS_BY_TASK_TYPE


@dataclass
class StageContext:
    organization_id: str
    campaign: dict
    business_profile: dict
    upstream_outputs: dict[str, dict]
    budget_usd: float
    timeout_seconds: int
    correlation_id: str


class AgentStage:
    """One logical capability from the PRD (CMO/planner, research analyst,
    marketing manager, content creator, quality reviewer). Each stage is a
    plain Python class/function today, not a separate autonomous process —
    matching the spec's explicit instruction not to over-engineer the MVP.
    """

    task_type: str = ""
    stage_name: str = ""

    def build_input_data(self, ctx: StageContext) -> dict[str, Any]:
        raise NotImplementedError

    def run(self, provider: AIProvider, ctx: StageContext) -> AIResult:
        schema = SCHEMAS_BY_TASK_TYPE[self.task_type]
        input_data = self.build_input_data(ctx)
        return provider.generate_structured(
            task_type=self.task_type,
            input_data=input_data,
            output_schema=schema,
            context={
                "campaign": ctx.campaign,
                "business_profile": ctx.business_profile,
                "upstream_outputs": ctx.upstream_outputs,
            },
            budget_usd=ctx.budget_usd,
            timeout_seconds=ctx.timeout_seconds,
            correlation_id=ctx.correlation_id,
        )
