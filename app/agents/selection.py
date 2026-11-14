"""Which agents a campaign run actually needs (docs/DECISIONS.md D21).

Six agents carry every run: strategy, research, plan, creative, the quality
gate and the record. The other six are channel specialists and only run
when the campaign's channels call for them, so a local business posting on
Instagram does not pay for a key-accounts plan it will never open.

A campaign with no channels, or channels we do not recognise, gets the
whole department: guessing wrong by skipping work is worse than spending a
few more calls.
"""

import re

CORE_AGENTS = ("cmo", "research_analyst", "marketing_manager", "creative_studio", "marketing_ops", "record_keeper")

# Channel words (lower case, matched on word boundaries) that call for each specialist.
CHANNEL_SPECIALISTS: dict[str, tuple[str, ...]] = {
    "social_media": ("instagram", "facebook", "tiktok", "linkedin", "snapchat", "youtube", "twitter", "x",
                     "social", "whatsapp", "threads", "pinterest", "google business profile"),
    "paid_media": ("ads", "ad", "paid", "ppc", "sem", "adwords", "sponsored", "boosted"),
    "seo_growth": ("seo", "website", "web", "blog", "search", "landing page", "landing pages", "e-commerce",
                   "ecommerce", "shopify", "woocommerce", "wordpress", "google business profile", "store"),
    "pr_partnerships": ("pr", "press", "media", "influencer", "influencers", "partnership", "partnerships",
                        "partners", "event", "events", "webinar", "outreach", "email", "newsletter"),
    "customer_insights": ("reviews", "review", "reputation", "support", "customer service", "whatsapp",
                          "community", "messages", "dms"),
    "key_accounts": ("b2b", "sales", "accounts", "key accounts", "distributors", "distributor", "wholesale",
                     "retailers", "resellers", "channel partners", "linkedin", "tenders"),
}


def _mentions(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


def agents_for_channels(channels: str | None) -> frozenset[str]:
    """Agent ids to run for a campaign's free-text `channels` value."""

    text = (channels or "").lower()
    everything = frozenset(CORE_AGENTS) | frozenset(CHANNEL_SPECIALISTS)
    if not text.strip():
        return everything
    chosen = {agent for agent, words in CHANNEL_SPECIALISTS.items() if any(_mentions(text, w) for w in words)}
    if not chosen:
        return everything
    return frozenset(CORE_AGENTS) | chosen
