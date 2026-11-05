from app.extensions import db
from app.models.membership import Membership
from tests.conftest import create_campaign, create_org, register_and_login


def test_results_are_tenant_scoped(app, client):
    register_and_login(client, email="a@example.com")
    org_a = create_org(client, name="A")
    camp_a = create_campaign(client, org_a["id"])
    row = client.post(f"/api/v1/organizations/{org_a['id']}/results", json={
        "campaign_id": camp_a["id"], "channel": "Email", "period_start": "2026-10-01",
        "period_end": "2026-10-31", "leads": 5}).get_json()["result"]
    client.post("/api/v1/auth/logout")

    register_and_login(client, email="b@example.com")
    org_b = create_org(client, name="B")
    a = f"/api/v1/organizations/{org_a['id']}"
    assert client.get(f"{a}/results").status_code in (403, 404)
    assert client.get(f"{a}/reports/monthly?month=2026-10").status_code in (403, 404)
    assert client.patch(f"{a}/results/{row['id']}", json={"leads": 999}).status_code in (403, 404)
    assert client.delete(f"{a}/results/{row['id']}").status_code in (403, 404)
    # Can't attach a result in B to A's campaign, or edit A's row through B.
    b = f"/api/v1/organizations/{org_b['id']}"
    resp = client.post(f"{b}/results", json={"campaign_id": camp_a["id"], "channel": "Email",
                                             "period_start": "2026-10-01", "period_end": "2026-10-31", "leads": 1})
    assert resp.status_code == 400
    assert client.patch(f"{b}/results/{row['id']}", json={"leads": 999}).status_code == 404


def test_viewers_cannot_enter_results(app, client):
    register_and_login(client)
    org = create_org(client)
    camp = create_campaign(client, org["id"])
    with app.app_context():
        m = Membership.query.filter_by(organization_id=org["id"]).first()
        m.role = "viewer"
        db.session.commit()
    resp = client.post(f"/api/v1/organizations/{org['id']}/results", json={
        "campaign_id": camp["id"], "channel": "Email", "period_start": "2026-10-01", "period_end": "2026-10-31", "leads": 5})
    assert resp.status_code == 403
    assert client.get(f"/api/v1/organizations/{org['id']}/results").status_code == 200
