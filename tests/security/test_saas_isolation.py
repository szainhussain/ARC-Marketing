"""Every workspace-scoped endpoint added for the SaaS foundation must deny
other tenants."""

from tests.conftest import create_org, register_and_login


def test_saas_endpoints_deny_other_tenants(app, client):
    register_and_login(client, email="a@example.com")
    a = create_org(client, name="A")["id"]
    client.post("/api/v1/auth/logout")
    register_and_login(client, email="b@example.com")
    create_org(client, name="B")

    checks = [
        ("get", ""), ("patch", ""), ("get", "/members"), ("post", "/invitations"), ("get", "/billing"),
        ("post", "/billing/checkout"), ("get", "/billing/history"), ("get", "/policies"),
        ("patch", "/policies/knowledge_update"), ("get", "/notifications"), ("post", "/notifications/read"),
        ("get", "/knowledge"), ("post", "/knowledge"), ("get", "/calendar"), ("post", "/calendar"),
        ("get", "/deliverables"), ("get", "/documents"), ("get", "/dashboard"), ("get", "/analytics"),
        ("get", "/reports/export.csv"), ("get", "/webhooks"), ("post", "/webhooks"), ("get", "/export"),
        ("post", "/deletion"), ("get", "/integrations/catalog"), ("patch", "/agents/cmo/settings"),
    ]
    for method, suffix in checks:
        url = f"/api/v1/organizations/{a}{suffix}"
        assert getattr(client, method)(url, json={}).status_code == 403, f"{method} {url}"


def test_viewer_cannot_administer(app, client):
    from app.extensions import db
    from app.models.membership import Membership

    register_and_login(client, email="v@example.com")
    org = create_org(client)["id"]
    m = Membership.query.filter_by(organization_id=org).one()
    m.role = "viewer"
    db.session.commit()
    for method, suffix, body in [
        ("patch", "", {"name": "x"}), ("post", "/invitations", {"email": "q@example.com"}),
        ("post", "/billing/checkout", {"plan_code": "growth"}), ("post", "/knowledge", {"title": "t", "body": "b"}),
        ("post", "/webhooks", {}), ("get", "/export", None), ("post", "/deletion", {}),
    ]:
        resp = getattr(client, method)(f"/api/v1/organizations/{org}{suffix}", json=body)
        assert resp.status_code == 403, f"{method} {suffix}"


def test_workspace_accent_is_tenant_scoped(app, client):
    from app.extensions import db
    from app.models.organization import Organization

    register_and_login(client, email="a2@example.com")
    a = create_org(client, name="A")["id"]
    client.post("/api/v1/auth/logout")
    register_and_login(client, email="b2@example.com")
    create_org(client, name="B")
    assert client.patch(f"/api/v1/organizations/{a}", json={"accent_color": "rose"}).status_code == 403
    assert client.get(f"/api/v1/organizations/{a}").status_code == 403
    db.session.expire_all()
    assert db.session.get(Organization, a).accent_color is None
