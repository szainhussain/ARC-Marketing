from tests.conftest import complete_profile, create_campaign, create_org, register_and_login


def test_checklist_reflects_real_progress_and_is_tenant_scoped(client):
    register_and_login(client, email="a@example.com")
    org = create_org(client)
    url = f"/api/v1/organizations/{org['id']}/onboarding-checklist"
    first = client.get(url).get_json()
    assert first["total"] == 9 and first["done"] == 0 and not first["complete"]

    complete_profile(client, org["id"])
    client.patch(f"/api/v1/organizations/{org['id']}/business-profile",
                 json={"tone_of_voice": "Warm and direct", "mark_onboarding_completed": True})
    create_campaign(client, org["id"])
    done = {i["key"] for i in client.get(url).get_json()["items"] if i["done"]}
    assert {"profile", "brand_voice", "campaign"} <= done and "run" not in done

    client.post("/api/v1/auth/logout")
    register_and_login(client, email="b@example.com")
    assert client.get(url).status_code in (403, 404)
