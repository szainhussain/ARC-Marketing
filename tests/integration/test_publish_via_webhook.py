"""Zapier/Make publishing: only approved, exported content is sent, it is the
exact approved version, and ARC still never marks anything as published."""

import json

from app.extensions import db
from app.models.billing import WebhookDelivery
from app.services.deliverable_service import create_deliverable_with_first_version
from tests.conftest import create_campaign, create_org, register_and_login

CONTENT = {"creative_brief": "Launch Trail 30", "variants": [
    {"channel": "instagram", "headline": "Built for the long way round", "body": "Light. Repairable. Ready."}],
    "calendar_notes": ""}


def test_approved_export_is_sent_to_automation_and_stays_unverified(app, client, monkeypatch):
    register_and_login(client)
    org = create_org(client)
    campaign = create_campaign(client, org["id"])
    base = f"/api/v1/organizations/{org['id']}"
    hook = client.post(f"{base}/webhooks", json={"url": "https://hooks.zapier.com/hooks/catch/1/abc/",
                                                 "events": ["content.approved_for_publishing"]})
    assert hook.status_code == 201, hook.get_json()
    with app.app_context():
        d = create_deliverable_with_first_version(organization_id=org["id"], campaign_id=campaign["id"],
                                                  workflow_run_id=None, deliverable_type="content_pack", content=CONTENT)
        db.session.commit()
        did = d.id

    approval = client.post(f"{base}/approvals", json={"deliverable_id": did}).get_json()["approval"]
    assert "connected automation" in approval["expected_outcome"]
    client.post(f"{base}/approvals/{approval['id']}/decision", json={"decision": "approved"})
    content_events = lambda: WebhookDelivery.query.filter_by(event_type="content.approved_for_publishing").all()  # noqa: E731
    with app.app_context():
        assert content_events() == []  # approval alone sends nothing

    resp = client.post(f"{base}/approvals/{approval['id']}/execute", headers={"Idempotency-Key": "pub-1"},
                       json={"target_platform": "meta_instagram"})
    assert resp.status_code in (200, 201), resp.get_json()
    action = resp.get_json()["external_action"]
    assert action["publication_status"] == "unverified"
    with app.app_context():
        (delivery,) = content_events()
        body = json.loads(delivery.payload_json)
        assert body["data"]["content"] == CONTENT
        assert body["data"]["target_platform"] == "meta_instagram" and body["data"]["platform_export"]
        assert body["data"]["campaign"]["name"] == campaign["name"]

    # Same idempotency key: no second send.
    client.post(f"{base}/approvals/{approval['id']}/execute", headers={"Idempotency-Key": "pub-1"},
                json={"target_platform": "meta_instagram"})
    with app.app_context():
        assert len(content_events()) == 1
