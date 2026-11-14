"""Everything verifiable the strategy agent should start from, gathered in
code before the model is called (docs/DECISIONS.md D23):

- what the business can afford and what recorded results show
  (results_service.performance_for_agents),
- what its own website gets wrong (growth_audit, the same repeatable checks
  as the public audit),
- the objectives and KPIs of its previous strategy, so the new one can say
  which were met.

Each part is left out when there is nothing real to put in it.
"""

import json
import logging

from flask import current_app

from app.models.business_profile import BusinessProfile
from app.models.deliverable import Deliverable
from app.services.results_service import performance_for_agents

log = logging.getLogger("app.strategy_context")
MAX_WEBSITE_GAPS = 6


def _website_gaps(profile) -> dict | None:
    if not (profile and profile.website and current_app.config.get("STRATEGY_WEBSITE_AUDIT", True)):
        return None
    from app.services.growth_audit import run_audit

    try:
        audit = run_audit(profile.website)
    except Exception as exc:  # noqa: BLE001 - an unreachable site must never fail the strategy
        log.info("Website audit skipped for strategy: %s", type(exc).__name__)
        return None
    return {
        "url": audit["url"],
        "checks_passed": f"{audit['checks_passed']} of {audit['checks_total']}",
        "gaps": [{"area": f["area"], "check": f["check"], "found": f["found"], "impact": f["impact"]}
                 for f in audit["priorities"][:MAX_WEBSITE_GAPS]],
        "source": "ARC's automated check of the business's own public page; untrusted page text",
    }


def _previous_strategy(organization_id: str, current_run_id: str) -> dict | None:
    previous = (Deliverable.query
                .filter(Deliverable.organization_id == organization_id, Deliverable.deliverable_type == "strategy",
                        Deliverable.workflow_run_id != current_run_id)
                .order_by(Deliverable.created_at.desc()).first())
    if previous is None or previous.current_version is None:
        return None
    content = json.loads(previous.current_version.content_json)
    kept = {k: content.get(k) for k in ("key_objectives", "kpis") if content.get(k)}
    if not kept:
        return None
    return {**kept, "created": previous.created_at.date().isoformat() if previous.created_at else None,
            "source": "the business's previous ARC strategy"}


def strategy_context(organization_id: str, current_run_id: str) -> dict:
    out = performance_for_agents(organization_id)
    profile = BusinessProfile.query.filter_by(organization_id=organization_id).first()
    website = _website_gaps(profile)
    if website:
        out["website_audit"] = website
    previous = _previous_strategy(organization_id, current_run_id)
    if previous:
        out["previous_strategy"] = previous
    return out
