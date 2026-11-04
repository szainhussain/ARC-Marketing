from dataclasses import dataclass, field
from typing import Any, Callable

from app.ai.base import AIProvider, AIResult
from app.ai.schemas import SCHEMAS_BY_TASK_TYPE


@dataclass
class StageContext:
    organization_id: str
    campaign: dict
    business_profile: dict
    # Only outputs of agents listed in the running agent's `reads`
    # allowlist — the engine filters this before the agent sees it.
    upstream_outputs: dict[str, dict]
    budget_usd: float
    timeout_seconds: int
    correlation_id: str
    evaluation_flags: list[dict] = field(default_factory=list)
    # Approved knowledge-library entries (untrusted data, small slice).
    knowledge: list[dict] = field(default_factory=list)


@dataclass(frozen=True)
class AgentSpec:
    """One of the 12 department agents. A spec is versioned: change
    `instructions`, `reads`, the schema, or the input builder and bump
    `version` — every AgentExecution records the version that produced
    its output."""

    agent_id: str
    number: int
    name: str
    version: str
    role: str
    responsibilities: tuple[str, ...]
    task_type: str
    instructions: str
    depends_on: tuple[str, ...]
    reads: tuple[str, ...]
    build_input: Callable[[StageContext], dict[str, Any]]
    outputs: tuple[str, ...]
    kpis: tuple[str, ...]
    escalates: tuple[str, ...]
    allowed_tools: tuple[str, ...] = ("ai.generate_structured",)
    allowed_integrations: tuple[dict, ...] = ()
    max_cost_per_task_usd: float = 0.50
    max_attempts: int = 5
    external_action_policy: str = "require_human_approval"
    evaluation_checks: tuple[str, ...] = ("schema_valid", "prohibited_phrases_absent")
    priority: int = 100

    @property
    def output_schema(self):
        return SCHEMAS_BY_TASK_TYPE[self.task_type]

    def run(self, provider: AIProvider, ctx: StageContext) -> AIResult:
        return provider.generate_structured(
            task_type=self.task_type,
            input_data=self.build_input(ctx),
            output_schema=self.output_schema,
            context={
                "agent_role": f"Agent {self.number:02d}, {self.name}. {self.instructions}",
                "campaign": ctx.campaign,
                "business_profile": ctx.business_profile,
            },
            budget_usd=min(ctx.budget_usd, self.max_cost_per_task_usd),
            timeout_seconds=ctx.timeout_seconds,
            correlation_id=ctx.correlation_id,
        )

    def to_public_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "number": self.number,
            "name": self.name,
            "version": self.version,
            "role": self.role,
            "responsibilities": list(self.responsibilities),
            "task_type": self.task_type,
            "depends_on": list(self.depends_on),
            "reads": list(self.reads),
            "outputs": list(self.outputs),
            "kpis": list(self.kpis),
            "escalates": list(self.escalates),
            "allowed_tools": list(self.allowed_tools),
            "allowed_integrations": [dict(i) for i in self.allowed_integrations],
            "budget_policy": {
                "max_cost_per_task_usd": self.max_cost_per_task_usd,
                "max_attempts": self.max_attempts,
            },
            "approval_policy": {"external_actions": self.external_action_policy},
            "evaluation_checks": list(self.evaluation_checks),
        }
