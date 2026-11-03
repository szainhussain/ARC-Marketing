"""Exercises the review -> edit -> version -> approval -> manual handoff
path end-to-end, without depending on a live AI provider (deliverables are
created directly through the service layer, the same way the workflow
orchestrator creates them after a successful AI stage)."""

from app.extensions import db
from app.services.deliverable_service import create_deliverable_with_first_version
from tests.conftest import create_campaign, create_org, register_and_login


def _create_test_deliverable(app, organization_id, campaign_id):
    with app.app_context():
        deliverable = create_deliverable_with_first_version(
            organization_id=organization_id,
            campaign_id=campaign_id,
            workflow_run_id=None,
            deliverable_type="content_pack",
            content={"creative_brief": "v1 brief", "variants": [], "calendar_notes": ""},
        )
        db.session.commit()
        return deliverable.id


def test_editing_creates_new_version_and_invalidates_pending_approval(app, client):
    register_and_login(client)
    org = create_org(client)
    campaign = create_campaign(client, org["id"])
    deliverable_id = _create_test_deliverable(app, org["id"], campaign["id"])

    resp = client.post(
        f"/api/v1/organizations/{org['id']}/approvals",
        json={"deliverable_id": deliverable_id},
    )
    assert resp.status_code == 201
    approval = resp.get_json()["approval"]
    assert approval["decision"] == "pending"

    resp = client.post(
        f"/api/v1/organizations/{org['id']}/deliverables/{deliverable_id}/versions",
        json={"content": {"creative_brief": "v2 brief", "variants": [], "calendar_notes": ""}},
    )
    assert resp.status_code == 201
    assert len(resp.get_json()["deliverable"]["versions"]) == 2

    with app.app_context():
        from app.extensions import db
        from app.models.approval import Approval

        refreshed = db.session.get(Approval, approval["id"])
        assert refreshed.decision == "invalidated"


def test_approval_then_manual_handoff_reports_handed_off_not_published(app, client):
    register_and_login(client)
    org = create_org(client)
    campaign = create_campaign(client, org["id"])
    deliverable_id = _create_test_deliverable(app, org["id"], campaign["id"])

    approval = client.post(
        f"/api/v1/organizations/{org['id']}/approvals",
        json={"deliverable_id": deliverable_id},
    ).get_json()["approval"]

    decided = client.post(
        f"/api/v1/organizations/{org['id']}/approvals/{approval['id']}/decision",
        json={"decision": "approved"},
    )
    assert decided.status_code == 200
    assert decided.get_json()["approval"]["decision"] == "approved"

    executed = client.post(
        f"/api/v1/organizations/{org['id']}/approvals/{approval['id']}/execute",
        headers={"Idempotency-Key": "handoff-1"},
    )
    assert executed.status_code == 200
    action = executed.get_json()["external_action"]
    assert action["status"] == "succeeded"
    # Must never claim "published" just because it was exported.
    assert action["publication_status"] == "unverified"

    confirmed = client.post(
        f"/api/v1/organizations/{org['id']}/external-actions/{action['id']}/confirm-publication"
    )
    assert confirmed.status_code == 200
    assert confirmed.get_json()["external_action"]["publication_status"] == (
        "manually_confirmed_published"
    )


def test_rejected_approval_cannot_execute(app, client):
    register_and_login(client)
    org = create_org(client)
    campaign = create_campaign(client, org["id"])
    deliverable_id = _create_test_deliverable(app, org["id"], campaign["id"])

    approval = client.post(
        f"/api/v1/organizations/{org['id']}/approvals",
        json={"deliverable_id": deliverable_id},
    ).get_json()["approval"]
    client.post(
        f"/api/v1/organizations/{org['id']}/approvals/{approval['id']}/decision",
        json={"decision": "rejected"},
    )

    executed = client.post(
        f"/api/v1/organizations/{org['id']}/approvals/{approval['id']}/execute",
        headers={"Idempotency-Key": "handoff-rejected"},
    )
    assert executed.status_code == 409


def test_duplicate_idempotency_key_does_not_execute_twice(app, client):
    register_and_login(client)
    org = create_org(client)
    campaign = create_campaign(client, org["id"])
    deliverable_id = _create_test_deliverable(app, org["id"], campaign["id"])

    approval = client.post(
        f"/api/v1/organizations/{org['id']}/approvals",
        json={"deliverable_id": deliverable_id},
    ).get_json()["approval"]
    client.post(
        f"/api/v1/organizations/{org['id']}/approvals/{approval['id']}/decision",
        json={"decision": "approved"},
    )

    first = client.post(
        f"/api/v1/organizations/{org['id']}/approvals/{approval['id']}/execute",
        headers={"Idempotency-Key": "same-handoff-key"},
    )
    second = client.post(
        f"/api/v1/organizations/{org['id']}/approvals/{approval['id']}/execute",
        headers={"Idempotency-Key": "same-handoff-key"},
    )
    assert first.get_json()["external_action"]["id"] == second.get_json()["external_action"]["id"]


def test_execute_with_target_platform_returns_formatted_export(app, client):
    register_and_login(client)
    org = create_org(client)
    campaign = create_campaign(client, org["id"])

    with app.app_context():
        deliverable = create_deliverable_with_first_version(
            organization_id=org["id"],
            campaign_id=campaign["id"],
            workflow_run_id=None,
            deliverable_type="content_pack",
            content={
                "creative_brief": "Launch brief",
                "variants": [
                    {
                        "channel": "instagram",
                        "headline": "A headline that is definitely longer than thirty characters",
                        "body": "Short body copy.",
                        "cta": "Shop now",
                    }
                ],
                "calendar_notes": "",
            },
        )
        db.session.commit()
        deliverable_id = deliverable.id

    approval = client.post(
        f"/api/v1/organizations/{org['id']}/approvals",
        json={"deliverable_id": deliverable_id},
    ).get_json()["approval"]
    client.post(
        f"/api/v1/organizations/{org['id']}/approvals/{approval['id']}/decision",
        json={"decision": "approved"},
    )

    resp = client.post(
        f"/api/v1/organizations/{org['id']}/approvals/{approval['id']}/execute",
        headers={"Idempotency-Key": "platform-export-1"},
        json={"target_platform": "google_ads"},
    )
    assert resp.status_code == 200
    action = resp.get_json()["external_action"]
    assert action["target_platform"] == "google_ads"

    export = action["platform_export"]
    assert export["platform"] == "google_ads"
    headline_field = export["variant_exports"][0]["fields"][0]
    assert headline_field["label"] == "Headline 1"
    assert headline_field["length"] <= 30
    assert headline_field["fits"] is True


def test_execute_with_unknown_platform_rejected(app, client):
    register_and_login(client)
    org = create_org(client)
    campaign = create_campaign(client, org["id"])

    with app.app_context():
        deliverable = create_deliverable_with_first_version(
            organization_id=org["id"],
            campaign_id=campaign["id"],
            workflow_run_id=None,
            deliverable_type="content_pack",
            content={"creative_brief": "b", "variants": [], "calendar_notes": ""},
        )
        db.session.commit()
        deliverable_id = deliverable.id

    approval = client.post(
        f"/api/v1/organizations/{org['id']}/approvals",
        json={"deliverable_id": deliverable_id},
    ).get_json()["approval"]
    client.post(
        f"/api/v1/organizations/{org['id']}/approvals/{approval['id']}/decision",
        json={"decision": "approved"},
    )

    resp = client.post(
        f"/api/v1/organizations/{org['id']}/approvals/{approval['id']}/execute",
        headers={"Idempotency-Key": "platform-export-bad"},
        json={"target_platform": "snapchat_ads"},
    )
    assert resp.status_code == 400
