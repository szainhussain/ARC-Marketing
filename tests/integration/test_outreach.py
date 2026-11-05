"""Outreach email: lawful lists only, batch approval bound to exactly what
is sent, daily limits, suppression, kill switch and one-click unsubscribe."""

import pytest

from app.extensions import db
from app.integrations import email_providers as ep
from app.models.outreach import OutreachMessage
from app.workflows.engine import drain
from tests.conftest import create_org, register_and_login

CSV = "email,first_name,company,source\nann@shop.co,Ann,Ann's Deli,you met us at the Bristol Food Fair\nbob@cafe.co,Bob,Bob's Cafe,\nnot-an-email,X,,\nann@shop.co,Ann,,\n"


class FakeMail:
    def __init__(self):
        self.sent, self.fail_next, self.calls = [], [], []

    def __call__(self, method, url, headers, body=None):
        self.calls.append((method, url, headers))
        if self.fail_next:
            raise self.fail_next.pop(0)
        if method == "GET":
            return {"email": "owner@shop.co"}
        self.sent.append({"url": url, "headers": headers, "body": body})
        return {"messageId": f"m{len(self.sent)}", "id": f"r{len(self.sent)}"}


@pytest.fixture
def mail(monkeypatch):
    f = FakeMail()
    monkeypatch.setattr(ep, "_http", f)
    return f


def _sender(client, org_id, provider="brevo"):
    return client.post(f"/api/v1/organizations/{org_id}/outreach/sender", json={
        "provider": provider, "api_key": "xkeysib-1234567890", "sender_email": "hello@fernleaf.co",
        "sender_name": "Fernleaf Home & Garden", "postal_address": "12 Mill Lane, Bristol BS1 4AA, UK"})


def _list(client, org_id, **kw):
    return client.post(f"/api/v1/organizations/{org_id}/outreach/lists", json={
        "name": "Fair leads", "lawful_basis": "legitimate_interest", "csv": CSV,
        "source_description": "people who left cards at our stand", "attest": True, **kw})


def _batch(client, org_id, list_id, daily_limit=25):
    return client.post(f"/api/v1/organizations/{org_id}/outreach/batches", json={
        "list_id": list_id, "name": "Autumn intro", "subject": "Hi {{first_name}}, autumn plants for {{company}}",
        "body": "Hello {{first_name}},\n\nWe'd love to stock {{company}} with autumn bulbs.", "daily_limit": daily_limit}).get_json()["batch"]


def _ready(client, mail, daily_limit=25, provider="brevo"):
    register_and_login(client)
    org = create_org(client)
    assert _sender(client, org["id"], provider).status_code == 200
    lst = _list(client, org["id"]).get_json()
    b = _batch(client, org["id"], lst["list"]["id"], daily_limit)
    base = f"/api/v1/organizations/{org['id']}/outreach/batches/{b['id']}"
    return org["id"], lst, b, base


def test_list_upload_requires_lawful_basis_and_attestation(app, client, mail):
    register_and_login(client)
    org = create_org(client)
    assert _list(client, org["id"], attest=False).status_code == 400
    assert _list(client, org["id"], lawful_basis="scraped").status_code == 400
    r = _list(client, org["id"])
    assert r.status_code == 201
    assert r.get_json()["stats"] == {"added": 2, "invalid": 1, "duplicates": 1, "suppressed": 0}


def test_nothing_sends_until_approved_and_started(app, client, mail):
    org_id, lst, b, base = _ready(client, mail)
    assert client.post(f"{base}/start").status_code == 409
    drain()
    assert mail.sent == []
    client.post(f"{base}/request-approval")
    a = client.post(f"{base}/approve").get_json()["batch"]
    assert a["status"] == "approved" and a["counts"]["queued"] == 2
    drain()
    assert mail.sent == []  # approved but not started
    client.post(f"{base}/start")
    drain()
    assert len(mail.sent) == 2
    first = mail.sent[0]["body"]
    assert first["subject"] == "Hi Ann, autumn plants for Ann's Deli"
    assert "Unsubscribe" in first["textContent"] and "12 Mill Lane" in first["textContent"]
    assert "Bristol Food Fair" in first["textContent"]  # why they're receiving it
    assert mail.sent[0]["body"]["headers"]["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"
    assert client.get(f"/api/v1/organizations/{org_id}/outreach").get_json()["batches"][0]["status"] in ("sending", "completed")


def test_daily_limit_is_enforced(app, client, mail):
    org_id, lst, b, base = _ready(client, mail, daily_limit=1)
    client.post(f"{base}/request-approval"); client.post(f"{base}/approve"); client.post(f"{base}/start")
    drain()
    assert len(mail.sent) == 1


def test_edit_after_approval_requires_reapproval(app, client, mail):
    org_id, lst, b, base = _ready(client, mail)
    client.post(f"{base}/request-approval"); client.post(f"{base}/approve")
    edited = client.patch(base, json={"subject": "Changed subject line", "body": b["body"]}).get_json()["batch"]
    assert edited["status"] == "draft" and edited["counts"]["queued"] == 0
    assert client.post(f"{base}/start").status_code == 409


def test_sender_change_mid_send_pauses_the_batch(app, client, mail):
    org_id, lst, b, base = _ready(client, mail, daily_limit=1)
    client.post(f"{base}/request-approval"); client.post(f"{base}/approve"); client.post(f"{base}/start")
    drain()
    client.post(f"/api/v1/organizations/{org_id}/outreach/sender", json={
        "provider": "brevo", "api_key": "xkeysib-other-key-123", "sender_email": "sales@other.co",
        "sender_name": "Someone else", "postal_address": "1 Other Street, London"})
    st = client.get(f"/api/v1/organizations/{org_id}/outreach").get_json()["batches"][0]
    assert st["status"] == "paused"
    assert client.post(f"{base}/start").status_code == 409  # must be re-approved


def test_kill_switch_stops_sending(app, client, mail):
    org_id, lst, b, base = _ready(client, mail)
    client.post(f"{base}/request-approval"); client.post(f"{base}/approve"); client.post(f"{base}/start")
    with app.app_context():
        from app.models.organization import Organization

        db.session.get(Organization, org_id).kill_switch_enabled = True
        db.session.commit()
    drain()
    assert mail.sent == []


def test_unsubscribe_is_one_click_permanent_and_workspace_wide(app, client, mail):
    org_id, lst, b, base = _ready(client, mail, daily_limit=1)
    client.post(f"{base}/request-approval"); client.post(f"{base}/approve"); client.post(f"{base}/start")
    drain()
    one_click = mail.sent[0]["body"]["headers"]["List-Unsubscribe"].strip("<>")
    token = one_click.rsplit("/", 1)[1]
    client.post("/api/v1/auth/logout")
    r = client.post(f"/api/v1/outreach/unsubscribe/{token}", data="List-Unsubscribe=One-Click")
    assert r.status_code == 200 and r.get_json()["unsubscribed"] is True
    client.post("/api/v1/auth/login", json={"email": "owner@example.com", "password": "correct-horse-1"})
    sup = client.get(f"/api/v1/organizations/{org_id}/outreach/suppressions").get_json()["suppressions"]
    assert [s["email"] for s in sup] == ["ann@shop.co"]
    # A new list with the same person never emails them.
    again = _list(client, org_id, name="Second list").get_json()
    assert again["stats"]["suppressed"] == 1
    assert client.post("/api/v1/outreach/unsubscribe/not-a-real-token").status_code == 404


def test_uncertain_brevo_send_is_never_retried(app, client, mail):
    org_id, lst, b, base = _ready(client, mail, daily_limit=1)
    client.post(f"{base}/request-approval"); client.post(f"{base}/approve"); client.post(f"{base}/start")
    with app.app_context():
        from datetime import timedelta

        from app.models.base import utcnow

        m = OutreachMessage.query.first()
        m.status, m.updated_at = "sending", utcnow() - timedelta(hours=1)
        db.session.commit()
    drain()
    with app.app_context():
        statuses = sorted(x.status for x in OutreachMessage.query.all())
    assert "failed" in statuses  # interrupted Brevo send is not repeated


def test_rejected_key_is_refused_and_secret_never_returned(app, client, mail):
    register_and_login(client)
    org = create_org(client)
    mail.fail_next = [ep.EmailProviderError("Email provider returned 401", status=401)]
    assert _sender(client, org["id"]).status_code == 400
    _sender(client, org["id"])
    body = client.get(f"/api/v1/organizations/{org['id']}/outreach").get_data(as_text=True)
    assert "xkeysib" not in body
