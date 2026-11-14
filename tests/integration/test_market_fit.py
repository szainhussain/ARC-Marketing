"""Channel-based agent selection, the light model tier, configurable prices
and the password-reset email (docs/DECISIONS.md D21)."""

from app.agents.selection import CORE_AGENTS, agents_for_channels
from app.workflows.engine import drain
from tests.conftest import complete_profile, create_org, register_and_login
from tests.fakes import FakeProvider, use_provider


def _campaign(client, org_id, channels):
    resp = client.post(f"/api/v1/organizations/{org_id}/campaigns",
                       json={"name": "Ramadan offer", "objective": "Fill weekday bookings", "channels": channels})
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()["campaign"]


def _start(client, org_id, campaign_id, key="k1"):
    resp = client.post(f"/api/v1/organizations/{org_id}/campaigns/{campaign_id}/runs",
                       headers={"Idempotency-Key": key})
    assert resp.status_code in (200, 201, 202), resp.get_json()
    return resp.get_json()["workflow_run"]


def test_selection_keeps_core_and_adds_only_matching_specialists():
    chosen = agents_for_channels("Instagram, Google Ads")
    assert set(CORE_AGENTS) <= chosen
    assert {"social_media", "paid_media"} <= chosen
    assert not chosen & {"key_accounts", "pr_partnerships", "customer_insights", "seo_growth"}


def test_selection_falls_back_to_everyone_when_unsure():
    assert len(agents_for_channels(None)) == 12
    assert len(agents_for_channels("  ")) == 12
    assert len(agents_for_channels("billboards on Sheikh Zayed Road")) == 12


def test_selection_matches_whole_words_only():
    # "broadcast" contains "ad" and "expo" contains "x": neither is a channel match.
    assert len(agents_for_channels("broadcast, expo")) == 12
    assert "paid_media" in agents_for_channels("Meta ads")


def test_run_only_queues_and_completes_selected_agents(client, app, monkeypatch):
    register_and_login(client)
    org = create_org(client)
    complete_profile(client, org["id"])
    campaign = _campaign(client, org["id"], "Instagram, Facebook")
    use_provider(monkeypatch, FakeProvider())

    run = _start(client, org["id"], campaign["id"])
    agent_ids = {t["agent_id"] for t in run["tasks"]}
    assert agent_ids == set(CORE_AGENTS) | {"social_media"}

    with app.app_context():
        assert drain() == 7
    detail = client.get(f"/api/v1/organizations/{org['id']}/runs/{run["id"]}").get_json()["workflow_run"]
    # The quality gate did not wait for specialists that were never queued.
    assert detail["status"] == "completed"
    assert all(t["status"] == "succeeded" for t in detail["tasks"])


def test_light_tier_uses_light_model_and_prices(app):
    from app.agents.registry import get_agent
    from app.workflows.engine import _provider_config

    with app.app_context():
        app.config.update(AI_MODEL="big", AI_MODEL_LIGHT="small", AI_PRICE_LIGHT_INPUT_PER_MTOK=0.1,
                          AI_PRICE_LIGHT_OUTPUT_PER_MTOK=0.4)
        light = _provider_config(get_agent("record_keeper"))
        assert light["AI_MODEL"] == "small" and light["AI_PRICE_OUTPUT_PER_MTOK"] == 0.4
        assert _provider_config(get_agent("cmo"))["AI_MODEL"] == "big"
        app.config.update(AI_MODEL_LIGHT="")
        assert _provider_config(get_agent("record_keeper"))["AI_MODEL"] == "big"


def test_cost_estimate_uses_configured_prices():
    from app.ai.provider_adapter import GroqProvider, _estimate_cost, get_provider

    provider = get_provider({"AI_PROVIDER": "groq", "GROQ_API_KEY": "k", "AI_MODEL": "m",
                             "AI_PRICE_INPUT_PER_MTOK": 0.15, "AI_PRICE_OUTPUT_PER_MTOK": 0.6})
    assert isinstance(provider, GroqProvider) and (provider.price_in, provider.price_out) == (0.15, 0.6)
    assert round(_estimate_cost(1_000_000, 500_000, 0.15, 0.6), 6) == 0.45


def test_prompt_puts_shared_context_first():
    from app.ai.provider_adapter import _build_prompt
    from app.ai.schemas import SocialCalendarSchema

    ctx = {"campaign": {"name": "X"}, "business_profile": {"company": "Y"}}
    a = _build_prompt("social_calendar", {"n": 1}, {**ctx, "agent_role": "Agent 03."}, SocialCalendarSchema())
    b = _build_prompt("campaign_record", {"n": 2}, {**ctx, "agent_role": "Agent 12."}, SocialCalendarSchema())
    shared = a[: a.index("You are the")]
    assert shared.startswith("Business/campaign context:") and b.startswith(shared)


def test_forgot_password_emails_the_reset_link(client, app, monkeypatch):
    sent = []
    monkeypatch.setattr("app.integrations.email_providers._http",
                        lambda method, url, headers, body=None: sent.append((url, body)) or {"id": "msg_1"})
    app.config.update(SYSTEM_EMAIL_PROVIDER="resend", SYSTEM_EMAIL_API_KEY="re_test",
                      SYSTEM_EMAIL_FROM="hello@example.com")
    user = register_and_login(client)
    client.post("/api/v1/auth/logout")

    resp = client.post("/api/v1/auth/forgot-password", json={"email": user["email"]})
    assert resp.status_code == 200
    assert len(sent) == 1
    url, body = sent[0]
    assert url == "https://api.resend.com/emails" and body["to"] == [user["email"]]
    assert "/reset-password?token=" in body["text"]

    # Unknown address: same response, nothing sent.
    assert client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}).status_code == 200
    assert len(sent) == 1


def test_forgot_password_still_answers_when_email_is_not_configured(client, app):
    app.config.update(SYSTEM_EMAIL_PROVIDER="", SYSTEM_EMAIL_API_KEY="", SYSTEM_EMAIL_FROM="")
    user = register_and_login(client)
    client.post("/api/v1/auth/logout")
    assert client.post("/api/v1/auth/forgot-password", json={"email": user["email"]}).status_code == 200
