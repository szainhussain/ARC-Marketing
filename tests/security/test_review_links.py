"""Client review links carry approval power for one approval, so they must be
single-use, expiring, revocable, version-bound, approver-created only, and
must never expose other workspaces or the team's internal comments."""

from datetime import timedelta

from app.extensions import db
from app.models.approval import Approval
from app.models.base import utcnow
from app.models.collaboration import ReviewLink
from app.services.deliverable_service import create_deliverable_with_first_version
from tests.conftest import create_campaign, create_org, register_and_login

CONTENT = {"creative_brief": "v1 brief", "variants": [], "calendar_notes": ""}


def _setup(app, client, email="owner@example.com"):
    register_and_login(client, email=email)
    org = create_org(client)
    campaign = create_campaign(client, org["id"])
    with app.app_context():
        d = create_deliverable_with_first_version(organization_id=org["id"], campaign_id=campaign["id"],
                                                  workflow_run_id=None, deliverable_type="content_pack", content=CONTENT)
        db.session.commit()
        did = d.id
    approval = client.post(f"/api/v1/organizations/{org['id']}/approvals", json={"deliverable_id": did}).get_json()["approval"]
    return org, did, approval


def _link(client, org, approval, **body):
    resp = client.post(f"/api/v1/organizations/{org['id']}/approvals/{approval['id']}/review-links", json=body)
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["url"].rsplit("/review/", 1)[1], resp.get_json()["review_link"]


def test_client_can_view_and_approve_once(app, client):
    org, did, approval = _setup(app, client)
    client.post(f"/api/v1/organizations/{org['id']}/deliverables/{did}/comments", json={"body": "Internal: check pricing"})
    token, _ = _link(client, org, approval, label="Client: Sara", days=5)
    client.post("/api/v1/auth/logout")

    view = client.get(f"/api/v1/public/review/{token}").get_json()
    assert view["can_decide"] and view["content"]["creative_brief"] == "v1 brief"
    assert view["comments"] == []  # internal team comments are never shown to the client
    bad = client.post(f"/api/v1/public/review/{token}/decision", json={"decision": "approved", "name": "", "email": "x"})
    assert bad.status_code == 400
    ok = client.post(f"/api/v1/public/review/{token}/decision",
                     json={"decision": "approved", "name": "Sara", "email": "sara@client.com", "comment": "Looks great"})
    assert ok.status_code == 200 and ok.get_json()["decision"] == "approved"
    again = client.post(f"/api/v1/public/review/{token}/decision",
                        json={"decision": "rejected", "name": "Sara", "email": "sara@client.com"})
    assert again.status_code == 409
    after = client.get(f"/api/v1/public/review/{token}").get_json()
    assert after["can_decide"] is False and after["comments"][0]["body"] == "Looks great"
    with app.app_context():
        a = db.session.get(Approval, approval["id"])
        assert a.decided_by_external_email == "sara@client.com" and a.decided_by_user_id is None


def test_editing_after_sharing_blocks_the_link(app, client):
    org, did, approval = _setup(app, client)
    token, _ = _link(client, org, approval)
    edit = client.post(f"/api/v1/organizations/{org['id']}/deliverables/{did}/versions",
                       json={"content": {**CONTENT, "creative_brief": "v2"}})
    assert edit.status_code == 201
    resp = client.post(f"/api/v1/public/review/{token}/decision",
                       json={"decision": "approved", "name": "Sara", "email": "sara@client.com"})
    assert resp.status_code == 409  # approval was invalidated by the new version


def test_revoked_expired_and_unknown_links_are_refused(app, client):
    org, did, approval = _setup(app, client)
    token, link = _link(client, org, approval)
    assert client.delete(f"/api/v1/organizations/{org['id']}/review-links/{link['id']}").status_code == 200
    assert client.get(f"/api/v1/public/review/{token}").status_code == 404
    token2, link2 = _link(client, org, approval)
    with app.app_context():
        row = db.session.get(ReviewLink, link2["id"])
        row.expires_at = utcnow() - timedelta(minutes=1)
        db.session.commit()
    assert client.get(f"/api/v1/public/review/{token2}").status_code == 404
    assert client.get("/api/v1/public/review/not-a-real-token").status_code == 404


def test_only_approvers_create_links_and_other_workspaces_are_denied(app, client):
    org, did, approval = _setup(app, client)
    client.post("/api/v1/auth/logout")
    register_and_login(client, email="intruder@example.com")
    create_org(client, name="Other Co")
    base = f"/api/v1/organizations/{org['id']}"
    assert client.post(f"{base}/approvals/{approval['id']}/review-links", json={}).status_code in (403, 404)
    assert client.get(f"{base}/deliverables/{did}/comments").status_code in (403, 404)
    assert client.post(f"{base}/deliverables/{did}/comments", json={"body": "hi"}).status_code in (403, 404)

    client.post("/api/v1/auth/logout")
    client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": "correct-horse-1"})
    from app.models.membership import Membership

    with app.app_context():
        m = Membership.query.filter_by(organization_id=org["id"]).first()
        m.role = "contributor"
        db.session.commit()
    assert client.post(f"{base}/approvals/{approval['id']}/review-links", json={}).status_code == 403


def test_edits_must_match_the_schema(app, client):
    org, did, _ = _setup(app, client)
    bad = client.post(f"/api/v1/organizations/{org['id']}/deliverables/{did}/versions",
                      json={"content": {"creative_brief": 123, "variants": "nope"}})
    assert bad.status_code == 400 and bad.get_json()["error"]["code"] == "VALIDATION_ERROR"
    client.patch(f"/api/v1/organizations/{org['id']}/business-profile", json={"prohibited_phrases": "guaranteed results"})
    ok = client.post(f"/api/v1/organizations/{org['id']}/deliverables/{did}/versions",
                     json={"content": {**CONTENT, "creative_brief": "Guaranteed results in a week"}})
    assert ok.status_code == 201 and ok.get_json()["brand_check"]["passed"] is False
