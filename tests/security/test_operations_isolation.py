"""Operations Center resources (tasks, runs, agents, executions, controls)
must not leak or be controllable across workspaces."""

from app.models.task import Task
from app.workflows.engine import drain
from tests.conftest import complete_profile, create_campaign, create_org, register_and_login
from tests.fakes import FakeProvider, use_provider


def test_operations_resources_are_tenant_isolated(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    register_and_login(client, email="ops-a@example.com")
    org_a = create_org(client, name="Ops A")
    complete_profile(client, org_a["id"])
    campaign = create_campaign(client, org_a["id"])
    run = client.post(
        f"/api/v1/organizations/{org_a['id']}/campaigns/{campaign['id']}/runs",
        headers={"Idempotency-Key": "iso-1"},
    ).get_json()["workflow_run"]
    drain()
    task_id = Task.query.filter_by(workflow_run_id=run["id"]).first().id
    client.post("/api/v1/auth/logout")

    register_and_login(client, email="ops-b@example.com")
    org_b = create_org(client, name="Ops B")
    a, b = org_a["id"], org_b["id"]

    # Direct access to org A's endpoints is denied.
    for method, url in [
        ("get", f"/api/v1/organizations/{a}/tasks"),
        ("get", f"/api/v1/organizations/{a}/agents"),
        ("get", f"/api/v1/organizations/{a}/agents/cmo"),
        ("get", f"/api/v1/organizations/{a}/operations/summary"),
        ("get", f"/api/v1/organizations/{a}/activity"),
        ("get", f"/api/v1/organizations/{a}/approvals"),
        ("get", f"/api/v1/organizations/{a}/tasks/{task_id}/executions"),
        ("post", f"/api/v1/organizations/{a}/tasks/{task_id}/retry"),
        ("post", f"/api/v1/organizations/{a}/runs/{run['id']}/pause"),
        ("post", f"/api/v1/organizations/{a}/agents/cmo/pause"),
        ("patch", f"/api/v1/organizations/{a}/operations/controls"),
    ]:
        assert getattr(client, method)(url, json={}).status_code == 403, url

    # Using org A's ids through org B's own path finds nothing.
    assert client.post(f"/api/v1/organizations/{b}/tasks/{task_id}/retry").status_code == 404
    assert client.post(f"/api/v1/organizations/{b}/runs/{run['id']}/pause").status_code == 404
    assert client.get(f"/api/v1/organizations/{b}/tasks/{task_id}/executions").get_json()["executions"] == []
    assert client.get(f"/api/v1/organizations/{b}/tasks").get_json()["tasks"] == []
    summary = client.get(f"/api/v1/organizations/{b}/operations/summary").get_json()
    assert summary["task_counts"] == {} and summary["latest_runs"] == []
