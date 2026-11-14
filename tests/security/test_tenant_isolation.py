"""Cross-tenant access attempts must be denied server-side, regardless of
what the frontend would or would not show."""

from tests.conftest import create_campaign, create_org, register_and_login


def test_user_cannot_read_another_organizations_campaign(client):
    register_and_login(client, email="owner-a@example.com")
    org_a = create_org(client, name="Org A")
    campaign_a = create_campaign(client, org_a["id"])
    client.post("/api/v1/auth/logout")

    register_and_login(client, email="owner-b@example.com")
    org_b = create_org(client, name="Org B")

    resp = client.get(f"/api/v1/organizations/{org_a['id']}/campaigns/{campaign_a['id']}")
    assert resp.status_code == 403

    resp = client.get(f"/api/v1/organizations/{org_a['id']}/campaigns")
    assert resp.status_code == 403

    # Org B's own data is still reachable, this isn't a blanket auth failure.
    resp = client.get(f"/api/v1/organizations/{org_b['id']}/campaigns")
    assert resp.status_code == 200


def test_user_cannot_read_another_organizations_business_profile(client):
    register_and_login(client, email="owner-a2@example.com")
    org_a = create_org(client, name="Org A2")
    client.post("/api/v1/auth/logout")

    register_and_login(client, email="owner-b2@example.com")

    resp = client.get(f"/api/v1/organizations/{org_a['id']}/business-profile")
    assert resp.status_code == 403

    resp = client.patch(
        f"/api/v1/organizations/{org_a['id']}/business-profile",
        json={"business_name": "Hijacked"},
    )
    assert resp.status_code == 403


def test_contributor_cannot_approve_external_action(app, client):
    # Build org A with an owner, then directly downgrade the owner's own
    # membership role to "contributor" to exercise the role check, since
    # the MVP has no invite-by-email flow yet.
    register_and_login(client)
    org = create_org(client)
    campaign = create_campaign(client, org["id"])

    from app.extensions import db
    from app.models.membership import Membership
    from app.services.deliverable_service import create_deliverable_with_first_version

    with app.app_context():
        deliverable = create_deliverable_with_first_version(
            organization_id=org["id"],
            campaign_id=campaign["id"],
            workflow_run_id=None,
            deliverable_type="content_pack",
            content={"creative_brief": "brief", "variants": [], "calendar_notes": ""},
        )
        db.session.commit()
        deliverable_id = deliverable.id

        membership = Membership.query.filter_by(organization_id=org["id"]).first()
        membership.role = "contributor"
        db.session.commit()

    approval = client.post(
        f"/api/v1/organizations/{org['id']}/approvals",
        json={"deliverable_id": deliverable_id},
    ).get_json()["approval"]

    resp = client.post(
        f"/api/v1/organizations/{org['id']}/approvals/{approval['id']}/decision",
        json={"decision": "approved"},
    )
    assert resp.status_code == 403
