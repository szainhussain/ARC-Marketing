"""Exercises the full 5-stage pipeline succeeding, using a fake provider
in place of a live Anthropic call. This is the only way to test the
success path without real API credentials, and mirrors exactly how
start_campaign_workflow consumes an AIProvider."""

from app.ai.base import AIProvider, AIResult
from app.models.deliverable import Deliverable
from app.models.workflow_run import STATUS_COMPLETED, WorkflowRun
from app.models.usage_record import UsageRecord
from tests.conftest import complete_profile, create_campaign, create_org, register_and_login

FAKE_OUTPUTS = {
    "strategy": {
        "strategic_direction": "Position as the go-to weekend hiking brand.",
        "key_objectives": ["Increase awareness", "Drive trial purchases"],
        "assumptions": ["Audience is price-sensitive"],
        "sources": [],
    },
    "research_notes": {
        "audience_hypotheses": ["Weekend hikers value durability"],
        "competitor_notes": [],
        "assumptions": ["No external research tool connected"],
        "sources": [],
        "scope_note": "Based on user-provided context only.",
    },
    "campaign_plan": {
        "summary": "A four-week trail launch campaign.",
        "channels": ["email", "social"],
        "timeline": [{"week": 1, "focus": "teaser"}],
        "success_metrics": ["signups"],
        "assumptions": [],
    },
    "content_pack": {
        "creative_brief": "Highlight durability and comfort on long trails.",
        "variants": [{"channel": "email", "headline": "Hit the trail", "body": "Body copy"}],
        "calendar_notes": "Send Tuesday mornings.",
    },
    "qa_report": {
        "passed": True,
        "issues": [],
        "checked": ["schema", "brand constraints"],
    },
}


class FakeProvider(AIProvider):
    name = "fake"

    def generate_structured(self, task_type, input_data, output_schema, context=None,
                             budget_usd=1.0, timeout_seconds=60, correlation_id=None):
        schema = output_schema()
        validated = schema.load(FAKE_OUTPUTS[task_type])
        return AIResult(data=validated, provider="fake", model="fake-model",
                         input_tokens=10, output_tokens=20, estimated_cost_usd=0.001)


def test_full_pipeline_success_creates_all_deliverables(app, client, monkeypatch):
    monkeypatch.setattr(
        "app.workflows.campaign_workflow.get_provider", lambda config: FakeProvider()
    )

    register_and_login(client)
    org = create_org(client)
    complete_profile(client, org["id"])
    campaign = create_campaign(client, org["id"])

    resp = client.post(
        f"/api/v1/organizations/{org['id']}/campaigns/{campaign['id']}/runs",
        headers={"Idempotency-Key": "success-run-1"},
    )
    assert resp.status_code == 202
    run = resp.get_json()["workflow_run"]
    assert run["status"] == "completed"
    assert all(t["status"] == "completed" for t in run["tasks"])

    with app.app_context():
        from app.extensions import db

        stored_run = db.session.get(WorkflowRun, run["id"])
        assert stored_run.status == STATUS_COMPLETED
        assert stored_run.estimated_cost_usd > 0

        deliverables = Deliverable.query.filter_by(campaign_id=campaign["id"]).all()
        assert {d.deliverable_type for d in deliverables} == {
            "strategy", "research_notes", "campaign_plan", "content_pack", "qa_report",
        }
        for d in deliverables:
            assert d.current_version is not None

        usage_rows = UsageRecord.query.filter_by(workflow_run_id=run["id"]).all()
        assert len(usage_rows) == 5

    listing = client.get(f"/api/v1/organizations/{org['id']}/campaigns/{campaign['id']}/deliverables")
    assert listing.status_code == 200
    assert len(listing.get_json()["deliverables"]) == 5
