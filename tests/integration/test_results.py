from datetime import date

from tests.conftest import create_campaign, create_org, register_and_login


def _row(campaign_id, **kw):
    base = {"campaign_id": campaign_id, "channel": "Instagram", "period_start": "2026-10-01", "period_end": "2026-10-31"}
    return {**base, **kw}


def test_results_metrics_monthly_report_and_dashboard(client):
    register_and_login(client)
    org = create_org(client)
    camp = create_campaign(client, org["id"])
    base = f"/api/v1/organizations/{org['id']}"

    bad = client.post(f"{base}/results", json=_row(camp["id"], spend="abc", period_end="2026-09-01"))
    assert bad.status_code == 400
    assert client.post(f"{base}/results", json=_row(camp["id"])).status_code == 400  # no numbers at all

    ig = client.post(f"{base}/results", json=_row(camp["id"], spend=500, impressions=40000, clicks=800, leads=40,
                                                  conversions=10, revenue=2000)).get_json()["result"]
    client.post(f"{base}/results", json=_row(camp["id"], channel="Google Ads", spend=300, clicks=300, leads=10))
    data = client.get(f"{base}/results?from=2026-10-01&to=2026-10-31").get_json()
    t = data["totals"]
    assert t["spend"] == 800 and t["leads"] == 50 and t["revenue"] == 2000
    assert t["cost_per_lead"] == 16.0 and t["roas"] == 2.5
    ig_row = next(c for c in data["by_channel"] if c["channel"] == "Instagram")
    assert ig_row["ctr_pct"] == 2.0 and ig_row["conversion_rate_pct"] == 1.25
    gads = next(c for c in data["by_channel"] if c["channel"] == "Google Ads")
    assert gads["roas"] is None  # no revenue entered: not invented

    assert client.patch(f"{base}/results/{ig['id']}", json={"revenue": 2500}).get_json()["result"]["revenue"] == 2500

    report = client.get(f"{base}/reports/monthly?month=2026-10").get_json()
    assert report["results"]["totals"]["revenue"] == 2500
    assert any("Lowest cost per lead: Instagram" in h for h in report["highlights"])
    assert client.get(f"{base}/reports/monthly?month=oct").status_code == 400

    # The dashboard shows entered numbers as "manual", and leaves the rest unconnected.
    dash = client.get(f"{base}/dashboard?days=365").get_json()
    metrics = {m["key"]: m for m in dash["business_metrics"]}
    if date.today() <= date(2027, 10, 1):  # results fall inside the 365-day window
        assert metrics["leads"]["status"] == "manual" and metrics["leads"]["value"] == 50
    assert metrics["website_traffic"]["status"] == "not_connected"

    assert client.delete(f"{base}/results/{ig['id']}").status_code == 200
