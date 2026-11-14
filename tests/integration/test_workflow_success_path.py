"""Full 12-agent department run succeeding end to end through the real
API + worker code path, with a fake provider in place of a live model."""

from app.models.agent_execution import AgentExecution
from app.models.deliverable import Deliverable
from app.models.usage_record import UsageRecord
from app.models.workflow_run import STATUS_COMPLETED, WorkflowRun
from app.workflows.engine import drain
from tests.conftest import complete_profile, create_campaign, create_org, register_and_login
from tests.fakes import FakeProvider, use_provider


def _start(client, org_id, campaign_id, key="success-run-1"):
    resp = client.post(
        f"/api/v1/organizations/{org_id}/campaigns/{campaign_id}/runs",
        headers={"Idempotency-Key": key},
    )
    assert resp.status_code == 202, resp.get_json()
    return resp.get_json()["workflow_run"]


def test_start_run_only_enqueues(app, client, monkeypatch):
    provider = use_provider(monkeypatch, FakeProvider())
    register_and_login(client)
    org = create_org(client)
    complete_profile(client, org["id"])
    campaign = create_campaign(client, org["id"])

    run = _start(client, org["id"], campaign["id"])
    assert run["status"] == "queued"
    assert len(run["tasks"]) == 12
    ready = [t["agent_id"] for t in run["tasks"] if t["status"] == "ready"]
    assert ready == ["research_analyst"]  # research runs first (D23)
    assert provider.calls == []  # the web request never calls the model


def test_full_department_run_creates_twelve_deliverables(app, client, monkeypatch):
    provider = use_provider(monkeypatch, FakeProvider())
    register_and_login(client)
    org = create_org(client)
    complete_profile(client, org["id"])
    campaign = create_campaign(client, org["id"])
    run = _start(client, org["id"], campaign["id"])

    assert drain() == 12

    body = client.get(f"/api/v1/organizations/{org['id']}/runs/{run['id']}").get_json()["workflow_run"]
    assert body["status"] == "completed"
    assert all(t["status"] == "succeeded" for t in body["tasks"])
    assert all(t["deliverable_id"] for t in body["tasks"])

    from app.extensions import db

    stored = db.session.get(WorkflowRun, run["id"])
    assert stored.status == STATUS_COMPLETED
    deliverables = Deliverable.query.filter_by(workflow_run_id=run["id"]).all()
    assert len({d.deliverable_type for d in deliverables}) == 12
    assert UsageRecord.query.filter_by(workflow_run_id=run["id"]).count() == 12
    executions = AgentExecution.query.filter_by(workflow_run_id=run["id"]).all()
    from app.agents.registry import AGENTS_BY_ID

    # Every execution records the version of the agent that produced it.
    assert all(e.agent_version == AGENTS_BY_ID[e.agent_id].version for e in executions)

    # Dependency order respected: every agent ran after all its dependencies.
    order = [c["task_type"] for c in provider.calls]
    assert order.index("research_notes") < order.index("strategy") < order.index("campaign_plan")
    assert order.index("content_pack") < order.index("social_calendar")
    assert order.index("qa_report") < order.index("campaign_record")
    assert order[-1] == "campaign_record"


def test_agents_only_see_allowlisted_upstream_outputs(app, client, monkeypatch):
    provider = use_provider(monkeypatch, FakeProvider())
    register_and_login(client)
    org = create_org(client)
    complete_profile(client, org["id"])
    campaign = create_campaign(client, org["id"])
    _start(client, org["id"], campaign["id"])
    drain()

    by_type = {c["task_type"]: c for c in provider.calls}
    # Upstream outputs are never passed wholesale in context...
    assert all("upstream_outputs" not in (c["context"] or {}) for c in provider.calls)
    # ...and the key-accounts agent, which only reads marketing_manager,
    # never receives research or creative output.
    accounts_input = by_type["account_plan"]["input_data"]
    assert "campaign_plan" in accounts_input
    assert "audience" not in accounts_input and "creative_variants" not in accounts_input
    # The role is stated per agent.
    assert "Key Accounts" in by_type["account_plan"]["context"]["agent_role"]
