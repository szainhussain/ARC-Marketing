"""WordPress.com live publishing: connect via signed OAuth state, publish an
approved article once, verify it by reading it back, and refuse anything that
isn't approved, current, connected or allowed by the kill switch."""

import json
from urllib.parse import parse_qs, urlparse

import pytest

from app.extensions import db
from app.integrations import wordpress_com as wp
from app.models.external_action import ExternalAction
from app.models.integration import Integration
from app.services.deliverable_service import create_deliverable_with_first_version
from app.workflows.engine import drain
from tests.conftest import create_campaign, create_org, register_and_login

ARTICLE = {"title": "How to plant autumn bulbs", "target_keyword": "autumn bulbs",
           "excerpt": "A quick guide.", "tags": ["gardening"],
           "body_markdown": "## Pick a sunny spot\n\nPlant bulbs twice as deep as they are tall. "
                            "<script>alert(1)</script>\n\n- Tulips\n- **Daffodils**"}


class FakeWP:
    """Stands in for public-api.wordpress.com."""

    def __init__(self):
        self.posts, self.calls, self.fail_next = {}, [], []

    def __call__(self, method, url, data=None, token=None):
        self.calls.append((method, url, data, token))
        if self.fail_next:
            raise self.fail_next.pop(0)
        path = urlparse(url).path
        if path.endswith("/oauth2/token"):
            assert data["code"] == "good-code"
            return {"access_token": "tok-secret-123", "blog_id": 4242, "blog_url": "https://fernleaf.wordpress.com", "scope": ""}
        assert token == "tok-secret-123"
        if "/posts/slug:" in path:
            slug = path.rsplit("slug:", 1)[1]
            for p in self.posts.values():
                if p["slug"] == slug:
                    return p
            raise wp.WordPressError("not found", status=404)
        if path.endswith("/posts/new"):
            pid = len(self.posts) + 100
            self.posts[pid] = {"ID": pid, "slug": data["slug"], "status": data["status"], "content": data["content"],
                               "URL": f"https://fernleaf.wordpress.com/{data['slug']}/"}
            return self.posts[pid]
        if path.endswith("/delete"):
            post = self.posts[int(path.rsplit("/", 2)[1])]
            post["status"] = "trash"
            return post
        if "/posts/" in path:
            return self.posts[int(path.rsplit("/", 1)[1])]
        return {"URL": "https://fernleaf.wordpress.com"}


@pytest.fixture
def fake_wp(app, monkeypatch):
    app.config.update(WORDPRESS_CLIENT_ID="cid", WORDPRESS_CLIENT_SECRET="csecret")
    fake = FakeWP()
    monkeypatch.setattr(wp, "_http", fake)
    return fake


def _connect(client, org_id):
    r = client.post(f"/api/v1/organizations/{org_id}/integrations/wordpress/connect")
    assert r.status_code == 200
    state = parse_qs(urlparse(r.get_json()["authorize_url"]).query)["state"][0]
    cb = client.get(f"/api/v1/integrations/wordpress/callback?code=good-code&state={state}")
    assert cb.status_code == 302 and "wordpress=connected" in cb.headers["Location"]
    return state


def _approved_article(app, client, org_id, campaign_id):
    with app.app_context():
        d = create_deliverable_with_first_version(organization_id=org_id, campaign_id=campaign_id, workflow_run_id=None,
                                                  deliverable_type="site_optimization_plan",
                                                  content={"keyword_themes": [], "blog_articles": [ARTICLE]})
        db.session.commit()
        did = d.id
    ap = client.post(f"/api/v1/organizations/{org_id}/approvals", json={"deliverable_id": did}).get_json()["approval"]
    client.post(f"/api/v1/organizations/{org_id}/approvals/{ap['id']}/decision", json={"decision": "approved"})
    return did, ap["id"]


def _setup(app, client, fake_wp):
    register_and_login(client)
    org = create_org(client)
    camp = create_campaign(client, org["id"])
    _connect(client, org["id"])
    did, aid = _approved_article(app, client, org["id"], camp["id"])
    return org["id"], camp["id"], did, aid


def test_connect_stores_token_encrypted_and_never_returns_it(app, client, fake_wp):
    register_and_login(client)
    org = create_org(client)
    _connect(client, org["id"])
    with app.app_context():
        integ = Integration.query.filter_by(organization_id=org["id"], provider="wordpress_com").one()
        assert integ.state == "connected" and integ.external_account_id == "4242"
        assert "tok-secret-123" not in (integ.credential_ciphertext or "")
    body = client.get(f"/api/v1/organizations/{org['id']}/integrations").get_data(as_text=True)
    assert "tok-secret-123" not in body and json.loads(body)["wordpress"]["connected"] is True


def test_oauth_state_cannot_be_forged_or_replayed(app, client, fake_wp):
    register_and_login(client)
    org = create_org(client)
    bad = client.get("/api/v1/integrations/wordpress/callback?code=good-code&state=forged")
    assert "wordpress=error" in bad.headers["Location"]
    state = _connect(client, org["id"])
    replay = client.get(f"/api/v1/integrations/wordpress/callback?code=good-code&state={state}")
    assert "wordpress=error" in replay.headers["Location"]  # nonce is single-use


def test_publish_once_and_verify_by_reading_back(app, client, fake_wp):
    org_id, _, did, aid = _setup(app, client, fake_wp)
    url = f"/api/v1/organizations/{org_id}/approvals/{aid}/publish/wordpress"
    r = client.post(url, json={"article_index": 0}, headers={"Idempotency-Key": "pub-1"})
    assert r.status_code == 202 and r.get_json()["external_action"]["status"] == "queued"
    # Same article again (new key) does not queue a second post.
    again = client.post(url, json={"article_index": 0}, headers={"Idempotency-Key": "pub-2"})
    assert again.get_json()["external_action"]["id"] == r.get_json()["external_action"]["id"]
    drain()
    pubs = client.get(f"/api/v1/organizations/{org_id}/deliverables/{did}/publications").get_json()["publications"]
    assert len(pubs) == 1 and pubs[0]["status"] == "succeeded"
    assert pubs[0]["publication_status"] == "platform_verified_published"
    assert pubs[0]["external_url"].startswith("https://fernleaf.wordpress.com/how-to-plant-autumn-bulbs-")
    post = next(iter(fake_wp.posts.values()))
    assert "<script>" not in post["content"] and "&lt;script&gt;" in post["content"]
    assert "<h2>Pick a sunny spot</h2>" in post["content"] and "<strong>Daffodils</strong>" in post["content"]
    assert len(fake_wp.posts) == 1


def test_retry_after_timeout_never_duplicates(app, client, fake_wp):
    org_id, _, did, aid = _setup(app, client, fake_wp)
    fake_wp.fail_next = [wp.WordPressError("timeout", retryable=True)]
    client.post(f"/api/v1/organizations/{org_id}/approvals/{aid}/publish/wordpress", json={"article_index": 0},
                headers={"Idempotency-Key": "pub-r"})
    drain()
    with app.app_context():
        a = ExternalAction.query.filter_by(idempotency_key="pub-r").one()
        assert a.status == "queued" and a.attempts == 1
        a.next_attempt_at = None
        db.session.commit()
    drain()
    assert len(fake_wp.posts) == 1


def test_draft_mode_is_not_reported_as_published(app, client, fake_wp):
    org_id, _, did, aid = _setup(app, client, fake_wp)
    client.post(f"/api/v1/organizations/{org_id}/approvals/{aid}/publish/wordpress",
                json={"article_index": 0, "mode": "draft"}, headers={"Idempotency-Key": "pub-d"})
    drain()
    pub = client.get(f"/api/v1/organizations/{org_id}/deliverables/{did}/publications").get_json()["publications"][0]
    assert pub["publication_status"] == "draft_created"


def test_edit_after_queueing_blocks_the_post(app, client, fake_wp):
    org_id, _, did, aid = _setup(app, client, fake_wp)
    client.post(f"/api/v1/organizations/{org_id}/approvals/{aid}/publish/wordpress", json={"article_index": 0},
                headers={"Idempotency-Key": "pub-e"})
    client.post(f"/api/v1/organizations/{org_id}/deliverables/{did}/versions",
                json={"content": {"keyword_themes": [], "blog_articles": [{**ARTICLE, "title": "Edited"}]}})
    drain()
    assert fake_wp.posts == {}
    with app.app_context():
        assert ExternalAction.query.filter_by(idempotency_key="pub-e").one().status == "failed"


def test_kill_switch_holds_the_post(app, client, fake_wp):
    org_id, _, did, aid = _setup(app, client, fake_wp)
    client.post(f"/api/v1/organizations/{org_id}/approvals/{aid}/publish/wordpress", json={"article_index": 0},
                headers={"Idempotency-Key": "pub-k"})
    with app.app_context():
        from app.models.organization import Organization

        db.session.get(Organization, org_id).kill_switch_enabled = True
        db.session.commit()
    drain()
    assert fake_wp.posts == {}
    with app.app_context():
        assert ExternalAction.query.filter_by(idempotency_key="pub-k").one().status == "queued"


def test_unapproved_or_unconnected_cannot_publish(app, client, fake_wp):
    register_and_login(client)
    org = create_org(client)
    camp = create_campaign(client, org["id"])
    did, aid = _approved_article(app, client, org["id"], camp["id"])
    r = client.post(f"/api/v1/organizations/{org['id']}/approvals/{aid}/publish/wordpress", json={"article_index": 0},
                    headers={"Idempotency-Key": "x1"})
    assert r.status_code == 409  # not connected
    _connect(client, org["id"])
    with app.app_context():
        d = create_deliverable_with_first_version(organization_id=org["id"], campaign_id=camp["id"], workflow_run_id=None,
                                                  deliverable_type="site_optimization_plan",
                                                  content={"keyword_themes": [], "blog_articles": [ARTICLE]})
        db.session.commit()
        did2 = d.id
    pending = client.post(f"/api/v1/organizations/{org['id']}/approvals", json={"deliverable_id": did2}).get_json()["approval"]
    r = client.post(f"/api/v1/organizations/{org['id']}/approvals/{pending['id']}/publish/wordpress",
                    json={"article_index": 0}, headers={"Idempotency-Key": "x2"})
    assert r.status_code == 409


def test_revoked_token_marks_connection_for_reauth(app, client, fake_wp):
    org_id, _, did, aid = _setup(app, client, fake_wp)
    fake_wp.fail_next = [wp.WordPressError("revoked", status=403)]
    client.post(f"/api/v1/organizations/{org_id}/approvals/{aid}/publish/wordpress", json={"article_index": 0},
                headers={"Idempotency-Key": "pub-a"})
    drain()
    st = client.get(f"/api/v1/organizations/{org_id}/integrations").get_json()["wordpress"]
    assert st["state"] == "reauth_required" and st["connected"] is False


def test_markdown_converter_escapes_everything():
    out = wp.markdown_to_html('## <img src=x onerror=alert(1)>\n\nHi **"there"** & <b>x</b>')
    assert "<img" not in out and "&lt;img" in out and "<strong>\"there\"</strong>" in out and "&amp;" in out


def test_unpublish_moves_post_to_trash_and_allows_republishing(app, client, fake_wp):
    org_id, _, did, aid = _setup(app, client, fake_wp)
    pub_url = f"/api/v1/organizations/{org_id}/approvals/{aid}/publish/wordpress"
    client.post(pub_url, json={"article_index": 0}, headers={"Idempotency-Key": "pub-u1"})
    drain()
    pub = client.get(f"/api/v1/organizations/{org_id}/deliverables/{did}/publications").get_json()["publications"][0]
    r = client.post(f"/api/v1/organizations/{org_id}/external-actions/{pub['id']}/unpublish")
    assert r.status_code == 200 and r.get_json()["external_action"]["publication_status"] == "removed_from_site"
    assert next(iter(fake_wp.posts.values()))["status"] == "trash"
    # Unpublishing twice is harmless; publishing again creates a fresh post.
    assert client.post(f"/api/v1/organizations/{org_id}/external-actions/{pub['id']}/unpublish").status_code == 200
    again = client.post(pub_url, json={"article_index": 0}, headers={"Idempotency-Key": "pub-u2"}).get_json()["external_action"]
    assert again["id"] != pub["id"] and again["status"] == "queued"
    drain()
    assert len(fake_wp.posts) == 2


def test_unpublish_works_with_kill_switch_on_and_needs_a_posted_article(app, client, fake_wp):
    org_id, _, did, aid = _setup(app, client, fake_wp)
    client.post(f"/api/v1/organizations/{org_id}/approvals/{aid}/publish/wordpress", json={"article_index": 0},
                headers={"Idempotency-Key": "pub-u3"})
    with app.app_context():
        queued = ExternalAction.query.filter_by(idempotency_key="pub-u3").one().id
    assert client.post(f"/api/v1/organizations/{org_id}/external-actions/{queued}/unpublish").status_code == 409
    drain()
    with app.app_context():
        from app.models.organization import Organization

        db.session.get(Organization, org_id).kill_switch_enabled = True
        db.session.commit()
    assert client.post(f"/api/v1/organizations/{org_id}/external-actions/{queued}/unpublish").status_code == 200
