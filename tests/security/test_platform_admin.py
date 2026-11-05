"""The platform-owner inbox holds every visitor's contact details, so only
emails in PLATFORM_ADMIN_EMAILS may read it — not even workspace owners."""

from tests.conftest import create_org, register_and_login


def _submit_demo(client, email="lead@example.com"):
    return client.post("/api/v1/public/contact", json={
        "name": "Lead", "email": email, "company": "Lead Co", "topic": "demo",
        "message": "Demo request\nTeam size: 6-20"})


def test_demo_topic_accepted(client):
    assert _submit_demo(client).status_code == 201


def test_non_admins_cannot_read_or_change_enquiries(app, client):
    app.config["PLATFORM_ADMIN_EMAILS"] = {"founder@example.com"}
    _submit_demo(client)
    assert client.get("/api/v1/admin/enquiries").status_code == 401  # signed out
    register_and_login(client, email="owner@example.com")
    create_org(client)  # a workspace owner is still not a platform admin
    assert client.get("/api/v1/admin/enquiries").status_code == 403
    assert client.get("/api/v1/admin/overview").status_code == 403
    assert client.patch("/api/v1/admin/enquiries/anything", json={"status": "closed"}).status_code == 403
    assert client.get("/api/v1/me").get_json()["user"]["is_platform_admin"] is False


def test_admin_sees_and_updates_enquiries(app, client):
    app.config["PLATFORM_ADMIN_EMAILS"] = {"founder@example.com"}
    _submit_demo(client)
    register_and_login(client, email="Founder@Example.com")
    assert client.get("/api/v1/me").get_json()["user"]["is_platform_admin"] is True
    data = client.get("/api/v1/admin/enquiries").get_json()
    assert data["counts"]["new"] == 1 and data["enquiries"][0]["topic"] == "demo"
    eid = data["enquiries"][0]["id"]
    assert client.patch(f"/api/v1/admin/enquiries/{eid}", json={"status": "bogus"}).status_code == 400
    assert client.patch(f"/api/v1/admin/enquiries/{eid}", json={"status": "contacted"}).get_json()["enquiry"]["status"] == "contacted"
    assert client.get("/api/v1/admin/enquiries?status=new").get_json()["enquiries"] == []
    overview = client.get("/api/v1/admin/overview").get_json()
    assert overview["users"]["total"] == 1 and overview["new_enquiries"] == 0
