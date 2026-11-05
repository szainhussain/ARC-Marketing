"""The integration catalog with honest statuses (brief §8.I, §14).

Status meanings:
- available_tested: implemented and covered by tests in this repo.
- architecture_supported: the connector contract exists, but no live
  connector is built for this provider.
- planned: on the roadmap; nothing built yet.

Nothing here is a claim of partnership with any provider.
"""

AVAILABLE = "available_tested"
SUPPORTED = "architecture_supported"
PLANNED = "planned"

CATALOG = [
    {"key": "manual_export:meta_instagram", "name": "Meta / Instagram — manual export", "category": "Social & publishing",
     "status": AVAILABLE, "agents": ["social_media", "creative_studio"],
     "detail": "Formats approved content to composer limits for copy-paste. Never posts.",
     "prerequisite": None},
    {"key": "manual_export:google_ads", "name": "Google Ads — manual export", "category": "Paid media",
     "status": AVAILABLE, "agents": ["paid_media"],
     "detail": "Responsive Search Ad field limits checked against Google's published limits. Never spends.",
     "prerequisite": None},
    {"key": "manual_export:tiktok_ads", "name": "TikTok Ads — manual export", "category": "Paid media",
     "status": AVAILABLE, "agents": ["paid_media", "social_media"],
     "detail": "Formats ad text for manual entry. Never posts or spends.", "prerequisite": None},
    {"key": "wordpress_com", "name": "WordPress.com — publish blog articles", "category": "Social & publishing",
     "status": AVAILABLE, "agents": ["seo_growth"],
     "detail": "Publishes an approved blog article to your WordPress.com site (or saves it as a draft), "
               "then reads it back from WordPress to confirm it is live. Nothing is posted before approval.",
     "prerequisite": "A WordPress.com site you can publish to. Connect it under Integrations."},
    {"key": "outreach:email", "name": "Outreach email — Brevo or Resend", "category": "Outreach",
     "status": AVAILABLE, "agents": ["pr_partnerships", "key_accounts"],
     "detail": "Sends an approved email to a contact list you uploaded, from your own Brevo or Resend account, "
               "with a daily limit, one-click unsubscribe and a suppression list. Nothing is sent before approval.",
     "prerequisite": "A Brevo or Resend account with a verified sender, and a contact list you're allowed to email."},
    {"key": "ads:launch", "name": "Ad launching with a daily cap", "category": "Paid media",
     "status": AVAILABLE, "agents": ["paid_media"],
     "detail": "Launch an ad from an approved paid media plan after a typed-budget approval. ARC pauses every ad "
               "if you hit your daily cap or turn on the kill switch. Runs on ARC's test platform (no real money) "
               "until Meta or Google Ads API access is connected.",
     "prerequisite": "A daily spend cap set by an owner or admin. Real spend needs Meta Marketing API or Google Ads API access."},
    {"key": "automation:zapier", "name": "Zapier — publish approved content", "category": "Automation",
     "status": AVAILABLE, "agents": ["social_media", "creative_studio", "paid_media"],
     "detail": "Approved content is sent to your Zap via a signed webhook (content.approved_for_publishing); "
               "your Zap posts it to any of thousands of apps. Nothing is sent before approval.",
     "prerequisite": "A Zapier account and a Zap that starts with 'Webhooks by Zapier — Catch Hook'."},
    {"key": "automation:make", "name": "Make — publish approved content", "category": "Automation",
     "status": AVAILABLE, "agents": ["social_media", "creative_studio", "paid_media"],
     "detail": "Approved content is sent to your Make scenario via a signed webhook "
               "(content.approved_for_publishing). Nothing is sent before approval.",
     "prerequisite": "A Make account and a scenario that starts with a 'Custom webhook' trigger."},
    {"key": "meta_graph", "name": "Meta Graph API (publishing)", "category": "Social & publishing",
     "status": SUPPORTED, "agents": ["social_media"],
     "detail": "Connector contract exists; live publishing is not built.",
     "prerequisite": "Meta app review, business verification, customer OAuth consent."},
    {"key": "linkedin", "name": "LinkedIn", "category": "Social & publishing", "status": PLANNED,
     "agents": ["social_media", "key_accounts"], "detail": "Not built.",
     "prerequisite": "LinkedIn Marketing Developer Platform access."},
    {"key": "youtube", "name": "YouTube Data API", "category": "Social & publishing", "status": PLANNED,
     "agents": ["social_media", "creative_studio"], "detail": "Not built.", "prerequisite": "Google OAuth app verification."},
    {"key": "google_ads_api", "name": "Google Ads API (live)", "category": "Paid media", "status": PLANNED,
     "agents": ["paid_media"], "detail": "Not built. Spend changes would stay human-only.",
     "prerequisite": "Google Ads developer token (basic access) and customer OAuth."},
    {"key": "ga4", "name": "Google Analytics 4", "category": "Analytics", "status": PLANNED,
     "agents": ["seo_growth", "marketing_ops"], "detail": "Not built; dashboards show 'Not connected' for traffic and conversions.",
     "prerequisite": "GA4 Data API access via customer OAuth."},
    {"key": "cms", "name": "CMS / e-commerce (e.g. Shopify, WordPress)", "category": "Website & commerce",
     "status": PLANNED, "agents": ["seo_growth"], "detail": "Not built.", "prerequisite": "Per-platform API credentials."},
    {"key": "crm", "name": "CRM (e.g. HubSpot, Salesforce)", "category": "Customer relationships",
     "status": PLANNED, "agents": ["key_accounts"], "detail": "Not built.", "prerequisite": "Per-platform OAuth app."},
    {"key": "helpdesk", "name": "Helpdesk & reviews", "category": "Customer relationships", "status": PLANNED,
     "agents": ["customer_insights"], "detail": "Not built; the Customer Insights agent labels everything a hypothesis.",
     "prerequisite": "Per-platform API credentials."},
    {"key": "email_delivery", "name": "Transactional email (e.g. Resend)", "category": "Internal infrastructure",
     "status": PLANNED, "agents": [],
     "detail": "Needed for invitation and password-reset emails. Until configured, links are shown to admins / logged server-side.",
     "prerequisite": "Email provider API key and verified sending domain."},
    {"key": "image_generation", "name": "Image / video generation (e.g. Higgsfield)", "category": "Creative production",
     "status": PLANNED, "agents": ["creative_studio"],
     "detail": "Not built. The Creative agent produces briefs, never claims to have generated media.",
     "prerequisite": "Provider API key and licensing review."},
    {"key": "web_research", "name": "Web research / search API", "category": "Research", "status": PLANNED,
     "agents": ["research_analyst"], "detail": "Not built; research is limited to supplied business facts.",
     "prerequisite": "Search API key; robots/terms compliance review."},
]

CATALOG_BY_KEY = {c["key"]: c for c in CATALOG}
