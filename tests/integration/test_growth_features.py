"""Profit maths, Growth Score, Growth Audit, cost report and agent teams
(docs/DECISIONS.md D22)."""

from datetime import date, timedelta

from app.services.growth_audit import audit_html
from app.services.unit_economics import economics, targets
from tests.conftest import create_campaign, create_org, register_and_login

GOOD_PAGE = """<html lang="en"><head><title>AC repair in Dubai Marina | CoolFix</title>
<meta name="description" content="Same-day AC repair and servicing across Dubai Marina and JLT. Fixed prices, licensed technicians.">
<meta name="viewport" content="width=device-width"><link rel="canonical" href="https://coolfix.example/">
<meta property="og:title" content="CoolFix"><meta property="og:image" content="https://coolfix.example/a.jpg">
<script type="application/ld+json">{}</script><script src="https://www.googletagmanager.com/gtag/js"></script></head>
<body><h1>Same-day AC repair in Dubai Marina</h1><img src="a.jpg" alt="Technician servicing an AC unit">
<a href="tel:+97140000000">Call now</a><a href="https://wa.me/97150000000">WhatsApp us</a>
<a href="https://instagram.com/coolfix">Instagram</a><form></form><p>""" + ("word " * 300) + "</p></body></html>"


def test_four_times_roas_on_a_thin_margin_loses_money():
    e = economics({"spend": 5000, "revenue": 20000, "conversions": 40, "leads": 200}, gross_margin_pct=20)
    assert e["roas"] == 4.0 and e["break_even_roas"] == 5.0
    assert e["contribution_profit"] == -1000.0 and e["verdict"] == "losing"
    assert e["customer_acquisition_cost"] == 125.0 and e["lead_to_customer_pct"] == 20.0
    assert "lost about $1,000" in e["explanation"]


def test_economics_never_guesses_missing_inputs():
    e = economics({"spend": 5000, "revenue": 20000})
    assert e["verdict"] == "unknown" and e["contribution_profit"] is None and e["break_even_roas"] is None
    assert "gross margin" in e["missing"] and "new customers" in e["missing"]
    assert economics({}, gross_margin_pct=40)["roas"] is None
    assert economics({"spend": 0, "revenue": 100}, gross_margin_pct=40)["roas"] is None  # no divide by zero


def test_lifetime_value_and_payback():
    e = economics({"spend": 1000, "revenue": 4000, "conversions": 10}, gross_margin_pct=50, orders_per_customer=3)
    assert e["average_order_value"] == 400.0 and e["contribution_per_order"] == 200.0
    assert e["customer_lifetime_value"] == 600.0 and e["ltv_to_cac"] == 6.0 and e["payback_orders"] == 0.5
    assert targets(50, 400, 3) == {"gross_margin_pct": 50.0, "break_even_roas": 2.0, "average_order_value": 400.0,
                                   "max_cost_per_customer_first_order": 200.0, "max_cost_per_customer_lifetime": 600.0}
    assert targets() == {}


def test_audit_passes_a_well_built_page_and_ranks_gaps_on_a_bare_one():
    good = audit_html(GOOD_PAGE, "https://coolfix.example/")
    assert good["checks_passed"] == good["checks_total"] and good["priorities"] == []

    bare = audit_html("<html><head><title>Home</title></head><body><h1>A</h1><h1>B</h1></body></html>", "http://x.example/")
    failed = [f["check"] for f in bare["priorities"]]
    assert "Secure address (HTTPS)" in failed and "A clear next step" in failed and "Visitor tracking installed" in failed
    impacts = [f["impact"] for f in bare["priorities"]]
    assert impacts == sorted(impacts, key=["high", "medium", "low"].index)
    assert all(f["fix"] for f in bare["priorities"])


def test_audit_ignores_titles_inside_svg_icons():
    page = "<html><head><title>AC repair in Dubai Marina | CoolFix</title></head><body><svg><title>Visa</title></svg></body></html>"
    title_check = next(f for f in audit_html(page, "https://x.example/")["passed"] if f["check"].startswith("Page title"))
    assert "CoolFix" in title_check["found"]


def test_public_audit_endpoint_reads_the_page_and_records_a_lead(client, app, monkeypatch):
    monkeypatch.setattr("app.services.growth_audit.fetch_html", lambda url: ("https://coolfix.example/", GOOD_PAGE))
    resp = client.post("/api/v1/public/growth-audit", json={"url": "coolfix.example", "email": "owner@coolfix.example",
                                                            "industry": "Home services"})
    assert resp.status_code == 200 and resp.get_json()["audit"]["checks_passed"] == 15
    with app.app_context():
        from app.models.platform import ContactEnquiry

        lead = ContactEnquiry.query.filter_by(topic="growth_audit").one()
        assert lead.email == "owner@coolfix.example" and "Home services" in lead.message
    # No email: the report is still returned and nothing is stored.
    assert client.post("/api/v1/public/growth-audit", json={"url": "coolfix.example"}).status_code == 200
    with app.app_context():
        assert ContactEnquiry.query.filter_by(topic="growth_audit").count() == 1
    assert client.post("/api/v1/public/growth-audit", json={"url": "x.example", "email": "nope"}).status_code == 400


def test_audit_refuses_private_addresses(client):
    assert client.post("/api/v1/public/growth-audit", json={"url": "http://127.0.0.1/admin"}).status_code == 400
    assert client.post("/api/v1/public/growth-audit", json={"url": ""}).status_code == 400


def test_speed_test_reports_not_connected_without_a_key_and_parses_googles_answer(client, app, monkeypatch):
    app.config["PAGESPEED_API_KEY"] = ""
    body = client.post("/api/v1/public/growth-audit/speed", json={"url": "coolfix.example"}).get_json()
    assert body["speed"] is None and "not connected" in body["unavailable"]

    app.config["PAGESPEED_API_KEY"] = "k"
    monkeypatch.setattr("app.services.growth_audit._psi_http", lambda url: {"lighthouseResult": {
        "categories": {"performance": {"score": 0.62}},
        "audits": {"largest-contentful-paint": {"displayValue": "3.1 s"}}}})
    speed = client.post("/api/v1/public/growth-audit/speed", json={"url": "coolfix.example"}).get_json()["speed"]
    assert speed["performance_score"] == 62 and speed["metrics"] == [{"label": "Main content visible", "value": "3.1 s"}]


def _result(client, org_id, campaign_id, **metrics):
    end = date.today() - timedelta(days=5)
    resp = client.post(f"/api/v1/organizations/{org_id}/results", json={
        "campaign_id": campaign_id, "channel": "Meta ads", "period_start": (end - timedelta(days=20)).isoformat(),
        "period_end": end.isoformat(), **metrics})
    assert resp.status_code == 201, resp.get_json()


def test_growth_score_only_scores_what_is_measured(client):
    register_and_login(client)
    org = create_org(client)
    base = f"/api/v1/organizations/{org['id']}"

    empty = client.get(f"{base}/growth-score").get_json()
    measured = {d["key"] for d in empty["dimensions"] if d["measured"]}
    assert measured == {"brand_readiness"} and empty["total_dimensions"] == 6
    assert all(d["score"] is None and d["next_step"] for d in empty["dimensions"] if not d["measured"])

    assert client.patch(f"{base}/business-profile", json={"gross_margin_pct": 20, "currency": "usd"}).status_code == 200
    campaign = create_campaign(client, org["id"])
    _result(client, org["id"], campaign["id"], spend=5000, revenue=20000, clicks=1000, leads=200, conversions=40)

    score = client.get(f"{base}/growth-score").get_json()
    dims = {d["key"]: d for d in score["dimensions"]}
    assert dims["campaign_performance"]["score"] == 40  # 4.0x against a 5.0x break-even
    assert dims["website_conversion"]["score"] == 80  # 40 customers / 1000 clicks = 4%
    assert dims["lead_generation"]["score"] == 50  # no earlier period to compare
    assert not dims["customer_retention"]["measured"] and not dims["customer_advocacy"]["measured"]
    assert score["measured_dimensions"] == 4 and "4 of 6" in score["note"]

    summary = client.get(f"{base}/results").get_json()
    assert summary["currency"] == "USD" and summary["economics"]["verdict"] == "losing"
    assert summary["by_channel"][0]["economics"]["contribution_profit"] == -1000.0


def test_profile_rejects_impossible_commercial_numbers(client):
    register_and_login(client)
    org = create_org(client)
    url = f"/api/v1/organizations/{org['id']}/business-profile"
    assert client.patch(url, json={"gross_margin_pct": 140}).status_code == 400
    assert client.patch(url, json={"average_order_value": "lots"}).status_code == 400
    assert client.patch(url, json={"currency": "dirhams"}).status_code == 400
    assert client.patch(url, json={"currency": "AED"}).status_code == 400  # USD only
    assert client.patch(url, json={"gross_margin_pct": ""}).status_code == 200  # clearing is allowed


def test_agents_get_margins_and_verified_results(client, app):
    register_and_login(client)
    org = create_org(client)
    base = f"/api/v1/organizations/{org['id']}"
    client.patch(f"{base}/business-profile", json={"gross_margin_pct": 50, "average_order_value": 400})
    campaign = create_campaign(client, org["id"])
    with app.app_context():
        from app.services.results_service import performance_for_agents

        only_targets = performance_for_agents(org["id"])
        assert only_targets["unit_economics"]["break_even_roas"] == 2.0 and "verified_results" not in only_targets
    _result(client, org["id"], campaign["id"], spend=1000, revenue=4000, conversions=10)
    with app.app_context():
        channel = performance_for_agents(org["id"])["verified_results"]["by_channel"][0]
        assert channel["verdict"] == "profitable" and channel["contribution_profit"] == 1000.0


def test_cost_report_and_new_endpoints_are_tenant_scoped(client):
    register_and_login(client, email="a@example.com")
    org_a = create_org(client, name="A")
    report = client.get(f"/api/v1/organizations/{org_a['id']}/cost-report").get_json()
    assert report["totals"]["calls"] == 0 and report["budget"]["level"] in ("ok", "none")
    assert report["reliability"]["calls_per_task"] is None
    client.post("/api/v1/auth/logout")

    register_and_login(client, email="b@example.com")
    create_org(client, name="B")
    for path in ("cost-report", "growth-score"):
        assert client.get(f"/api/v1/organizations/{org_a['id']}/{path}").status_code in (403, 404)
    client.post("/api/v1/auth/logout")
    assert client.get(f"/api/v1/organizations/{org_a['id']}/growth-score").status_code == 401


def test_every_agent_belongs_to_a_team(client):
    body = client.get("/api/v1/public/agents").get_json()
    assert len(body["teams"]) == 8
    assert all(a["team"]["key"] for a in body["agents"])
    assert {a["agent_id"] for a in body["agents"] if a["team"]["key"] == "skills"} == {"pr_partnerships", "key_accounts"}
    cmo = next(a for a in body["agents"] if a["agent_id"] == "cmo")
    assert cmo["team"]["name"] == "Growth Orchestrator" and cmo["version"] == "1.4.0"
