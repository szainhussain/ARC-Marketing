import pytest

from app import create_app
from app.extensions import db


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def register_and_login(client, email="owner@example.com", password="correct-horse-1"):
    resp = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test Owner"},
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["user"]


def create_org(client, name="Acme Co"):
    resp = client.post("/api/v1/organizations", json={"name": name})
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["organization"]


def complete_profile(client, organization_id):
    resp = client.patch(
        f"/api/v1/organizations/{organization_id}/business-profile",
        json={
            "business_name": "Acme Co",
            "industry": "Outdoor gear",
            "products_services": "Hiking backpacks",
            "target_audience": "Weekend hikers",
            "primary_goal": "Increase brand awareness",
        },
    )
    assert resp.status_code == 200, resp.get_json()
    return resp.get_json()["business_profile"]


def create_campaign(client, organization_id, name="Spring Launch"):
    resp = client.post(
        f"/api/v1/organizations/{organization_id}/campaigns",
        json={"name": name, "objective": "Launch the new backpack line"},
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["campaign"]
