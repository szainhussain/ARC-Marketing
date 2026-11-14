"""The Growth Score: six dimensions, each scored only from evidence ARC
actually holds (docs/DECISIONS.md D22).

A dimension with no evidence is "not measured", never estimated, and the
overall score says how many dimensions it rests on. Each scale is ARC's own
and is spelled out in `how_scored`; none is an industry benchmark.
"""

from datetime import date, timedelta

from app.models.results import CampaignResult
from app.services.business_profile_service import get_or_create_profile
from app.services.unit_economics import economics

WINDOW_DAYS = 90
_BRAND_FIELDS = (
    ("target_audience", "Target audience"), ("customer_problem", "Customer problem"),
    ("differentiators", "What makes you different"), ("tone_of_voice", "Tone of voice"),
    ("brand_persona", "Brand persona"), ("prohibited_phrases", "Claims and phrases to avoid"),
    ("competitors", "Competitors"), ("brand_colors", "Brand colours"),
)


def _clamp(v: float) -> int:
    return int(max(0, min(100, round(v))))


def _dim(key, label, score, basis, evidence, how_scored, next_step=None) -> dict:
    return {"key": key, "label": label, "score": score, "measured": score is not None, "basis": basis,
            "evidence": evidence, "how_scored": how_scored, "next_step": next_step}


def _totals(rows) -> dict:
    out = {}
    for f in ("spend", "clicks", "leads", "conversions", "revenue"):
        vals = [getattr(r, f) for r in rows if getattr(r, f) is not None]
        out[f] = sum(vals) if vals else None
    return out


def growth_score(organization_id: str, today: date | None = None) -> dict:
    today = today or date.today()
    start, prev_start = today - timedelta(days=WINDOW_DAYS), today - timedelta(days=WINDOW_DAYS * 2)
    profile = get_or_create_profile(organization_id)
    base = CampaignResult.query.filter_by(organization_id=organization_id)
    now_rows = base.filter(CampaignResult.period_end >= start).all()
    prev_rows = base.filter(CampaignResult.period_end >= prev_start, CampaignResult.period_end < start).all()
    now, prev = _totals(now_rows), _totals(prev_rows)
    econ = economics(now, profile.gross_margin_pct, profile.orders_per_customer)
    results_link = "Record results under Results."

    filled = [label for field, label in _BRAND_FIELDS if getattr(profile, field)]
    missing = [label for field, label in _BRAND_FIELDS if not getattr(profile, field)]
    dims = [_dim(
        "brand_readiness", "Brand readiness", _clamp(len(filled) / len(_BRAND_FIELDS) * 100), "business profile",
        [f"{len(filled)} of {len(_BRAND_FIELDS)} brand foundations are written down."]
        + ([f"Missing: {', '.join(missing)}."] if missing else []),
        "Share of the eight brand foundations in your business profile that are filled in. "
        "It measures whether they are written down, not how good they are.",
        "Complete the missing items in your business profile." if missing else None)]

    clicks, customers = now.get("clicks"), now.get("conversions")
    if clicks and customers is not None:
        rate = customers / clicks * 100
        dims.append(_dim("website_conversion", "Website conversion", _clamp(rate / 5 * 100), "recorded results",
                         [f"{customers:g} customers from {clicks:g} clicks in the last {WINDOW_DAYS} days ({rate:.1f}%)."],
                         "Customers divided by clicks. 5% or more scores 100; the scale is linear below that."))
    else:
        dims.append(_dim("website_conversion", "Website conversion", None, "not measured", [],
                         "Customers divided by clicks.", "Record clicks and customers for at least one channel. " + results_link))

    leads, prev_leads = now.get("leads"), prev.get("leads")
    if leads:
        evidence = [f"{leads:g} leads in the last {WINDOW_DAYS} days."]
        if econ["cost_per_lead"] is not None:
            evidence.append(f"Cost per lead: {econ['cost_per_lead']:,.2f}.")
        if prev_leads:
            change = (leads - prev_leads) / prev_leads * 100
            evidence.append(f"{change:+.0f}% against the {WINDOW_DAYS} days before ({prev_leads:g} leads).")
            score = _clamp(50 + change / 2)
        else:
            score = 50
            evidence.append("No earlier period to compare with yet, so the score starts at 50.")
        dims.append(_dim("lead_generation", "Lead generation", score, "recorded results", evidence,
                         "Starts at 50 and moves with the change in leads against the previous 90 days "
                         "(+100% scores 100, -100% scores 0)."))
    else:
        dims.append(_dim("lead_generation", "Lead generation", None, "not measured", [],
                         "Change in leads against the previous 90 days.", "Record leads per channel. " + results_link))

    if econ["verdict"] != "unknown":
        dims.append(_dim("campaign_performance", "Campaign performance",
                         _clamp(econ["roas"] / econ["break_even_roas"] * 50), "recorded results and your margin",
                         [econ["explanation"]],
                         "ROAS against your break-even ROAS. Break-even scores 50; twice break-even scores 100."))
    else:
        dims.append(_dim("campaign_performance", "Campaign performance", None, "not measured", [],
                         "ROAS against your break-even ROAS.",
                         f"Still needed: {', '.join(econ['missing']) or 'ad spend and revenue'}."))

    dims.append(_dim("customer_retention", "Customer retention", None, "not measured",
                     ([f"You told us customers order about {profile.orders_per_customer:g} times; ARC has not measured it."]
                      if profile.orders_per_customer else []),
                     "Repeat purchase rate from order data.",
                     "Needs order or CRM data. No store or CRM connection exists in ARC yet."))
    dims.append(_dim("customer_advocacy", "Customer advocacy", None, "not measured", [],
                     "Review volume, rating and referrals.",
                     "Needs review or referral data. No review-platform connection exists in ARC yet."))

    scored = [d["score"] for d in dims if d["measured"]]
    return {
        "overall": round(sum(scored) / len(scored)) if scored else None,
        "measured_dimensions": len(scored),
        "total_dimensions": len(dims),
        "window_days": WINDOW_DAYS,
        "dimensions": dims,
        "economics": econ,
        "note": f"Based on {len(scored)} of {len(dims)} dimensions. Scores come from your business profile and the "
                "results recorded in ARC, on ARC's own scales. They are not industry benchmarks.",
    }
