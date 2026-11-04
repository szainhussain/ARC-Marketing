"""Fake AI provider + schema-valid canned outputs for all 12 agents, so
engine tests never call a real model (see CLAUDE.md testing conventions)."""

from app.ai.base import AIProvider, AIResult

FAKE_OUTPUTS = {
    "strategy": {
        "strategic_direction": "Position as the go-to weekend hiking brand.",
        "key_objectives": ["Increase awareness", "Drive trial purchases"],
        "assumptions": ["Audience is price-sensitive"],
    },
    "research_notes": {
        "audience_hypotheses": ["Weekend hikers value durability"],
        "scope_note": "Based on user-provided context only.",
    },
    "campaign_plan": {
        "summary": "A four-week trail launch campaign.",
        "channels": ["email", "social"],
        "timeline": [{"phase": "Teaser week", "activities": ["Post countdown content"]}],
        "success_metrics": ["signups"],
    },
    "content_pack": {
        "creative_brief": "Highlight durability and comfort on long trails.",
        "variants": [{"channel": "email", "headline": "Hit the trail", "body": "Body copy"}],
    },
    "social_calendar": {
        "channels": ["instagram"],
        "calendar_entries": [{"day": "Mon", "channel": "instagram", "caption": "Trail ready."}],
    },
    "outreach_plan": {
        "target_profiles": [
            {"target_type": "creator", "fit_criteria": "Hiking niche", "why_relevant": "Audience overlap"}
        ],
        "outreach_drafts": [{"target_type": "creator", "channel": "email", "message": "Hello"}],
    },
    "paid_media_plan": {
        "campaign_structure": [
            {"name": "Search - brand", "channel": "google_ads", "objective": "traffic", "audience": "hikers"}
        ],
        "budget_allocation_recommendation": [
            {"channel": "google_ads", "share_percent": 100, "rationale": "Intent capture"}
        ],
    },
    "site_optimization_plan": {
        "keyword_themes": [{"theme": "hiking backpacks", "search_intent": "commercial", "priority": "high"}],
    },
    "customer_insights": {
        "data_note": "No customer data connected; hypotheses only.",
        "themes": [{"theme": "Fit", "evidence_basis": "inferred from business profile", "implication": "Size guide"}],
    },
    "account_plan": {
        "account_segments": [{"segment": "Outdoor retailers", "opportunity": "Stockists", "priority": "medium"}],
    },
    "qa_report": {"passed": True, "issues": [], "checked": ["schema", "brand constraints"]},
    "campaign_record": {
        "summary": "Launch plan recorded.",
        "action_items": [{"item": "Approve plan", "owner_agent": "human"}],
    },
}


class FakeProvider(AIProvider):
    """Returns canned outputs. `fail_for` maps task_type -> list of
    exceptions to raise on successive calls before succeeding."""

    name = "fake"

    def __init__(self, fail_for: dict | None = None, overrides: dict | None = None):
        self.fail_for = {k: list(v) for k, v in (fail_for or {}).items()}
        self.overrides = overrides or {}
        self.calls: list[dict] = []

    def generate_structured(self, task_type, input_data, output_schema, context=None,
                            budget_usd=1.0, timeout_seconds=60, correlation_id=None):
        self.calls.append({"task_type": task_type, "input_data": input_data, "context": context})
        pending = self.fail_for.get(task_type)
        if pending:
            raise pending.pop(0)
        data = self.overrides.get(task_type, FAKE_OUTPUTS[task_type])
        validated = output_schema().load(data)
        return AIResult(data=validated, provider="fake", model="fake-model",
                        input_tokens=10, output_tokens=20, estimated_cost_usd=0.001)


def use_provider(monkeypatch, provider):
    monkeypatch.setattr("app.workflows.engine.get_provider", lambda config: provider)
    return provider
