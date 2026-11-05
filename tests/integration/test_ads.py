"""Ad launching: off until a cap is set, only from an approved plan, needs a
typed-budget approval, never exceeds the cap, and the kill switch, Stop all
and end dates halt spend on the (test) platform."""

from datetime import date, timedelta

from app.extensions import db
from app.models.ads import SandboxAdCampaign
from app.services.ads_service import process_ads
from app.services.deliverable_service import create_deliverable_with_first_version
from tests.conftest import create_campaign, create_org, register_and_login

PLAN = {"campaign_structure": [{"name": "Autumn bulbs — Instagram", "channel": "meta", "objective": "traffic", "audience": "Local gardeners"},
                               {"name": "Search — bulbs near me", "channel": "google_ads", "objective": "leads", "audience": "Bristol"}]}


def _plan(app, client, org_id, approve=True):
    camp = create_campaign(client, org_id)
    with app.app_context():
        d = create_deliverable_with_first_version(organization_id=org_id, campaign_id=camp["id"], workflow_run_id=None,
                                                  deliverable_type="paid_media_plan", content=PLAN)
        db.session.commit()
        did = d.id
    if approve:
        ap = client.post(f"/api/v1/organizations/{org_id}/approvals", json={"deliverable_id": did}).get_json()["approval"]
        client.post(f"/api/v1/organizations/{org_id}/approvals/{ap['id']}/decision", json={"decision": "approved"})
    return did


def _setup(app, client, cap=50):
    register_and_login(client)
    org = create_org(client)
    base = f"/api/v1/organizations/{org['id']}/ads"
    client.post(f"{base}/guardrail", json={"max_daily_budget": cap, "currency": "GBP"})
    return org["id"], base, _plan(app, client, org["id"])


def _request(client, base, did, budget=20, idx=0, end=None):
    return client.post(f"{base}/launches", json={"deliverable_id": did, "item_index": idx, "daily_budget": budget,
                                                 "end_date": end or (date.today() + timedelta(days=7)).isoformat()})


def _launch(app, client, base, did, budget=20):
    a = _request(client, base, did, budget).get_json()["launch"]
    client.post(f"{base}/launches/{a['id']}/decision", json={"decision": "approve", "confirm_daily_budget": budget})
    with app.app_context():
        process_ads()
    return a["id"]


def _status(client, base, lid):
    return next(x for x in client.get(base).get_json()["launches"] if x["id"] == lid)


def test_launching_is_off_until_a_cap_is_set(app, client):
    register_and_login(client)
    org = create_org(client)
    did = _plan(app, client, org["id"])
    r = _request(client, f"/api/v1/organizations/{org['id']}/ads", did)
    assert r.status_code == 409


def test_only_an_approved_current_plan_can_launch(app, client):
    org_id, base, did = _setup(app, client)
    unapproved = _plan(app, client, org_id, approve=False)
    assert _request(client, base, unapproved).status_code == 409
    assert _request(client, base, did).status_code == 201


def test_budget_must_fit_under_the_cap_across_all_ads(app, client):
    org_id, base, did = _setup(app, client, cap=50)
    assert _request(client, base, did, budget=60).status_code == 400
    assert _request(client, base, did, budget=30).status_code == 201
    r = _request(client, base, did, budget=30, idx=1)  # 30 + 30 > 50
    assert r.status_code == 400 and "20.00" in r.get_json()["error"]["details"][0]["issue"]


def test_approval_requires_retyping_the_budget_and_nothing_runs_before(app, client):
    org_id, base, did = _setup(app, client)
    a = _request(client, base, did, budget=20).get_json()["launch"]
    with app.app_context():
        process_ads()
        assert SandboxAdCampaign.query.count() == 0
    bad = client.post(f"{base}/launches/{a['id']}/decision", json={"decision": "approve", "confirm_daily_budget": 2000})
    assert bad.status_code == 400
    ok = client.post(f"{base}/launches/{a['id']}/decision", json={"decision": "approve", "confirm_daily_budget": "20"})
    assert ok.get_json()["launch"]["status"] == "approved"
    with app.app_context():
        process_ads()
        process_ads()  # idempotent: still one campaign on the platform
        assert SandboxAdCampaign.query.count() == 1
    assert _status(client, base, a["id"])["status"] == "active"


def test_kill_switch_pauses_live_ads(app, client):
    org_id, base, did = _setup(app, client)
    lid = _launch(app, client, base, did)
    with app.app_context():
        from app.models.organization import Organization

        db.session.get(Organization, org_id).kill_switch_enabled = True
        db.session.commit()
        process_ads()
        assert SandboxAdCampaign.query.one().status == "PAUSED"
    st = _status(client, base, lid)
    assert st["status"] == "paused" and st["stop_reason"] == "Kill switch is on"
    assert client.post(f"{base}/launches/{lid}/resume").status_code == 403


def test_stop_all_pauses_everything(app, client):
    org_id, base, did = _setup(app, client, cap=50)
    a1 = _launch(app, client, base, did, 20)
    client.post(f"{base}/stop-all")
    with app.app_context():
        process_ads()
        assert {c.status for c in SandboxAdCampaign.query} == {"PAUSED"}
    assert _status(client, base, a1)["status"] == "paused"


def test_workspace_cap_breach_pauses_all_ads(app, client):
    org_id, base, did = _setup(app, client, cap=20)
    lid = _launch(app, client, base, did, 20)
    app.config["ADS_SANDBOX_SPEED"] = 10_000_000  # a day of spend in an instant
    with app.app_context():
        from app.models.ads import AdLaunch, AdGuardrail

        AdGuardrail.query.one().max_daily_budget = 10  # an admin lowered the cap below today's spend
        AdLaunch.query.one().last_checked_at = None
        db.session.commit()
        process_ads()
    st = _status(client, base, lid)
    assert st["status"] == "paused" and st["stop_reason"] == "Workspace daily cap reached"


def test_end_date_stops_the_ad(app, client):
    org_id, base, did = _setup(app, client)
    lid = _launch(app, client, base, did)
    with app.app_context():
        from app.models.ads import AdLaunch

        from app.models.base import utcnow

        AdLaunch.query.one().end_date = utcnow().date() - timedelta(days=1)
        db.session.commit()
        process_ads()
        assert SandboxAdCampaign.query.one().status == "ARCHIVED"
    assert _status(client, base, lid)["stop_reason"] == "End date reached"


def test_plan_edit_before_launch_blocks_it(app, client):
    org_id, base, did = _setup(app, client)
    a = _request(client, base, did).get_json()["launch"]
    client.post(f"{base}/launches/{a['id']}/decision", json={"decision": "approve", "confirm_daily_budget": 20})
    client.post(f"/api/v1/organizations/{org_id}/deliverables/{did}/versions", json={"content": PLAN})
    with app.app_context():
        process_ads()
        assert SandboxAdCampaign.query.count() == 0
    assert _status(client, base, a["id"])["status"] == "failed"
