"""Website import fetches a user-supplied URL on the server, so it must never
reach private networks (SSRF), and only workspace members may use it."""

import socket

import pytest

from app.services import website_import as wi
from tests.conftest import create_org, register_and_login

SAMPLE = """<!doctype html><html lang="en-GB"><head>
<title>Trailhead Packs | Hiking backpacks for weekend explorers</title>
<meta name="description" content="Lightweight, repairable hiking backpacks made in Leeds.">
<meta property="og:site_name" content="Trailhead Packs">
<script>var x = "<h1>not a heading</h1>";</script></head>
<body><nav><h2>Menu</h2></nav><h1>Packs built for the long way round</h1>
<h2>Free repairs for life</h2><p>Every pack is hand-finished in our Leeds workshop and comes with free repairs for as long as you own it.</p>
</body></html>"""


@pytest.mark.parametrize("url", ["", "ftp://example.com", "https://user:pw@example.com", "https://example.com:8080/"])
def test_rejects_bad_urls(app, url):
    with app.app_context(), pytest.raises(wi.ImportFailed):
        wi.normalise_url(url)


def test_adds_https_when_missing(app):
    with app.app_context():
        assert wi.normalise_url("example.com/about#x") == "https://example.com/about"


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1", "100.64.0.1"])
def test_private_addresses_are_refused(app, monkeypatch, ip):
    family = socket.AF_INET6 if ":" in ip else socket.AF_INET
    monkeypatch.setattr(wi.socket, "getaddrinfo", lambda *a, **k: [(family, socket.SOCK_STREAM, 6, "", (ip, 443))])
    with app.app_context(), pytest.raises(wi.ImportFailed) as exc:
        wi.fetch_html("https://internal.example.com/")
    assert "private" in exc.value.details[0]["issue"]


def test_redirect_to_private_address_is_refused(app, monkeypatch):
    addrs = {"good.example.com": "93.184.216.34", "evil.example.com": "10.0.0.1"}
    monkeypatch.setattr(wi.socket, "getaddrinfo", lambda host, *a, **k: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (addrs[host], 443))])

    class Resp:
        status = 302

        def getheader(self, name, default=None):
            return "https://evil.example.com/" if name == "Location" else default

    connected = []

    class Conn:
        def __init__(self, host, ip, **kw):
            connected.append((host, ip))

        def request(self, *a, **k):
            pass

        def getresponse(self):
            return Resp()

        def close(self):
            pass

    monkeypatch.setattr(wi, "_PinnedHTTPSConnection", Conn)
    with app.app_context(), pytest.raises(wi.ImportFailed):
        wi.fetch_html("https://good.example.com/")
    assert connected == [("good.example.com", "93.184.216.34")]  # never connected to the private host


def test_extracts_profile_suggestions():
    out = wi.extract_profile(SAMPLE, "https://trailhead.example/home")
    assert out["suggested"] == {
        "business_name": "Trailhead Packs",
        "website": "https://trailhead.example",
        "business_description": "Lightweight, repairable hiking backpacks made in Leeds.",
        "language": "English",
    }
    assert out["found"]["headings"] == ["Packs built for the long way round", "Free repairs for life"]
    assert "Leeds workshop" in out["found"]["paragraphs"][0]


def test_route_needs_membership_and_saves_nothing(app, client, monkeypatch):
    monkeypatch.setattr(wi, "fetch_html", lambda url: (url, SAMPLE))
    from app.api.v1 import business_profile as bp

    monkeypatch.setattr(bp, "import_from_website", lambda url: wi.extract_profile(SAMPLE, wi.normalise_url(url)))
    register_and_login(client, email="a@example.com")
    org_a = create_org(client, name="A Co")
    resp = client.post(f"/api/v1/organizations/{org_a['id']}/business-profile/import-website", json={"url": "trailhead.example"})
    assert resp.status_code == 200 and resp.get_json()["suggested"]["business_name"] == "Trailhead Packs"
    profile = client.get(f"/api/v1/organizations/{org_a['id']}/business-profile").get_json()["business_profile"]
    assert profile["business_name"] in (None, "")  # suggestions are not saved automatically

    client.post("/api/v1/auth/logout")
    register_and_login(client, email="b@example.com")
    resp = client.post(f"/api/v1/organizations/{org_a['id']}/business-profile/import-website", json={"url": "trailhead.example"})
    assert resp.status_code in (403, 404)
