from datetime import timedelta

from app.ai.errors import InvalidOutput, ProviderUnavailable, RateLimited
from app.extensions import db
from app.models.agent_execution import AgentExecution
from app.models.base import utcnow
from app.models.task import Task
from app.models.workflow_run import WorkflowRun
from app.workflows.engine import claim_next_task, drain, recover_expired_leases, work_once
from tests.conftest import complete_profile, create_campaign, create_org, register_and_login
from tests.fakes import FakeProvider, use_provider


def _setup(client, key="run-1"):
    register_and_login(client)
    org = create_org(client)
    complete_profile(client, org["id"])
    campaign = create_campaign(client, org["id"])
    resp = client.post(
        f"/api/v1/organizations/{org['id']}/campaigns/{campaign['id']}/runs",
        headers={"Idempotency-Key": key},
    )
    assert resp.status_code == 202
    return org, resp.get_json()["workflow_run"]


def _task(run_id, agent_id) -> Task:
    return Task.query.filter_by(workflow_run_id=run_id, agent_id=agent_id).one()


def test_rate_limited_task_retries_then_succeeds(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider(fail_for={"strategy": [RateLimited("429", 0)]}))
    _org, run = _setup(client)
    drain()
    cmo = _task(run["id"], "cmo")
    assert cmo.status == "succeeded"
    assert cmo.attempt_count == 1  # rate limits don't use up attempts
    execs = AgentExecution.query.filter_by(task_id=cmo.id).order_by(AgentExecution.attempt_number).all()
    assert [e.status for e in execs] == ["failed", "succeeded"]
    assert execs[0].error_code == "rate_limited"
    # Raw provider text (account ids, JSON) never reaches users.
    assert "429" not in execs[0].error_summary
    assert db.session.get(WorkflowRun, run["id"]).status == "completed"


def test_rate_limits_do_not_exhaust_attempts(app, client, monkeypatch):
    # More rate limits than max_attempts (5), then success.
    use_provider(monkeypatch, FakeProvider(fail_for={"strategy": [RateLimited("429", 0)] * 8}))
    _org, run = _setup(client)
    drain()
    cmo = _task(run["id"], "cmo")
    assert cmo.status == "succeeded"
    assert AgentExecution.query.filter_by(task_id=cmo.id, error_code="rate_limited").count() == 8


def test_persistent_rate_limit_eventually_fails(app, client, monkeypatch):
    from app.workflows.engine import MAX_CONSECUTIVE_RATE_LIMITS

    use_provider(monkeypatch, FakeProvider(fail_for={"strategy": [RateLimited("429", 0)] * 50}))
    _org, run = _setup(client)
    drain()
    cmo = _task(run["id"], "cmo")
    assert cmo.status == "failed"
    assert AgentExecution.query.filter_by(task_id=cmo.id).count() == MAX_CONSECUTIVE_RATE_LIMITS


def test_retry_after_pauses_the_worker(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider(fail_for={"strategy": [RateLimited("429", 30)]}))
    _setup(client)
    assert work_once() is True
    # Cooldown: the worker claims nothing, even if other tasks were ready.
    assert work_once() is False


def test_retry_after_from_provider_delays_next_attempt(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider(fail_for={"strategy": [RateLimited("429", 30)]}))
    _org, run = _setup(client)
    assert work_once() is True
    cmo = _task(run["id"], "cmo")
    assert cmo.status == "retrying"
    assert cmo.next_attempt_at is not None
    # Not claimable until the provider's retry-after has passed.
    assert claim_next_task() is None
    assert claim_next_task(now=utcnow() + timedelta(seconds=60)) is not None


def test_retries_stop_at_max_attempts(app, client, monkeypatch):
    errors = [InvalidOutput("bad json")] * 10
    use_provider(monkeypatch, FakeProvider(fail_for={"strategy": errors}))
    _org, run = _setup(client)
    drain()
    cmo = _task(run["id"], "cmo")
    assert cmo.status == "failed"
    assert cmo.attempt_count == cmo.max_attempts == 5
    stored = db.session.get(WorkflowRun, run["id"])
    assert stored.status == "failed"
    # Dependents never ran and are still waiting, not silently skipped.
    assert _task(run["id"], "research_analyst").status == "waiting_for_dependency"


def test_provider_unavailable_fails_without_retry(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider(fail_for={"strategy": [ProviderUnavailable("no key")]}))
    _org, run = _setup(client)
    drain()
    cmo = _task(run["id"], "cmo")
    assert cmo.status == "failed"
    assert cmo.attempt_count == 1
    assert cmo.error_summary.startswith("capability_unavailable:")
    assert db.session.get(WorkflowRun, run["id"]).error_summary.startswith("capability_unavailable:")


def test_manual_retry_reopens_failed_run(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider(fail_for={"strategy": [ProviderUnavailable("no key")]}))
    org, run = _setup(client)
    drain()
    cmo = _task(run["id"], "cmo")
    resp = client.post(f"/api/v1/organizations/{org['id']}/tasks/{cmo.id}/retry")
    assert resp.status_code == 200, resp.get_json()
    assert resp.get_json()["task"]["status"] == "ready"
    drain()
    assert db.session.get(WorkflowRun, run["id"]).status == "completed"


def test_independent_branch_continues_after_sibling_fails(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider(fail_for={"social_calendar": [ProviderUnavailable("x")]}))
    _org, run = _setup(client)
    drain()
    assert _task(run["id"], "social_media").status == "failed"
    for agent in ("paid_media", "seo_growth", "pr_partnerships", "customer_insights", "key_accounts"):
        assert _task(run["id"], agent).status == "succeeded"
    assert _task(run["id"], "marketing_ops").status == "waiting_for_dependency"
    assert db.session.get(WorkflowRun, run["id"]).status == "failed"


def test_paused_agent_is_skipped_until_resumed(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    org, run = _setup(client)
    assert client.post(f"/api/v1/organizations/{org['id']}/agents/cmo/pause").status_code == 200
    assert drain() == 0
    assert _task(run["id"], "cmo").status == "ready"
    agents = client.get(f"/api/v1/organizations/{org['id']}/agents").get_json()["agents"]
    assert next(a for a in agents if a["agent_id"] == "cmo")["status"] == "paused"

    client.post(f"/api/v1/organizations/{org['id']}/agents/cmo/resume")
    assert drain() == 12


def test_workspace_automation_pause_stops_all_work(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    org, run = _setup(client)
    resp = client.patch(f"/api/v1/organizations/{org['id']}/operations/controls",
                        json={"automation_paused": True})
    assert resp.status_code == 200
    assert drain() == 0
    client.patch(f"/api/v1/organizations/{org['id']}/operations/controls",
                 json={"automation_paused": False})
    assert drain() == 12


def test_pause_and_resume_run(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    org, run = _setup(client)
    work_once()  # cmo
    resp = client.post(f"/api/v1/organizations/{org['id']}/runs/{run['id']}/pause")
    assert resp.get_json()["workflow_run"]["status"] == "paused"
    assert drain() == 0
    resp = client.post(f"/api/v1/organizations/{org['id']}/runs/{run['id']}/resume")
    assert resp.get_json()["workflow_run"]["status"] == "running"
    assert drain() == 11
    assert db.session.get(WorkflowRun, run["id"]).status == "completed"


def test_cancelled_run_discards_and_stops(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    org, run = _setup(client)
    work_once()
    resp = client.post(f"/api/v1/organizations/{org['id']}/runs/{run['id']}/cancel")
    assert resp.get_json()["workflow_run"]["status"] == "cancelled"
    assert drain() == 0
    statuses = {t.status for t in Task.query.filter_by(workflow_run_id=run["id"])}
    assert statuses == {"succeeded", "cancelled"}


def test_expired_lease_is_recovered(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    _org, run = _setup(client)
    task = claim_next_task()  # simulate a worker that claims and then dies
    assert task.status == "running"
    assert recover_expired_leases() == 0  # lease still valid
    assert recover_expired_leases(now=utcnow() + timedelta(hours=1)) == 1
    db.session.refresh(task)
    assert task.status == "retrying"
    assert drain() == 12
    assert db.session.get(WorkflowRun, run["id"]).status == "completed"


def test_task_cannot_be_claimed_twice(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    _setup(client)
    first = claim_next_task()
    assert first is not None and first.agent_id == "cmo"
    # cmo is the only ready task and it's already claimed.
    assert claim_next_task() is None


def test_run_budget_exhaustion_fails_without_calling_model(app, client, monkeypatch):
    provider = use_provider(monkeypatch, FakeProvider())
    _org, run = _setup(client)
    stored = db.session.get(WorkflowRun, run["id"])
    stored.budget_usd = 0.0
    db.session.commit()
    drain()
    cmo = _task(run["id"], "cmo")
    assert cmo.status == "failed" and cmo.last_error_code == "budget_exceeded"
    assert provider.calls == []


def test_evaluation_flags_contact_details_and_feeds_qa(app, client, monkeypatch):
    bad_outreach = {
        "target_profiles": [{"target_type": "journalist", "fit_criteria": "x", "why_relevant": "y"}],
        "outreach_drafts": [{"target_type": "journalist", "channel": "email",
                             "message": "Email jane.doe@example.com today"}],
    }
    provider = use_provider(monkeypatch, FakeProvider(overrides={"outreach_plan": bad_outreach}))
    _org, run = _setup(client)
    drain()
    pr_exec = AgentExecution.query.filter_by(workflow_run_id=run["id"], agent_id="pr_partnerships").one()
    assert "no_contact_details" in pr_exec.summary
    qa_call = next(c for c in provider.calls if c["task_type"] == "qa_report")
    flags = qa_call["input_data"]["automated_evaluation_flags"]
    assert any(f["check"] == "no_contact_details" and f["agent_id"] == "pr_partnerships" for f in flags)


def test_viewer_cannot_control_runs(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    org, run = _setup(client)
    from app.models.membership import Membership

    membership = Membership.query.filter_by(organization_id=org["id"]).one()
    membership.role = "viewer"
    db.session.commit()
    assert client.post(f"/api/v1/organizations/{org['id']}/runs/{run['id']}/pause").status_code == 403
    assert client.post(f"/api/v1/organizations/{org['id']}/agents/cmo/pause").status_code == 403
    assert client.patch(f"/api/v1/organizations/{org['id']}/operations/controls",
                        json={"automation_paused": True}).status_code == 403
