"""Deterministic fixture provider for automated end-to-end tests (brief §21).

Selected only with AI_PROVIDER=fixture AND ALLOW_FIXTURE_PROVIDER=true, and
refused under ProductionConfig (see get_provider). Every output is marked
"[E2E fixture]" so it can never be mistaken for real generated work. This
is not a fallback: with no real provider configured, the app still takes
the capability_unavailable path (CLAUDE.md rule 5).
"""

from app.ai.base import AIProvider, AIResult

MARK = "[E2E fixture]"

FIXTURE_OUTPUTS = {
    "strategy": {
        "strategic_direction": f"{MARK} Position as the go-to weekend hiking brand.",
        "key_objectives": ["Increase awareness", "Drive trial purchases"],
        "assumptions": ["Audience is price-sensitive"],
    },
    "research_notes": {
        "audience_hypotheses": ["Weekend hikers value durability"],
        "scope_note": f"{MARK} Based on user-provided context only.",
    },
    "campaign_plan": {
        "summary": f"{MARK} A four-week trail launch campaign.",
        "channels": ["email", "social"],
        "timeline": [{"phase": "Teaser week", "activities": ["Post countdown content"]}],
        "success_metrics": ["signups"],
    },
    "content_pack": {
        "creative_brief": f"{MARK} Highlight durability and comfort on long trails.",
        "variants": [{"channel": "instagram", "headline": "Hit the trail", "body": "Built for the long weekend."}],
    },
    "social_calendar": {
        "channels": ["instagram"],
        "calendar_entries": [
            {"day": "Day 1", "channel": "instagram", "caption": f"{MARK} Trail ready.", "hashtags": ["#hiking"]},
            {"day": "Day 2", "channel": "instagram", "caption": f"{MARK} Pack light, go far.", "hashtags": ["#trail"]},
        ],
    },
    "outreach_plan": {
        "target_profiles": [{"target_type": "creator", "fit_criteria": "Hiking niche", "why_relevant": "Audience overlap"}],
        "outreach_drafts": [{"target_type": "creator", "channel": "email", "message": f"{MARK} Hello"}],
    },
    "paid_media_plan": {
        "campaign_structure": [{"name": "Search - brand", "channel": "google_ads", "objective": "traffic", "audience": "hikers"}],
        "budget_allocation_recommendation": [{"channel": "google_ads", "share_percent": 100, "rationale": "Intent capture"}],
    },
    "site_optimization_plan": {
        "keyword_themes": [{"theme": "hiking backpacks", "search_intent": "commercial", "priority": "high"}],
        "blog_articles": [{"title": f"{MARK} How to choose a hiking backpack", "target_keyword": "hiking backpacks",
                           "excerpt": "A short guide to fit, volume and weight.",
                           "body_markdown": ("## Start with fit\n\nMeasure your torso first, then choose a pack "
                                             "that matches it.\n\n- Volume\n- Weight"),
                           "tags": ["hiking", "guides"]}],
    },
    "customer_insights": {
        "data_note": f"{MARK} No customer data connected; hypotheses only.",
        "themes": [{"theme": "Fit", "evidence_basis": "inferred from business profile", "implication": "Size guide"}],
    },
    "account_plan": {
        "account_segments": [{"segment": "Outdoor retailers", "opportunity": "Stockists", "priority": "medium"}],
    },
    "qa_report": {"passed": True, "issues": [], "checked": ["schema", "brand constraints"]},
    "campaign_record": {
        "summary": f"{MARK} Launch plan recorded.",
        "action_items": [{"item": "Approve plan", "owner_agent": "human"}],
        "knowledge_updates": [f"{MARK} Weekend hikers respond to durability claims"],
    },
}


class FixtureProvider(AIProvider):
    name = "fixture"

    def generate_structured(self, task_type, input_data, output_schema, context=None,
                            budget_usd=1.0, timeout_seconds=60, correlation_id=None):
        data = output_schema().load(FIXTURE_OUTPUTS[task_type])
        return AIResult(data=data, provider="fixture", model="e2e-fixture", input_tokens=10,
                        output_tokens=20, estimated_cost_usd=0.0)
