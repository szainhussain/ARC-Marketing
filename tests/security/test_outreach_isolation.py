"""Outreach data and sending are workspace-scoped and role-gated."""

from app.extensions import db
from app.models.membership import Membership
from tests.conftest import create_org, register_and_login
from tests.integration.test_outreach import FakeMail, _batch, _list, _sender, mail  # noqa: F401  (fixture)


def test_other_workspace_is_denied_every_outreach_endpoint(app, client, mail):
    register_and_login(client)
    org_a = create_org(client, name="A")
    _sender(client, org_a["id"])
    lst = _list(client, org_a["id"]).get_json()["list"]
    b = _batch(client, org_a["id"], lst["id"])
    client.post("/api/v1/auth/logout")
    register_and_login(client, email="intruder@example.com")
    create_org(client, name="B")
    base = f"/api/v1/organizations/{org_a['id']}/outreach"
    checks = [("get", base), ("post", f"{base}/sender"), ("delete", f"{base}/sender"), ("post", f"{base}/lists"),
              ("get", f"{base}/lists/{lst['id']}/contacts"), ("get", f"{base}/suppressions"), ("post", f"{base}/suppressions"),
              ("post", f"{base}/batches"), ("patch", f"{base}/batches/{b['id']}"), ("get", f"{base}/batches/{b['id']}/preview"),
              ("post", f"{base}/batches/{b['id']}/approve"), ("post", f"{base}/batches/{b['id']}/start")]
    for method, url in checks:
        assert getattr(client, method)(url, json={}).status_code == 403, url


def test_viewer_cannot_send_or_approve(app, client, mail):
    register_and_login(client)
    org = create_org(client)
    _sender(client, org["id"])
    lst = _list(client, org["id"]).get_json()["list"]
    b = _batch(client, org["id"], lst["id"])
    base = f"/api/v1/organizations/{org['id']}/outreach/batches/{b['id']}"
    client.post(f"{base}/request-approval")
    with app.app_context():
        Membership.query.filter_by(organization_id=org["id"]).first().role = "viewer"
        db.session.commit()
    assert client.post(f"{base}/approve").status_code == 403
    assert client.post(f"{base}/start").status_code == 403
    assert _sender(client, org["id"]).status_code == 403
    assert _list(client, org["id"], name="x").status_code == 403
