from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models.campaign import Campaign
from app.models.membership import Membership
from app.models.platform import Notification
from app.models.workflow_run import WorkflowRun
from app.services.recurrence_service import next_occurrence, run_due_recurrences
from tests.conftest import complete_profile, create_campaign, create_org, register_and_login


def test_next_occurrence_rolls_over_months_and_years():
    assert next_occurrence(5, datetime(2026, 11, 4, tzinfo=timezone.utc)) == datetime(2026, 11, 5, 9, tzinfo=timezone.utc)
    assert next_occurrence(5, datetime(2026, 11, 5, 10, tzinfo=timezone.utc)) == datetime(2026, 12, 5, 9, tzinfo=timezone.utc)
    assert next_occurrence(1, datetime(2026, 12, 20, tzinfo=timezone.utc)) == datetime(2027, 1, 1, 9, tzinfo=timezone.utc)


def test_monthly_campaign_starts_one_run_per_month(app, client):
    register_and_login(client)
    org = create_org(client)
    complete_profile(client, org["id"])
    camp = create_campaign(client, org["id"])
    url = f"/api/v1/organizations/{org['id']}/campaigns/{camp['id']}/recurrence"
    assert client.post(url, json={"recurrence": "monthly", "recurrence_day": 31}).status_code == 400
    body = client.post(url, json={"recurrence": "monthly", "recurrence_day": 3}).get_json()["campaign"]
    assert body["recurrence"] == "monthly" and body["next_run_at"]

    with app.app_context():
        c = db.session.get(Campaign, camp["id"])
        c.next_run_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()
        now = datetime.now(timezone.utc)
        assert run_due_recurrences(now) == 1
        assert WorkflowRun.query.filter_by(campaign_id=camp["id"]).count() == 1
        c = db.session.get(Campaign, camp["id"])
        nxt = c.next_run_at if c.next_run_at.tzinfo else c.next_run_at.replace(tzinfo=timezone.utc)
        assert nxt > now
        # Forcing it due again in the same month does not start a second run.
        c.next_run_at = now - timedelta(minutes=1)
        db.session.commit()
        run_due_recurrences(now)
        assert WorkflowRun.query.filter_by(campaign_id=camp["id"]).count() == 1
        assert Notification.query.filter_by(organization_id=org["id"], kind="campaign.recurring_run").count() >= 1

    assert client.post(url, json={"recurrence": "none"}).get_json()["campaign"]["next_run_at"] is None


def test_limit_reached_notifies_instead_of_crashing_and_archived_are_skipped(app, client, monkeypatch):
    register_and_login(client)
    org = create_org(client)
    complete_profile(client, org["id"])
    camp = create_campaign(client, org["id"])
    other = create_campaign(client, org["id"], name="Old")
    for cid in (camp["id"], other["id"]):
        client.post(f"/api/v1/organizations/{org['id']}/campaigns/{cid}/recurrence", json={"recurrence": "monthly", "recurrence_day": 1})
    from app.services import platform_service
    from app.services.errors import PermissionDenied

    def over_limit(org_id, key):
        raise PermissionDenied("Your plan's monthly run limit is reached.")

    monkeypatch.setattr("app.workflows.engine.check_entitlement", over_limit)
    with app.app_context():
        db.session.get(Campaign, other["id"]).status = "archived"
        for cid in (camp["id"], other["id"]):
            db.session.get(Campaign, cid).next_run_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.session.commit()
        assert run_due_recurrences() == 0
        assert WorkflowRun.query.filter_by(organization_id=org["id"]).count() == 0
        blocked = Notification.query.filter_by(organization_id=org["id"], kind="campaign.recurring_run_blocked").all()
        assert len(blocked) == 1 and "limit" in blocked[0].body
    assert platform_service  # imported for monkeypatch path clarity


def test_only_operators_set_recurrence(app, client):
    register_and_login(client)
    org = create_org(client)
    camp = create_campaign(client, org["id"])
    with app.app_context():
        Membership.query.filter_by(organization_id=org["id"]).first().role = "viewer"
        db.session.commit()
    resp = client.post(f"/api/v1/organizations/{org['id']}/campaigns/{camp['id']}/recurrence",
                      json={"recurrence": "monthly", "recurrence_day": 1})
    assert resp.status_code == 403
