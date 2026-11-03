from dataclasses import dataclass, field
from typing import Any


@dataclass
class AIResult:
    data: dict
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    warnings: list[str] = field(default_factory=list)


class AIProvider:
    """Provider-neutral contract. A concrete provider (Anthropic, OpenAI,
    ...) implements this; domain/workflow code never imports a specific
    SDK directly, so the provider can be swapped without touching
    campaign/governance logic.
    """

    name = "base"

    def generate_structured(
        self,
        task_type: str,
        input_data: dict[str, Any],
        output_schema,
        context: dict[str, Any] | None = None,
        budget_usd: float = 1.0,
        timeout_seconds: int = 60,
        correlation_id: str | None = None,
    ) -> AIResult:
        raise NotImplementedError
