"""Workspace accent colour: admin-only, allowlisted, and exposed with the Brand Kit colour."""

from tests.conftest import create_org, register_and_login


def _ws(client, org_id):
    return client.get(f"/api/v1/organizations/{org_id}").get_json()["workspace"]


def test_admin_sets_preset_brand_and_reset(app, client):
    register_and_login(client)
    org = create_org(client)
    assert _ws(client, org["id"])["accent_color"] is None
    assert _ws(client, org["id"])["brand_accent"] is None

    r = client.patch(f"/api/v1/organizations/{org['id']}", json={"accent_color": "emerald"})
    assert r.status_code == 200 and r.get_json()["workspace"]["accent_color"] == "emerald"

    client.patch(f"/api/v1/organizations/{org['id']}/business-profile", json={"brand_colors": "#0a2540, #635bff"})
    r = client.patch(f"/api/v1/organizations/{org['id']}", json={"accent_color": "brand"})
    ws = r.get_json()["workspace"]
    assert ws["accent_color"] == "brand" and ws["brand_accent"] == "#0A2540"

    # "arc" (ARC's default) and empty both clear the setting.
    for reset in ("arc", None, ""):
        client.patch(f"/api/v1/organizations/{org['id']}", json={"accent_color": "rose"})
        assert client.patch(f"/api/v1/organizations/{org['id']}", json={"accent_color": reset}).get_json()["workspace"]["accent_color"] is None


def test_unknown_accent_is_rejected(app, client):
    register_and_login(client)
    org = create_org(client)
    for bad in ("#ff0000", "neon", "javascript:alert(1)", 7):
        r = client.patch(f"/api/v1/organizations/{org['id']}", json={"accent_color": bad})
        assert r.status_code == 400, bad
        assert r.get_json()["error"]["details"][0]["field"] == "accent_color"
    assert _ws(client, org["id"])["accent_color"] is None


def test_non_admin_cannot_change_workspace_accent(app, client):
    register_and_login(client)
    org = create_org(client)
    invite = client.post(f"/api/v1/organizations/{org['id']}/invitations",
                         json={"email": "mate@example.com", "role": "contributor"}).get_json()
    token = invite["invite_link"].split("token=")[1]
    client.post("/api/v1/auth/logout")
    register_and_login(client, email="mate@example.com")
    assert client.post("/api/v1/invitations/accept", json={"token": token}).status_code == 200

    assert client.patch(f"/api/v1/organizations/{org['id']}", json={"accent_color": "rose"}).status_code == 403
    assert _ws(client, org["id"])["accent_color"] is None  # members can still read it
