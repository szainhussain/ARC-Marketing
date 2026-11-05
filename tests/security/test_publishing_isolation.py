"""Another workspace can never connect, read, publish to or disconnect a
workspace's WordPress site, nor hijack its OAuth state."""

from urllib.parse import parse_qs, urlparse

from tests.conftest import create_org, register_and_login
from tests.integration.test_wordpress_publishing import FakeWP  # noqa: F401
from tests.integration.test_wordpress_publishing import fake_wp  # noqa: F401  (fixture)


def test_other_workspace_is_denied_everything(app, client, fake_wp):
    register_and_login(client)
    org_a = create_org(client, name="A")
    r = client.post(f"/api/v1/organizations/{org_a['id']}/integrations/wordpress/connect")
    state_a = parse_qs(urlparse(r.get_json()["authorize_url"]).query)["state"][0]
    client.post("/api/v1/auth/logout")

    register_and_login(client, email="intruder@example.com")
    create_org(client, name="B")
    base = f"/api/v1/organizations/{org_a['id']}"
    assert client.get(f"{base}/integrations").status_code == 403
    assert client.post(f"{base}/integrations/wordpress/connect").status_code == 403
    assert client.delete(f"{base}/integrations/wordpress").status_code == 403
    assert client.post(f"{base}/approvals/x/publish/wordpress", json={}, headers={"Idempotency-Key": "k"}).status_code == 403
    assert client.get(f"{base}/deliverables/x/publications").status_code == 403
    # A's signed state is useless in B's session.
    cb = client.get(f"/api/v1/integrations/wordpress/callback?code=good-code&state={state_a}")
    assert "wordpress=error" in cb.headers["Location"]
    assert not [c for c in fake_wp.calls if c[1].endswith("/oauth2/token")]
