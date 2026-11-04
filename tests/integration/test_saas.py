import io
import json
from datetime import timedelta

from app.billing.providers import sign_payload
from app.extensions import db
from app.models.base import utcnow
from app.models.billing import BillingEvent, WebhookDelivery
from app.models.membership import Membership
from app.models.platform import KnowledgeEntry, Notification
from app.workflows.engine import drain
from tests.conftest import complete_profile, create_campaign, create_org, register_and_login
from tests.fakes import FakeProvider, use_provider

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def _org(client, email="owner@example.com"):
    register_and_login(client, email=email)
    org = create_org(client)
    complete_profile(client, org["id"])
    return org


def _run(client, org_id, key="k1"):
    campaign = create_campaign(client, org_id)
    resp = client.post(f"/api/v1/organizations/{org_id}/campaigns/{campaign['id']}/runs",
                       headers={"Idempotency-Key": key})
    assert resp.status_code == 202, resp.get_json()
    return campaign, resp.get_json()["workflow_run"]


# ---- Billing ----------------------------------------------------------------

def test_public_plans_are_provisional(client):
    body = client.get("/api/v1/public/plans").get_json()
    assert [p["code"] for p in body["plans"]] == ["launch", "growth", "scale", "enterprise"]
    assert all(p["price_is_provisional"] for p in body["plans"])


def test_test_mode_checkout_changes_plan_only_via_signed_webhook(app, client):
    org = _org(client)
    billing = client.get(f"/api/v1/organizations/{org['id']}/billing").get_json()
    assert billing["subscription"]["plan"]["code"] == "launch"
    assert billing["subscription"]["status"] == "trialing"

    checkout = client.post(f"/api/v1/organizations/{org['id']}/billing/checkout",
                           json={"plan_code": "growth"}).get_json()["checkout"]
    assert checkout["mode"] == "test"
    # Starting checkout alone changes nothing.
    assert client.get(f"/api/v1/organizations/{org['id']}/billing").get_json()["subscription"]["plan"]["code"] == "launch"

    result = client.post(f"/api/v1/organizations/{org['id']}/billing/test-complete",
                         json={"plan_code": "growth", "session_id": checkout["session_id"]}).get_json()
    assert result["status"] == "subscription_activated"
    sub = client.get(f"/api/v1/organizations/{org['id']}/billing").get_json()["subscription"]
    assert sub["plan"]["code"] == "growth" and sub["status"] == "active"
    history = client.get(f"/api/v1/organizations/{org['id']}/billing/history").get_json()["events"]
    assert history[0]["is_test"] is True


def test_billing_webhook_rejects_bad_signature_and_dedupes_replays(app, client):
    org = _org(client)
    event = {"id": "evt_1", "type": "checkout.session.completed", "livemode": False,
             "data": {"object": {"metadata": {"organization_id": org["id"], "plan_code": "scale"}}}}
    body = json.dumps(event).encode()
    bad = client.post("/api/v1/billing/webhook", data=body, headers={"Stripe-Signature": "t=1,v1=deadbeef"})
    assert bad.status_code == 400
    secret = app.config["BILLING_WEBHOOK_SECRET"]
    ok = client.post("/api/v1/billing/webhook", data=body, headers={"Stripe-Signature": sign_payload(body, secret)})
    assert ok.get_json()["status"] == "subscription_activated"
    again = client.post("/api/v1/billing/webhook", data=body, headers={"Stripe-Signature": sign_payload(body, secret)})
    assert again.get_json()["status"] == "duplicate_ignored"
    assert BillingEvent.query.count() == 1
    stale = client.post("/api/v1/billing/webhook", data=body,
                        headers={"Stripe-Signature": sign_payload(body, secret, timestamp=1_000_000)})
    assert stale.status_code == 400  # outside replay window


def test_plan_limit_blocks_extra_runs(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    org = _org(client)
    from app.services.platform_service import get_subscription

    plan = get_subscription(org["id"]).plan
    plan.entitlements_json = json.dumps({**plan.entitlements, "monthly_workflow_runs": 1})
    db.session.commit()
    campaign, _ = _run(client, org["id"], "a")
    second = client.post(f"/api/v1/organizations/{org['id']}/campaigns/{campaign['id']}/runs",
                         headers={"Idempotency-Key": "b"})
    assert second.status_code == 429
    assert "plan allows 1" in second.get_json()["error"]["message"]


def test_downgrade_blocked_when_usage_exceeds_target_plan(app, client):
    org = _org(client)
    from app.models.platform import Plan
    from app.services.platform_service import ensure_plans_seeded

    ensure_plans_seeded()
    launch = Plan.query.filter_by(code="launch").first()
    launch.entitlements_json = json.dumps({**launch.entitlements, "active_campaigns": 0})
    db.session.commit()
    create_campaign(client, org["id"])
    resp = client.post(f"/api/v1/organizations/{org['id']}/billing/checkout", json={"plan_code": "launch"})
    assert resp.status_code == 409


# ---- Auth -------------------------------------------------------------------

def test_password_reset_flow_revokes_old_sessions(app, client):
    register_and_login(client, email="reset@example.com")
    other = app.test_client()
    other.post("/api/v1/auth/login", json={"email": "reset@example.com", "password": "correct-horse-1"})
    assert other.get("/api/v1/me").status_code == 200

    resp = client.post("/api/v1/auth/forgot-password", json={"email": "reset@example.com"})
    assert resp.status_code == 200
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert unknown.get_json() == resp.get_json()  # no account enumeration
    token = app.extensions["last_reset_link"].split("token=")[1]
    done = client.post("/api/v1/auth/reset-password", json={"token": token, "password": "new-password-9"})
    assert done.status_code == 200
    from flask import g

    g.pop("_login_user", None)  # the test fixture shares one app context; real requests don't
    assert other.get("/api/v1/me").status_code == 401  # old session revoked
    reuse = client.post("/api/v1/auth/reset-password", json={"token": token, "password": "another-pass-1"})
    assert reuse.status_code == 400
    assert client.post("/api/v1/auth/login", json={"email": "reset@example.com",
                                                   "password": "new-password-9"}).status_code == 200


def test_change_password_and_sign_out_everywhere(app, client):
    register_and_login(client, email="cp@example.com")
    wrong = client.post("/api/v1/auth/change-password", json={"current_password": "x", "new_password": "abcdefgh1"})
    assert wrong.status_code == 400
    ok = client.post("/api/v1/auth/change-password",
                     json={"current_password": "correct-horse-1", "new_password": "abcdefgh1"})
    assert ok.status_code == 200
    assert client.get("/api/v1/me").status_code == 200  # current session kept
    client.post("/api/v1/auth/sign-out-everywhere")
    assert client.get("/api/v1/me").status_code == 401


def test_security_headers_present(client):
    resp = client.get("/api/v1/health/live")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["X-Request-Id"]


# ---- Team -------------------------------------------------------------------

def test_invitation_flow_and_owner_protection(app, client):
    org = _org(client)
    invite = client.post(f"/api/v1/organizations/{org['id']}/invitations",
                         json={"email": "mate@example.com", "role": "approver"}).get_json()
    token = invite["invite_link"].split("token=")[1]
    client.post("/api/v1/auth/logout")

    register_and_login(client, email="wrong@example.com")
    assert client.post("/api/v1/invitations/accept", json={"token": token}).status_code == 403
    client.post("/api/v1/auth/logout")

    register_and_login(client, email="mate@example.com")
    assert client.post("/api/v1/invitations/accept", json={"token": token}).status_code == 200
    me = Membership.query.join(Membership.user).filter_by(email="mate@example.com").one()
    assert me.role == "approver"
    # An approver can't change roles.
    owner = Membership.query.filter_by(organization_id=org["id"], role="owner").one()
    assert client.patch(f"/api/v1/organizations/{org['id']}/members/{owner.id}",
                        json={"role": "viewer"}).status_code == 403


def test_last_owner_cannot_be_demoted(app, client):
    org = _org(client)
    owner = Membership.query.filter_by(organization_id=org["id"]).one()
    resp = client.patch(f"/api/v1/organizations/{org['id']}/members/{owner.id}", json={"role": "admin"})
    assert resp.status_code == 409


# ---- Policies, notifications, knowledge -------------------------------------

def test_locked_policies_cannot_be_loosened(client):
    org = _org(client)
    resp = client.patch(f"/api/v1/organizations/{org['id']}/policies/spend_change", json={"mode": "auto"})
    assert resp.status_code == 403


def test_drafting_policy_requires_start_approval(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    org = _org(client)
    client.patch(f"/api/v1/organizations/{org['id']}/policies/agent_drafting", json={"mode": "require_approval"})
    _campaign, run = _run(client, org["id"])
    assert run["status"] == "awaiting_approval"
    assert drain() == 0
    resp = client.post(f"/api/v1/organizations/{org['id']}/runs/{run['id']}/approve-start")
    assert resp.get_json()["workflow_run"]["status"] == "queued"
    assert drain() == 12


def test_completed_run_notifies_and_proposes_knowledge(app, client, monkeypatch):
    record = {"summary": "Done.", "knowledge_updates": ["Weekend hikers respond to durability claims"]}
    use_provider(monkeypatch, FakeProvider(overrides={"campaign_record": record}))
    org = _org(client)
    _run(client, org["id"])
    drain()
    kinds = {n.kind for n in Notification.query.filter_by(organization_id=org["id"])}
    assert {"run.completed", "knowledge.proposed"} <= kinds
    entry = KnowledgeEntry.query.filter_by(organization_id=org["id"]).one()
    assert entry.status == "proposed" and entry.source_run_id
    # Proposed knowledge is not given to agents until approved.
    from app.services.platform_service import approved_knowledge_for_agents

    assert approved_knowledge_for_agents(org["id"]) == []
    client.patch(f"/api/v1/organizations/{org['id']}/knowledge/{entry.id}", json={"status": "approved"})
    assert approved_knowledge_for_agents(org["id"])[0]["title"].startswith("Weekend hikers")
    unread = client.get(f"/api/v1/organizations/{org['id']}/notifications").get_json()["unread_count"]
    assert unread >= 2
    client.post(f"/api/v1/organizations/{org['id']}/notifications/read", json={})
    assert client.get(f"/api/v1/organizations/{org['id']}/notifications").get_json()["unread_count"] == 0


def test_calendar_import_from_social_deliverable(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    org = _org(client)
    _run(client, org["id"])
    drain()
    from app.models.deliverable import Deliverable

    social = Deliverable.query.filter_by(organization_id=org["id"], deliverable_type="social_calendar").one()
    resp = client.post(f"/api/v1/organizations/{org['id']}/calendar/from-deliverable",
                       json={"deliverable_id": social.id, "start_date": "2026-12-01"})
    assert resp.get_json()["created"] == 1
    again = client.post(f"/api/v1/organizations/{org['id']}/calendar/from-deliverable",
                        json={"deliverable_id": social.id, "start_date": "2026-12-01"})
    assert again.status_code == 409
    entries = client.get(f"/api/v1/organizations/{org['id']}/calendar?from=2026-12-01&to=2026-12-31").get_json()
    assert entries["entries"][0]["status"] == "planned"


# ---- Uploads, webhooks, data lifecycle --------------------------------------

def test_upload_validation(app, client, tmp_path):
    app.config["UPLOAD_DIR"] = str(tmp_path)
    org = _org(client)
    url = f"/api/v1/organizations/{org['id']}/documents"
    ok = client.post(url, data={"file": (io.BytesIO(PNG), "logo.png", "image/png")},
                     content_type="multipart/form-data")
    assert ok.status_code == 201, ok.get_json()
    exe = client.post(url, data={"file": (io.BytesIO(b"MZ..."), "run.exe", "application/octet-stream")},
                      content_type="multipart/form-data")
    assert exe.status_code == 400
    fake = client.post(url, data={"file": (io.BytesIO(b"<script>"), "logo.png", "image/png")},
                       content_type="multipart/form-data")
    assert fake.status_code == 400
    doc_id = ok.get_json()["document"]["id"]
    dl = client.get(f"{url}/{doc_id}/download")
    assert dl.data == PNG and "attachment" in dl.headers["Content-Disposition"]


def test_webhook_ssrf_and_signed_delivery(app, client, monkeypatch):
    org = _org(client)
    url = f"/api/v1/organizations/{org['id']}/webhooks"
    assert client.post(url, json={"url": "http://example.com/h", "events": ["run.completed"]}).status_code == 400
    created = client.post(url, json={"url": "https://127.0.0.1/hook", "events": ["run.completed"]}).get_json()
    from app.services import webhook_service

    sent = []
    monkeypatch.setattr(webhook_service, "_send", lambda u, b, h: sent.append((u, b, h)) or 200)
    webhook_service.emit(org["id"], "run.completed", {"run_id": "r1"})
    db.session.commit()
    webhook_service.deliver_due()
    delivery = WebhookDelivery.query.one()
    # 127.0.0.1 resolves to loopback: refused at delivery time, nothing sent.
    assert delivery.status == "failed" and "private" in delivery.last_error and sent == []

    endpoint_id = created["endpoint"]["id"]
    from app.models.billing import WebhookEndpoint

    ep = db.session.get(WebhookEndpoint, endpoint_id)
    monkeypatch.setattr(webhook_service, "validate_target_url", lambda u, resolve=True: None)
    webhook_service.emit(org["id"], "run.completed", {"run_id": "r2"})
    db.session.commit()
    webhook_service.deliver_due()
    _u, body, headers = sent[0]
    from app.billing.providers import verify_signature

    verify_signature(body, headers["ARC-Signature"], ep.secret)
    assert headers["ARC-Event-Version"]


def test_export_excludes_secrets_and_deletion_purges(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    org = _org(client)
    client.post(f"/api/v1/organizations/{org['id']}/webhooks",
                json={"url": "https://example.com/h", "events": ["run.completed"]})
    _run(client, org["id"])
    drain()
    export = client.get(f"/api/v1/organizations/{org['id']}/export").get_data(as_text=True)
    data = json.loads(export)
    assert len(data["deliverables"]) == 12 and "whsec_" not in export and "password_hash" not in export

    bad = client.post(f"/api/v1/organizations/{org['id']}/deletion", json={"confirm_name": "nope"})
    assert bad.status_code == 400
    resp = client.post(f"/api/v1/organizations/{org['id']}/deletion", json={"confirm_name": "Acme Co"})
    assert resp.get_json()["status"] == "deletion_scheduled"
    from app.models.organization import Organization
    from app.services.data_lifecycle import purge_due_workspaces

    assert purge_due_workspaces() == 0  # grace period
    stored = db.session.get(Organization, org["id"])
    stored.deletion_scheduled_at = utcnow() - timedelta(minutes=1)
    db.session.commit()
    assert purge_due_workspaces() == 1
    db.session.expire_all()
    assert db.session.get(Organization, org["id"]) is None


# ---- Approvals --------------------------------------------------------------

def test_approval_context_expiry_and_revoke(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    org = _org(client)
    _run(client, org["id"])
    drain()
    from app.models.deliverable import Deliverable

    d = Deliverable.query.filter_by(organization_id=org["id"], deliverable_type="content_pack").one()
    a = client.post(f"/api/v1/organizations/{org['id']}/approvals", json={"deliverable_id": d.id}).get_json()["approval"]
    assert a["requesting_agent_id"] == "creative_studio"
    assert a["risk_level"] in ("medium", "high") and a["expires_at"]
    dup = client.post(f"/api/v1/organizations/{org['id']}/approvals", json={"deliverable_id": d.id}).get_json()
    assert dup["approval"]["id"] == a["id"]  # one pending decision per version

    client.post(f"/api/v1/organizations/{org['id']}/approvals/{a['id']}/decision", json={"decision": "approved"})
    revoked = client.post(f"/api/v1/organizations/{org['id']}/approvals/{a['id']}/revoke").get_json()
    assert revoked["approval"]["decision"] == "revoked"
    execute = client.post(f"/api/v1/organizations/{org['id']}/approvals/{a['id']}/execute",
                          headers={"Idempotency-Key": "x1"})
    assert execute.status_code == 409

    r = Deliverable.query.filter_by(organization_id=org["id"], deliverable_type="strategy").one()
    b = client.post(f"/api/v1/organizations/{org['id']}/approvals", json={"deliverable_id": r.id}).get_json()["approval"]
    from app.models.approval import Approval

    row = db.session.get(Approval, b["id"])
    row.expires_at = utcnow() - timedelta(days=1)
    db.session.commit()
    late = client.post(f"/api/v1/organizations/{org['id']}/approvals/{b['id']}/decision", json={"decision": "approved"})
    assert late.status_code == 409 and "expired" in late.get_json()["error"]["message"]


# ---- Analytics, concurrency, openapi ---------------------------------------

def test_dashboard_reports_business_metrics_as_unavailable(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    org = _org(client)
    _run(client, org["id"])
    drain()
    body = client.get(f"/api/v1/organizations/{org['id']}/dashboard?days=30").get_json()
    kpis = {k["key"]: k for k in body["kpis"]}
    assert kpis["runs_completed"]["value"] == 1
    assert kpis["tasks_completed"]["value"] == 12
    assert kpis["agent_cost"]["basis"] == "estimate"
    assert all(m["available"] is False and m["value"] is None for m in body["business_metrics"])
    assert body["campaigns"][0]["progress_pct"] == 100
    assert client.get(f"/api/v1/organizations/{org['id']}/dashboard?days=3").status_code == 400
    csv_body = client.get(f"/api/v1/organizations/{org['id']}/reports/export.csv?days=30").get_data(as_text=True)
    assert csv_body.startswith("date,tasks_succeeded")


def test_concurrency_limit_is_enforced(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    org = _org(client)
    client.patch(f"/api/v1/organizations/{org['id']}", json={"max_concurrent_tasks": 1})
    c1 = create_campaign(client, org["id"], name="One")
    c2 = create_campaign(client, org["id"], name="Two")
    for c, k in ((c1, "x"), (c2, "y")):
        client.post(f"/api/v1/organizations/{org['id']}/campaigns/{c['id']}/runs", headers={"Idempotency-Key": k})
    from app.workflows.engine import claim_next_task

    assert claim_next_task() is not None
    assert claim_next_task() is None  # second CMO task is ready but the workspace is at its limit


def test_openapi_lists_real_routes(client):
    spec = client.get("/api/v1/openapi.json").get_json()
    assert spec["openapi"] == "3.1.0"
    assert "/api/v1/organizations/{organization_id}/campaigns/{campaign_id}/runs" in spec["paths"]
    assert "/api/v1/billing/webhook" in spec["paths"]


def test_contact_form_validation(client):
    assert client.post("/api/v1/public/contact", json={"name": "", "email": "x"}).status_code == 400
    ok = client.post("/api/v1/public/contact",
                     json={"name": "Sam", "email": "sam@example.com", "message": "Tell me about pricing please"})
    assert ok.status_code == 201


def test_kill_switch_and_disabled_destination_block_exports(app, client, monkeypatch):
    use_provider(monkeypatch, FakeProvider())
    org = _org(client)
    _run(client, org["id"])
    drain()
    from app.models.deliverable import Deliverable

    d = Deliverable.query.filter_by(organization_id=org["id"], deliverable_type="content_pack").one()
    a = client.post(f"/api/v1/organizations/{org['id']}/approvals", json={"deliverable_id": d.id}).get_json()["approval"]
    client.post(f"/api/v1/organizations/{org['id']}/approvals/{a['id']}/decision", json={"decision": "approved"})
    url = f"/api/v1/organizations/{org['id']}/approvals/{a['id']}/execute"

    client.patch(f"/api/v1/organizations/{org['id']}/operations/controls", json={"kill_switch_enabled": True})
    assert client.post(url, headers={"Idempotency-Key": "k1"}).status_code == 403
    client.patch(f"/api/v1/organizations/{org['id']}/operations/controls", json={"kill_switch_enabled": False})

    client.patch(f"/api/v1/organizations/{org['id']}/integrations/manual_export:google_ads", json={"enabled": False})
    blocked = client.post(url, headers={"Idempotency-Key": "k2"}, json={"target_platform": "google_ads"})
    assert blocked.status_code == 403
    ok = client.post(url, headers={"Idempotency-Key": "k3"}, json={"target_platform": "meta_instagram"})
    assert ok.status_code in (200, 201), ok.get_json()
