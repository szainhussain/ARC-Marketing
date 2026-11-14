"""The department as customers see it: one orchestrator, six teams and a
set of on-demand skills (docs/DECISIONS.md D22).

The twelve AgentSpecs stay separate, small model calls, because small tasks
with narrow inputs are cheaper and fail less than one large call. This file
only groups them and says which are called on demand.
"""

TEAMS = (
    {"key": "orchestrator", "name": "Growth Orchestrator",
     "responsibility": "Understands the goal, sets the strategy and priorities, and decides which work is needed."},
    {"key": "strategy_intelligence", "name": "Strategy & Intelligence",
     "responsibility": "Market, competitor and audience research with facts kept apart from assumptions."},
    {"key": "campaign_content", "name": "Campaign & Content",
     "responsibility": "The dated campaign plan, copy, creative briefs and social content."},
    {"key": "performance_acquisition", "name": "Performance & Acquisition",
     "responsibility": "Paid media structure and budget recommendations sized to your margins."},
    {"key": "website_conversion", "name": "Website & Conversion",
     "responsibility": "Search themes, page improvements, conversion ideas and blog articles."},
    {"key": "customer_lifecycle", "name": "Customer Lifecycle",
     "responsibility": "Customer themes, objections and reply templates for reviews and messages."},
    {"key": "analytics_governance", "name": "Analytics & Governance",
     "responsibility": "The quality gate, brand and claim checks, and the campaign record."},
    {"key": "skills", "name": "On-demand skills",
     "responsibility": "PR, influencer, partnership and sales-enablement work, called only when a campaign needs it."},
)

AGENT_TEAM = {
    "cmo": "orchestrator",
    "research_analyst": "strategy_intelligence",
    "marketing_manager": "campaign_content",
    "creative_studio": "campaign_content",
    "social_media": "campaign_content",
    "paid_media": "performance_acquisition",
    "seo_growth": "website_conversion",
    "customer_insights": "customer_lifecycle",
    "marketing_ops": "analytics_governance",
    "record_keeper": "analytics_governance",
    "pr_partnerships": "skills",
    "key_accounts": "skills",
}

TEAMS_BY_KEY = {t["key"]: t for t in TEAMS}


def team_for(agent_id: str) -> dict:
    return TEAMS_BY_KEY[AGENT_TEAM[agent_id]]
