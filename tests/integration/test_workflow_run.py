from app.workflows.engine import drain
from tests.conftest import complete_profile, create_campaign, create_org, register_and_login


def test_run_needs_input_when_business_profile_incomplete(client):
    register_and_login(client)
    org = create_org(client)
    campaign = create_campaign(client, org["id"])

    resp = client.post(
        f"/api/v1/organizations/{org['id']}/campaigns/{campaign['id']}/runs",
        headers={"Idempotency-Key": "run-1"},
    )
    assert resp.status_code == 202
    run = resp.get_json()["workflow_run"]
    assert run["status"] == "needs_input"
    assert "business profile" in run["error_summary"].lower()


def test_run_reports_capability_unavailable_without_ai_key(app, client, monkeypatch):
    from app.ai.provider_adapter import NullProvider

    monkeypatch.setattr("app.workflows.engine.get_provider", lambda config: NullProvider())
    register_and_login(client)
    org = create_org(client)
    complete_profile(client, org["id"])
    campaign = create_campaign(client, org["id"])

    resp = client.post(
        f"/api/v1/organizations/{org['id']}/campaigns/{campaign['id']}/runs",
        headers={"Idempotency-Key": "run-2"},
    )
    assert resp.status_code == 202
    run_id = resp.get_json()["workflow_run"]["id"]
    drain()
    run = client.get(f"/api/v1/organizations/{org['id']}/runs/{run_id}").get_json()["workflow_run"]
    assert run["status"] == "failed"
    assert "capability_unavailable" in run["error_summary"] or any(
        "capability_unavailable" in (t.get("error_summary") or "") for t in run["tasks"]
    )
    # The failure must be on the first agent, with no retry and no output.
    first_task = run["tasks"][0]
    assert first_task["agent_id"] == "cmo"
    assert first_task["attempt_count"] == 1
    assert "capability_unavailable" in first_task["error_summary"]
    assert first_task["deliverable_id"] is None


def test_duplicate_idempotency_key_returns_same_run(client):
    register_and_login(client)
    org = create_org(client)
    complete_profile(client, org["id"])
    campaign = create_campaign(client, org["id"])

    first = client.post(
        f"/api/v1/organizations/{org['id']}/campaigns/{campaign['id']}/runs",
        headers={"Idempotency-Key": "same-key"},
    )
    second = client.post(
        f"/api/v1/organizations/{org['id']}/campaigns/{campaign['id']}/runs",
        headers={"Idempotency-Key": "same-key"},
    )
    assert first.get_json()["workflow_run"]["id"] == second.get_json()["workflow_run"]["id"]


def test_missing_idempotency_key_rejected(client):
    register_and_login(client)
    org = create_org(client)
    complete_profile(client, org["id"])
    campaign = create_campaign(client, org["id"])

    resp = client.post(f"/api/v1/organizations/{org['id']}/campaigns/{campaign['id']}/runs")
    assert resp.status_code == 400
