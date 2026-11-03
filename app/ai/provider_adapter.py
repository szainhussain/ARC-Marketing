import json
import time
from typing import Any

from marshmallow import ValidationError as SchemaValidationError

from app.ai.base import AIProvider, AIResult
from app.ai.errors import (
    AIRequestTimeout,
    BudgetExceeded,
    InvalidOutput,
    ProviderUnavailable,
    RateLimited,
)

# Rough, clearly-labelled placeholder price used only to produce an
# *estimate* shown to users as an estimate; it is not an invoice amount.
_PLACEHOLDER_USD_PER_1K_INPUT_TOKENS = 0.003
_PLACEHOLDER_USD_PER_1K_OUTPUT_TOKENS = 0.015


class NullProvider(AIProvider):
    """Used when no provider is configured. Always raises
    ProviderUnavailable so callers take the documented
    capability_unavailable path instead of fabricating output."""

    name = "none"

    def generate_structured(self, *args, **kwargs) -> AIResult:
        raise ProviderUnavailable(
            "No AI provider is configured. Set ANTHROPIC_API_KEY to enable "
            "AI-generated workflow stages."
        )


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def _client(self):
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - exercised only without the package
            raise ProviderUnavailable(
                "The 'anthropic' package is not installed in this environment."
            ) from exc
        return anthropic.Anthropic(api_key=self.api_key)

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
        if not self.api_key:
            raise ProviderUnavailable("ANTHROPIC_API_KEY is not set.")

        client = self._client()
        schema = output_schema()
        prompt = self._build_prompt(task_type, input_data, context, schema)

        last_error_text = None
        for attempt in range(1, 3):  # bounded: 1 initial + 1 repair attempt
            try:
                response = client.messages.create(
                    model=self.model,
                    max_tokens=2000,
                    timeout=timeout_seconds,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt if attempt == 1 else self._repair_prompt(
                                prompt, last_error_text
                            ),
                        }
                    ],
                )
            except Exception as exc:  # noqa: BLE001 - map every SDK failure to a typed error
                text = str(exc).lower()
                if "rate" in text or "429" in text:
                    raise RateLimited(str(exc)) from exc
                if "timeout" in text:
                    raise AIRequestTimeout(str(exc)) from exc
                raise ProviderUnavailable(str(exc)) from exc

            raw_text = "".join(
                block.text for block in response.content if getattr(block, "type", "") == "text"
            )
            input_tokens = getattr(response.usage, "input_tokens", 0) or 0
            output_tokens = getattr(response.usage, "output_tokens", 0) or 0
            estimated_cost = (
                input_tokens / 1000 * _PLACEHOLDER_USD_PER_1K_INPUT_TOKENS
                + output_tokens / 1000 * _PLACEHOLDER_USD_PER_1K_OUTPUT_TOKENS
            )
            if estimated_cost > budget_usd:
                raise BudgetExceeded(
                    f"Estimated cost ${estimated_cost:.4f} exceeds budget ${budget_usd:.4f}."
                )

            try:
                parsed = json.loads(raw_text)
                validated = schema.load(parsed)
            except (json.JSONDecodeError, SchemaValidationError) as exc:
                last_error_text = str(exc)
                continue

            return AIResult(
                data=validated,
                provider=self.name,
                model=self.model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                estimated_cost_usd=round(estimated_cost, 6),
            )

        raise InvalidOutput(
            f"Model output did not match the required schema after retries: {last_error_text}"
        )

    @staticmethod
    def _build_prompt(task_type: str, input_data: dict, context: dict | None, schema) -> str:
        field_names = list(schema.fields.keys())
        return (
            f"You are the '{task_type}' stage of a marketing campaign workflow. "
            f"Respond with ONLY a single JSON object with exactly these top-level "
            f"keys: {field_names}. Do not include markdown fences or commentary. "
            f"Clearly distinguish facts the user provided from assumptions you add "
            f"(list assumptions explicitly where the schema has an 'assumptions' field). "
            f"Input data: {json.dumps(input_data, default=str)}. "
            f"Business/campaign context: {json.dumps(context or {}, default=str)}."
        )

    @staticmethod
    def _repair_prompt(original_prompt: str, error_text: str | None) -> str:
        return (
            f"{original_prompt}\n\nYour previous response was invalid JSON or did not "
            f"match the required schema ({error_text}). Respond again with ONLY the "
            f"corrected JSON object."
        )


def get_provider(app_config) -> AIProvider:
    provider_name = (app_config.get("AI_PROVIDER") or "").lower()
    api_key = app_config.get("ANTHROPIC_API_KEY") or ""
    if provider_name == "anthropic" and api_key:
        return AnthropicProvider(api_key=api_key, model=app_config.get("AI_MODEL"))
    return NullProvider()
