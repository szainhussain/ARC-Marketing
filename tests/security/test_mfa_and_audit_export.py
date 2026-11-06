import time

from app.extensions import db
from app.models.membership import Membership
from app.services.mfa_service import _code_at, totp_now
from tests.conftest import create_org, register_and_login

LOGIN = "/api/v1/auth/login"
CREDS = {"email": "owner@example.com", "password": "correct-horse-1"}


def test_totp_matches_rfc6238_vector():
    # RFC 6238 appendix B, SHA-1, T=59s -> step 1, secret "12345678901234567890".
    import base64

    secret = base64.b32encode(b"12345678901234567890").decode()
    assert _code_at(secret, 1) == "287082"  # last 6 digits of 94287082


def test_mfa_enrolment_login_replay_recovery_and_disable(client):
    register_and_login(client)
    setup = client.post("/api/v1/auth/mfa/setup").get_json()
    assert setup["otpauth_uri"].startswith("otpauth://totp/ARC:")
    assert client.post("/api/v1/auth/mfa/enable", json={"code": "000000"}).status_code == 400
    # Pin one clock reading: codes roll every 30s, so calling totp_now() twice could straddle a
    # boundary and turn the "replayed" code below into a fresh, valid one (seen flaking in CI).
    t0 = time.time()
    enrol_code = totp_now(setup["secret"], t0)
    enabled = client.post("/api/v1/auth/mfa/enable", json={"code": enrol_code}).get_json()
    codes = enabled["recovery_codes"]
    assert len(codes) == 8 and client.get("/api/v1/me").get_json()["user"]["mfa_enabled"] is True

    client.post("/api/v1/auth/logout")
    need = client.post(LOGIN, json=CREDS)
    assert need.status_code == 401 and need.get_json()["error"]["code"] == "MFA_REQUIRED"
    assert client.get("/api/v1/me").status_code == 401  # password alone did not sign in
    # The code used for enrolment can't be replayed.
    assert client.post(LOGIN, json={**CREDS, "mfa_code": enrol_code}).get_json()["error"]["code"] == "MFA_INVALID"
    nxt = totp_now(setup["secret"], t0 + 30)
    assert client.post(LOGIN, json={**CREDS, "mfa_code": nxt}).status_code == 200

    client.post("/api/v1/auth/logout")
    assert client.post(LOGIN, json={**CREDS, "recovery_code": codes[0]}).status_code == 200
    client.post("/api/v1/auth/logout")
    assert client.post(LOGIN, json={**CREDS, "recovery_code": codes[0]}).status_code == 401  # single use
    assert client.post(LOGIN, json={**CREDS, "recovery_code": codes[1].upper()}).status_code == 200
    assert client.get("/api/v1/auth/mfa").get_json()["recovery_codes_left"] == 6

    bad = client.post("/api/v1/auth/mfa/disable", json={"password": "wrong", "recovery_code": codes[2]})
    assert bad.status_code == 400
    assert client.post("/api/v1/auth/mfa/disable", json={"password": "correct-horse-1", "recovery_code": codes[2]}).status_code == 200
    client.post("/api/v1/auth/logout")
    assert client.post(LOGIN, json=CREDS).status_code == 200


def test_audit_export_is_admin_only_and_neutralises_formulas(app, client):
    register_and_login(client)
    org = create_org(client)
    from app.services.audit_service import record_audit_event

    with app.app_context():
        record_audit_event(org["id"], "=HYPERLINK(\"x\")", actor_user_id=None)
        db.session.commit()
    resp = client.get(f"/api/v1/organizations/{org['id']}/audit-events/export.csv")
    assert resp.status_code == 200 and resp.mimetype == "text/csv"
    text = resp.get_data(as_text=True)
    assert "organization.created" in text or "workspace" in text.lower()
    assert "'=HYPERLINK" in text and ",=HYPERLINK" not in text
    with app.app_context():
        Membership.query.filter_by(organization_id=org["id"]).first().role = "analyst"
        db.session.commit()
    client.post("/api/v1/auth/logout")
    client.post(LOGIN, json=CREDS)  # fresh session so the cached membership is reloaded
    assert client.get(f"/api/v1/organizations/{org['id']}/audit-events/export.csv").status_code == 403
