"""Profit maths for marketing results. Plain arithmetic, never a model call
(docs/DECISIONS.md D22): a 4x ROAS on a 20% margin loses money, and a
customer should be told that by a calculation, not an opinion.

"Contribution" here means revenue x gross margin, minus ad spend. It is
before salaries, rent and other fixed costs, and every output says so.
"""


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # NaN guard


def _div(a, b):
    return a / b if a is not None and b not in (None, 0) else None


def _r(v, places=2):
    return round(v, places) if v is not None else None


def economics(totals: dict, gross_margin_pct=None, orders_per_customer=None) -> dict:
    """`totals` uses the CampaignResult metric names: spend, revenue, leads,
    conversions (new customers or sales). Anything that cannot be worked out
    from what was supplied comes back as None, never as a guess."""

    spend, revenue = _num(totals.get("spend")), _num(totals.get("revenue"))
    customers, leads = _num(totals.get("conversions")), _num(totals.get("leads"))
    margin_pct = _num(gross_margin_pct)
    margin = margin_pct / 100 if margin_pct and 0 < margin_pct <= 100 else None
    lifetime_orders = _num(orders_per_customer)

    roas = _div(revenue, spend)
    break_even_roas = _div(1, margin)
    contribution = revenue * margin - (spend or 0) if revenue is not None and margin else None
    cac = _div(spend, customers)
    aov = _div(revenue, customers)
    contribution_per_order = aov * margin if aov is not None and margin else None
    payback_orders = _div(cac, contribution_per_order)
    ltv = contribution_per_order * lifetime_orders if contribution_per_order is not None and lifetime_orders else None

    if roas is None or break_even_roas is None:
        verdict = "unknown"
    elif roas >= break_even_roas * 1.05:
        verdict = "profitable"
    elif roas <= break_even_roas * 0.95:
        verdict = "losing"
    else:
        verdict = "break_even"

    return {
        "roas": _r(roas),
        "marketing_efficiency_ratio": _r(roas),  # blended: all recorded revenue / all recorded spend
        "gross_margin_pct": margin_pct if margin else None,
        "break_even_roas": _r(break_even_roas),
        "contribution_profit": _r(contribution),
        "cost_per_lead": _r(_div(spend, leads)),
        "customer_acquisition_cost": _r(cac),
        "average_order_value": _r(aov),
        "contribution_per_order": _r(contribution_per_order),
        "payback_orders": _r(payback_orders, 1),
        "customer_lifetime_value": _r(ltv),
        "ltv_to_cac": _r(_div(ltv, cac), 1),
        "lead_to_customer_pct": _r(_div(customers, leads) * 100 if _div(customers, leads) is not None else None, 1),
        "verdict": verdict,
        "explanation": _explain(verdict, roas, break_even_roas, contribution, margin_pct if margin else None),
        "missing": [name for name, v in (("gross margin", margin), ("ad spend", spend), ("revenue", revenue),
                                         ("new customers", customers)) if v is None],
        "basis": "Contribution = revenue x gross margin - ad spend. Before fixed costs. "
                 "Gross margin and repeat orders are the figures you entered in your business profile.",
    }


def _explain(verdict, roas, break_even, contribution, margin_pct) -> str:
    if margin_pct is None:
        return "Add your gross margin in the business profile to see whether this spend made or lost money."
    if roas is None:
        return "Record both ad spend and revenue to see whether this spend made or lost money."
    head = f"ROAS is {roas:.2f}x. At a {margin_pct:g}% margin you need {break_even:.2f}x to break even"
    if verdict == "profitable":
        return f"{head}, so this made about ${contribution:,.0f} after ad spend."
    if verdict == "losing":
        return f"{head}, so this lost about ${abs(contribution):,.0f} after ad spend."
    return f"{head}, so this roughly broke even."


def targets(gross_margin_pct=None, average_order_value=None, orders_per_customer=None) -> dict:
    """What a business can afford before any results exist: handed to the
    strategy and paid-media agents so plans are sized to real margins."""

    margin_pct, aov, orders = _num(gross_margin_pct), _num(average_order_value), _num(orders_per_customer)
    margin = margin_pct / 100 if margin_pct and 0 < margin_pct <= 100 else None
    per_order = aov * margin if aov and margin else None
    return {k: v for k, v in {
        "gross_margin_pct": margin_pct if margin else None,
        "break_even_roas": _r(_div(1, margin)),
        "average_order_value": aov,
        "max_cost_per_customer_first_order": _r(per_order),
        "max_cost_per_customer_lifetime": _r(per_order * orders) if per_order and orders else None,
    }.items() if v is not None}
