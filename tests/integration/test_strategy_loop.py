"""Research-first strategy, its verified context, the 90-day roadmap, cached
tokens, budget notifications and the platform margin view (D23)."""

from datetime import date, timedelta

from app.extensions import db
from app.workflows.engine import drain
from tests.conftest import complete_profile, create_campaign, create_org, register_and_login
from tests.fakes import FAKE_OUTPUTS, FakeProvider, use_provider

PAGE = "<html><head><title>Home</title></head><body><h1>A</h1><h1>B</h1></body></html>"


def _run(client, org_id, campaign_id, key):
    resp = client.post(f"/api/v1/organizations/{org_id}/campaigns/{campaign_id}/runs", headers={"Idempotency-Key": key})
    assert resp.status_code == 202, resp.get_json()
    return resp.get_json()["workflow_run"]


def _strategy_call(provider):
    return next(c for c in provider.calls if c["task_type"] == "strategy")


def test_strategy_runs_after_research_and_reads_it(client, app, monkeypatch):
    register_and_login(client)
    org = create_org(client)
    complete_profile(client, org["id"])
    campaign = create_campaign(client, org["id"])
    provider = FakeProvider()
    use_provider(monkeypatch, provider)
    run = _run(client, org["id"], campaign["id"], "r1")
    assert [t["agent_id"] for t in run["tasks"] if t["status"] == "ready"] == ["research_analyst"]
    with app.app_context():
        drain()
    order = [c["task_type"] for c in provider.calls]
    assert order.index("research_notes") < order.index("strategy")
    research = _strategy_call(provider)["input_data"]["research"]
    assert research["audience_hypotheses"] == FAKE_OUTPUTS["research_notes"]["audience_hypotheses"]


def test_strategy_context_holds_only_what_is_real(client, app, monkeypatch):
    register_and_login(client)
    org = create_org(client)
    base = f"/api/v1/organizations/{org['id']}"
    complete_profile(client, org["id"])
    campaign = create_campaign(client, org["id"])
    with app.app_context():
        from app.services.strategy_context import strategy_context

        assert strategy_context(org["id"], "none") == {}  # no margins, results, website or earlier strategy

    client.patch(f"{base}/business-profile", json={"website": "https://coolfix.example", "gross_margin_pct": 20})
    end = date.today() - timedelta(days=3)
    client.post(f"{base}/results", json={"campaign_id": campaign["id"], "channel": "Meta ads", "spend": 5000, "revenue": 20000,
                                         "period_start": (end - timedelta(days=20)).isoformat(), "period_end": end.isoformat()})
    monkeypatch.setattr("app.services.growth_audit.fetch_html", lambda url: ("http://coolfix.example/", PAGE))
    with app.app_context():
        app.config["STRATEGY_WEBSITE_AUDIT"] = True
        ctx = strategy_context(org["id"], "none")
        assert ctx["unit_economics"]["break_even_roas"] == 5.0
        assert ctx["verified_results"]["by_channel"][0]["verdict"] == "losing"
        gaps = ctx["website_audit"]["gaps"]
        assert 0 < len(gaps) <= 6 and gaps[0]["impact"] == "high"

        # An unreachable website is left out; it never fails the strategy.
        def boom(url):
            raise OSError("down")

        monkeypatch.setattr("app.services.growth_audit.fetch_html", boom)
        assert "website_audit" not in strategy_context(org["id"], "none")


def test_next_strategy_receives_the_previous_kpis(client, app, monkeypatch):
    register_and_login(client)
    org = create_org(client)
    complete_profile(client, org["id"])
    campaign = create_campaign(client, org["id"])
    strategy = {**FAKE_OUTPUTS["strategy"], "kpis": ["40 booked jobs a month"]}
    provider = FakeProvider(overrides={"strategy": strategy})
    use_provider(monkeypatch, provider)
    _run(client, org["id"], campaign["id"], "first")
    with app.app_context():
        drain()
    assert "previous_strategy" not in _strategy_call(provider)["input_data"]

    second = FakeProvider(overrides={"strategy": {**strategy, "previous_kpi_review": [
        {"kpi": "40 booked jobs a month", "status": "not_measured", "evidence": "No results recorded."}]}})
    use_provider(monkeypatch, second)
    run2 = _run(client, org["id"], campaign["id"], "second")
    with app.app_context():
        drain()
    assert _strategy_call(second)["input_data"]["previous_strategy"]["kpis"] == ["40 booked jobs a month"]
    deliverables = client.get(f"/api/v1/organizations/{org['id']}/campaigns/{campaign['id']}/deliverables").get_json()["deliverables"]
    latest = next(d for d in deliverables if d["deliverable_type"] == "strategy" and d["workflow_run_id"] == run2["id"])
    assert latest["id"]


def test_plan_schema_accepts_roadmap_and_tracking():
    from app.ai.schemas import CampaignPlanSchema, StrategySchema

    plan = CampaignPlanSchema().load({**FAKE_OUTPUTS["campaign_plan"], "tracking_requirements": ["Install the Meta Pixel"],
                                      "roadmap_90_day": [{"period": "Days 1-30", "focus": "Fix the website", "activities": ["Add WhatsApp link"],
                                                          "owner": "Owner", "budget_share": "20%", "expected_outcome": "More enquiries (forecast)",
                                                          "kpi": "Enquiries per week"}]})
    assert plan["roadmap_90_day"][0]["period"] == "Days 1-30" and plan["tracking_requirements"]
    assert CampaignPlanSchema().load(FAKE_OUTPUTS["campaign_plan"])["roadmap_90_day"] == []
    assert StrategySchema().load(FAKE_OUTPUTS["strategy"])["previous_kpi_review"] == []


def test_cached_tokens_are_recorded_and_reported(client, app):
    register_and_login(client)
    org = create_org(client)
    with app.app_context():
        from app.services.usage_service import record_usage

        record_usage(org["id"], None, "groq", "m", 1000, 200, 0.01, cached_input_tokens=600)
        record_usage(org["id"], None, "groq", "m", 500, 100, 0.01)
        db.session.commit()
    report = client.get(f"/api/v1/organizations/{org['id']}/cost-report").get_json()
    assert report["totals"]["cached_input_tokens"] == 600 and report["by_model"][0]["cached_input_tokens"] == 600


def test_groq_cached_tokens_are_read_from_usage(monkeypatch):
    from types import SimpleNamespace as NS

    from app.ai.provider_adapter import GroqProvider
    from app.ai.schemas import StrategySchema

    usage = NS(prompt_tokens=900, completion_tokens=50, prompt_tokens_details=NS(cached_tokens=700))
    reply = NS(choices=[NS(message=NS(content='{"strategic_direction": "x", "key_objectives": ["y"]}'), finish_reason="stop")], usage=usage)
    client = NS(chat=NS(completions=NS(create=lambda **kw: reply)))
    provider = GroqProvider("k", "m")
    monkeypatch.setattr(provider, "_client", lambda: client)
    assert provider.generate_structured("strategy", {}, StrategySchema).cached_input_tokens == 700
    usage.prompt_tokens_details = None  # a provider that reports nothing
    assert provider.generate_structured("strategy", {}, StrategySchema).cached_input_tokens == 0


def test_budget_notification_fires_once_per_threshold(client, app):
    register_and_login(client)
    org = create_org(client)
    with app.app_context():
        from app.models.platform import Notification
        from app.services.cost_service import notify_budget_if_crossed
        from app.services.platform_service import entitlements
        from app.services.usage_service import record_usage

        allowance = entitlements(org["id"])["monthly_ai_budget_usd"]
        assert notify_budget_if_crossed(org["id"]) is None
        record_usage(org["id"], None, "groq", "m", 1, 1, allowance * 0.85)
        assert notify_budget_if_crossed(org["id"]) == "ai_budget.warning"
        assert notify_budget_if_crossed(org["id"]) is None  # not repeated
        record_usage(org["id"], None, "groq", "m", 1, 1, allowance * 0.2)
        assert notify_budget_if_crossed(org["id"]) == "ai_budget.reached"
        assert notify_budget_if_crossed(org["id"]) is None
        db.session.commit()
        assert Notification.query.filter(Notification.kind.like("ai_budget.%")).count() == 2


def test_margin_view_is_for_the_platform_owner_only(client, app):
    user = register_and_login(client, email="boss@example.com")
    create_org(client, name="CoolFix")
    assert client.get("/api/v1/admin/unit-economics").status_code == 403  # a workspace owner is not the platform owner
    app.config["PLATFORM_ADMIN_EMAILS"] = {user["email"]}
    rows = client.get("/api/v1/admin/unit-economics").get_json()["workspaces"]
    assert rows[0]["name"] == "CoolFix" and rows[0]["status"] == "trialing"
    assert rows[0]["revenue_usd"] == 0 and rows[0]["gross_margin_pct"] is None  # a trial is not revenue
    client.post("/api/v1/auth/logout")
    assert client.get("/api/v1/admin/unit-economics").status_code == 401
