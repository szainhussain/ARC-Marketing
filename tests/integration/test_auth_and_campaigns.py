from tests.conftest import create_campaign, create_org, register_and_login


def test_register_requires_valid_fields(client):
    resp = client.post(
        "/api/v1/auth/register", json={"email": "not-an-email", "password": "short"}
    )
    assert resp.status_code == 400
    body = resp.get_json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    fields = {d["field"] for d in body["error"]["details"]}
    assert {"email", "password", "full_name"} <= fields


def test_login_failure_message_does_not_reveal_account_existence(client):
    register_and_login(client, email="exists@example.com")
    client.post("/api/v1/auth/logout")

    resp_no_account = client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong-pass-1"}
    )
    resp_wrong_password = client.post(
        "/api/v1/auth/login", json={"email": "exists@example.com", "password": "wrong-pass-1"}
    )
    assert resp_no_account.status_code == 401
    assert resp_wrong_password.status_code == 401
    assert (
        resp_no_account.get_json()["error"]["message"]
        == resp_wrong_password.get_json()["error"]["message"]
    )


def test_unauthenticated_requests_are_denied(client):
    resp = client.get("/api/v1/me")
    assert resp.status_code == 401


def test_campaign_crud_happy_path(client):
    register_and_login(client)
    org = create_org(client)
    campaign = create_campaign(client, org["id"])
    assert campaign["status"] == "draft"

    resp = client.get(f"/api/v1/organizations/{org['id']}/campaigns")
    assert resp.status_code == 200
    assert len(resp.get_json()["campaigns"]) == 1

    resp = client.patch(
        f"/api/v1/organizations/{org['id']}/campaigns/{campaign['id']}",
        json={"name": "Spring Launch v2"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["campaign"]["name"] == "Spring Launch v2"

    resp = client.delete(f"/api/v1/organizations/{org['id']}/campaigns/{campaign['id']}")
    assert resp.status_code == 200
    assert resp.get_json()["campaign"]["status"] == "archived"


def test_campaign_creation_requires_objective(client):
    register_and_login(client)
    org = create_org(client)
    resp = client.post(
        f"/api/v1/organizations/{org['id']}/campaigns", json={"name": "No objective"}
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"]["details"][0]["field"] == "objective"


def test_duplicate_idempotency_key_does_not_create_duplicate_campaign(client):
    register_and_login(client)
    org = create_org(client)
    payload = {
        "name": "Spring Launch",
        "objective": "Launch the new line",
        "idempotency_key": "fixed-key-123",
    }
    first = client.post(f"/api/v1/organizations/{org['id']}/campaigns", json=payload)
    second = client.post(f"/api/v1/organizations/{org['id']}/campaigns", json=payload)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.get_json()["campaign"]["id"] == second.get_json()["campaign"]["id"]

    listing = client.get(f"/api/v1/organizations/{org['id']}/campaigns")
    assert len(listing.get_json()["campaigns"]) == 1
