"""Growth Score, cost report and profit figures never cross workspaces (D22)."""

from tests.conftest import create_campaign, create_org, register_and_login


def test_growth_and_cost_endpoints_deny_other_tenants(app, client):
    register_and_login(client, email="a@example.com")
    org_a = create_org(client, name="A")
    a = f"/api/v1/organizations/{org_a['id']}"
    client.patch(f"{a}/business-profile", json={"gross_margin_pct": 20})
    campaign = create_campaign(client, org_a["id"])
    client.post(f"{a}/results", json={"campaign_id": campaign["id"], "channel": "Meta ads", "period_start": "2026-10-01",
                                      "period_end": "2026-10-31", "spend": 5000, "revenue": 20000})
    client.post("/api/v1/auth/logout")

    register_and_login(client, email="b@example.com")
    org_b = create_org(client, name="B")
    for path in ("growth-score", "cost-report", "results"):
        assert client.get(f"{a}/{path}").status_code in (403, 404)
    # B's own figures contain nothing of A's margin or results.
    own = client.get(f"/api/v1/organizations/{org_b['id']}/results").get_json()
    assert own["economics"]["roas"] is None and own["economics"]["gross_margin_pct"] is None
    score = client.get(f"/api/v1/organizations/{org_b['id']}/growth-score").get_json()
    assert score["measured_dimensions"] == 1

    client.post("/api/v1/auth/logout")
    for path in ("growth-score", "cost-report"):
        assert client.get(f"{a}/{path}").status_code == 401
