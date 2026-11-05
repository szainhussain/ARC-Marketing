"""Ad spend is workspace-scoped and role-gated: no other workspace can see,
launch, approve or control ads; viewers can't approve or raise the cap."""

from app.extensions import db
from app.models.membership import Membership
from tests.conftest import create_org, register_and_login
from tests.integration.test_ads import _plan, _request


def test_other_workspace_is_denied_every_ads_endpoint(app, client):
    register_and_login(client)
    org = create_org(client, name="A")
    base = f"/api/v1/organizations/{org['id']}/ads"
    client.post(f"{base}/guardrail", json={"max_daily_budget": 50})
    did = _plan(app, client, org["id"])
    lid = _request(client, base, did).get_json()["launch"]["id"]
    client.post("/api/v1/auth/logout")
    register_and_login(client, email="intruder@example.com")
    create_org(client, name="B")
    for method, url in [("get", base), ("post", f"{base}/guardrail"), ("post", f"{base}/launches"),
                        ("post", f"{base}/launches/{lid}/decision"), ("post", f"{base}/launches/{lid}/pause"),
                        ("post", f"{base}/launches/{lid}/resume"), ("post", f"{base}/stop-all")]:
        assert getattr(client, method)(url, json={"decision": "approve", "confirm_daily_budget": 20}).status_code == 403, url


def test_viewer_cannot_approve_or_raise_the_cap(app, client):
    register_and_login(client)
    org = create_org(client)
    base = f"/api/v1/organizations/{org['id']}/ads"
    client.post(f"{base}/guardrail", json={"max_daily_budget": 50})
    did = _plan(app, client, org["id"])
    lid = _request(client, base, did).get_json()["launch"]["id"]
    with app.app_context():
        Membership.query.filter_by(organization_id=org["id"]).first().role = "viewer"
        db.session.commit()
    assert client.post(f"{base}/launches/{lid}/decision", json={"decision": "approve", "confirm_daily_budget": 20}).status_code == 403
    assert client.post(f"{base}/guardrail", json={"max_daily_budget": 500}).status_code == 403
    assert _request(client, base, did).status_code == 403
