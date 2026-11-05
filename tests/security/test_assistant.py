"""Ask ARC answers only from the asking workspace, only cites real items,
never sees unapproved knowledge, and keeps each member's chat private."""

from app.ai.base import AIResult
from app.ai.errors import ProviderUnavailable, RateLimited
from app.extensions import db
from app.models.assistant import AssistantMessage
from app.models.platform import KnowledgeEntry, Notification
from app.services import assistant_service
from app.workflows.engine import drain
from tests.conftest import complete_profile, create_org, register_and_login


class FakeAssistant:
    name = "fake"

    def __init__(self, answer=None, exc=None):
        self.calls, self.answer, self.exc = [], answer, exc

    def generate_structured(self, task_type, input_data, output_schema, context=None, **kw):
        self.calls.append(input_data)
        if self.exc:
            raise self.exc
        data = self.answer(input_data) if callable(self.answer) else self.answer
        return AIResult(data=output_schema().load(data), provider="fake", model="fake", input_tokens=1, output_tokens=1,
                        estimated_cost_usd=0.0)


def _org_with_knowledge(app, client, email="owner@example.com", name="Acme Co"):
    register_and_login(client, email=email)
    org = create_org(client, name=name)
    complete_profile(client, org["id"])
    with app.app_context():
        db.session.add(KnowledgeEntry(organization_id=org["id"], kind="faq", title="Shipping policy",
                                      body="We ship worldwide in 3-5 business days. Returns accepted for 60 days.", status="approved"))
        db.session.add(KnowledgeEntry(organization_id=org["id"], kind="faq", title="Secret draft shipping plan",
                                      body="Unapproved: shipping becomes free next year.", status="proposed"))
        db.session.commit()
    return org


def _use(monkeypatch, provider):
    monkeypatch.setattr("app.workflows.engine.get_provider", lambda cfg: provider)
    return provider


def test_answers_from_own_workspace_with_real_citations(app, client, monkeypatch):
    org = _org_with_knowledge(app, client)

    def answer(inp):
        kid = next(i["id"] for i in inp["workspace_data"] if i["kind"] == "knowledge")
        return {"answer": "We ship in 3-5 business days.", "source_ids": [kid, "k:made-up-id"],
                "suggested_action": {"type": "open_knowledge", "label": "See knowledge"}}

    fake = _use(monkeypatch, FakeAssistant(answer=answer))
    url = f"/api/v1/organizations/{org['id']}/assistant/messages"
    assert client.post(url, json={"content": ""}).status_code == 400
    resp = client.post(url, json={"content": "How long does shipping take?"})
    assert resp.status_code == 202 and resp.get_json()["reply"]["status"] == "pending"
    drain()
    msgs = client.get(url).get_json()["messages"]
    reply = msgs[-1]
    assert reply["status"] == "answered" and "3-5 business days" in reply["content"]
    assert reply["sources"] == [{"kind": "knowledge", "title": "Shipping policy", "link": "/app/knowledge"}]  # fake id dropped
    assert reply["action"] == {"type": "open_knowledge", "label": "See knowledge", "link": "/app/knowledge"}
    data = fake.calls[0]["workspace_data"]
    assert not any("Secret draft" in i["title"] for i in data)  # unapproved knowledge never reaches the model


def test_contact_team_notifies_and_failures_are_honest(app, client, monkeypatch):
    org = _org_with_knowledge(app, client)
    url = f"/api/v1/organizations/{org['id']}/assistant/messages"
    _use(monkeypatch, FakeAssistant(answer={"answer": "I'll pass this to your team.", "source_ids": [],
                                            "suggested_action": {"type": "contact_team"}}))
    client.post(url, json={"content": "Can a person call me about my invoice?"})
    drain()
    with app.app_context():
        assert Notification.query.filter_by(organization_id=org["id"], kind="assistant.handoff").count() == 1

    _use(monkeypatch, FakeAssistant(exc=ProviderUnavailable("no key")))
    client.post(url, json={"content": "Anything?"})
    drain()
    last = client.get(url).get_json()["messages"][-1]
    assert last["status"] == "failed" and last["error_summary"].startswith("capability_unavailable")

    _use(monkeypatch, FakeAssistant(exc=RateLimited("slow")))
    client.post(url, json={"content": "Again?"})
    with app.app_context():
        assert assistant_service.process_next_question() is False
        pending = AssistantMessage.query.filter_by(role="assistant", status="pending").one()
        assert pending.error_summary.startswith("retrying")
        assert assistant_service.process_next_question() is False  # cooling down, not hammering the provider


def test_chats_are_private_per_member_and_workspace(app, client, monkeypatch):
    _use(monkeypatch, FakeAssistant(answer={"answer": "ok", "source_ids": []}))
    org_a = _org_with_knowledge(app, client)
    client.post(f"/api/v1/organizations/{org_a['id']}/assistant/messages", json={"content": "Private question"})
    client.post("/api/v1/auth/logout")
    org_b = _org_with_knowledge(app, client, email="b@example.com", name="B Co")
    a_url = f"/api/v1/organizations/{org_a['id']}/assistant/messages"
    assert client.get(a_url).status_code in (403, 404)
    assert client.post(a_url, json={"content": "hi"}).status_code in (403, 404)
    assert client.get(f"/api/v1/organizations/{org_b['id']}/assistant/messages").get_json()["messages"] == []
    # B's question never retrieves A's knowledge.
    fake = _use(monkeypatch, FakeAssistant(answer={"answer": "ok", "source_ids": []}))
    with app.app_context():
        KnowledgeEntry.query.filter_by(organization_id=org_b["id"]).delete()
        db.session.commit()
    client.post(f"/api/v1/organizations/{org_b['id']}/assistant/messages", json={"content": "shipping policy?"})
    drain()
    assert all(i["kind"] != "knowledge" for c in fake.calls for i in c["workspace_data"])


def test_monthly_limit(app, client, monkeypatch):
    org = _org_with_knowledge(app, client)
    app.config["ASSISTANT_MONTHLY_LIMIT"] = 1
    url = f"/api/v1/organizations/{org['id']}/assistant/messages"
    assert client.post(url, json={"content": "one"}).status_code == 202
    assert client.post(url, json={"content": "two"}).status_code == 429
