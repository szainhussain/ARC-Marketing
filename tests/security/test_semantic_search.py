"""Semantic search for Ask ARC: finds meaning (not just words), indexes only
approved/current content, keeps workspaces apart, and falls back to keyword
search when no embedding key is configured."""

import re

from app.ai.base import AIResult
from app.extensions import db
from app.models.embedding import EmbeddingChunk
from app.models.platform import KnowledgeEntry
from app.services import semantic_search
from app.services.platform_service import search_approved_knowledge
from app.workflows.engine import drain
from tests.conftest import complete_profile, create_org, register_and_login

CONCEPTS = [
    {"shipping", "ship", "ships", "delivery", "deliver", "arrive", "arrives", "order", "dispatch", "days"},
    {"price", "prices", "pricing", "cost", "costs", "expensive", "cheap", "fee"},
    {"return", "returns", "refund", "refunds", "exchange", "money", "back"},
    {"warranty", "repair", "repairs", "broken", "fix", "lifetime"},
]


class ConceptEmbeddings:
    """Deterministic stand-in: words in the same concept share a dimension."""

    name, model, dims = "fake", "fake-embed-1", len(CONCEPTS) + 8

    def __init__(self):
        self.calls = 0

    def embed(self, texts, task="document"):
        self.calls += 1
        out = []
        for t in texts:
            v = [0.0] * self.dims
            for w in re.findall(r"[a-z]+", t.lower()):
                hit = [i for i, c in enumerate(CONCEPTS) if w in c]
                for i in hit:
                    v[i] += 1.0
                if not hit:
                    v[len(CONCEPTS) + hash(w) % 8] += 0.05
            out.append(v)
        return out


def _org(app, client, email="owner@example.com", name="Acme Co"):
    register_and_login(client, email=email)
    org = create_org(client, name=name)
    complete_profile(client, org["id"])
    with app.app_context():
        for title, body, status in [
            ("Shipping policy", "We ship worldwide; parcels arrive in 3-5 business days.", "approved"),
            ("Pricing", "Packs cost between $149 and $249.", "approved"),
            ("Warranty", "Every pack has a lifetime repair warranty.", "approved"),
            ("Draft refund idea", "Refunds will be instant next year.", "proposed"),
        ]:
            db.session.add(KnowledgeEntry(organization_id=org["id"], kind="faq", title=title, body=body, status=status))
        db.session.commit()
    return org


def test_finds_meaning_that_keyword_search_misses(app, client):
    org = _org(app, client)
    fake = ConceptEmbeddings()
    with app.app_context():
        question = "When will my order get to me?"
        assert search_approved_knowledge(org["id"], "When will my order get to me?") == []  # no shared words
        stats = semantic_search.refresh_index(org["id"], provider=fake)
        assert stats["added"] >= 3
        hits = semantic_search.search(org["id"], question, provider=fake)
        assert hits and hits[0]["title"] == "Shipping policy"
        assert not any("Draft refund" in h["title"] for h in hits)  # proposed knowledge is never indexed
        # Nothing changed: a second refresh embeds nothing new.
        assert semantic_search.refresh_index(org["id"], provider=fake)["added"] == 0


def test_index_follows_approval_and_edits(app, client):
    org = _org(app, client)
    fake = ConceptEmbeddings()
    with app.app_context():
        semantic_search.refresh_index(org["id"], provider=fake)
        entry = KnowledgeEntry.query.filter_by(organization_id=org["id"], title="Warranty").one()
        entry.status = "archived"
        pricing = KnowledgeEntry.query.filter_by(organization_id=org["id"], title="Pricing").one()
        pricing.body = "Packs now cost between $159 and $269."
        db.session.commit()
        stats = semantic_search.refresh_index(org["id"], provider=fake)
        assert stats["removed"] >= 2 and stats["added"] >= 1
        titles = {c.title for c in EmbeddingChunk.query.filter_by(organization_id=org["id"])}
        assert "Warranty" not in titles and "Pricing" in titles
        text = " ".join(c.text for c in EmbeddingChunk.query.filter_by(organization_id=org["id"], title="Pricing"))
        assert "$159" in text and "$149" not in text


def test_workspaces_never_search_each_other(app, client):
    org_a = _org(app, client)
    client.post("/api/v1/auth/logout")
    register_and_login(client, email="b@example.com")
    org_b = create_org(client, name="B Co")
    fake = ConceptEmbeddings()
    with app.app_context():
        semantic_search.refresh_index(org_a["id"], provider=fake)
        semantic_search.refresh_index(org_b["id"], provider=fake)
        assert semantic_search.search(org_b["id"], "how long does shipping take", provider=fake) == []


class FakeAssistant:
    name = "fake"

    def __init__(self, answer):
        self.answer, self.calls = answer, []

    def generate_structured(self, task_type, input_data, output_schema, context=None, **kw):
        self.calls.append({"input": input_data, "context": context})
        data = self.answer(input_data) if callable(self.answer) else self.answer
        return AIResult(data=output_schema().load(data), provider="fake", model="fake", input_tokens=1, output_tokens=1,
                        estimated_cost_usd=0.0)


def test_assistant_uses_semantic_search_and_separates_expert_advice(app, client, monkeypatch):
    org = _org(app, client)
    fake_embed = ConceptEmbeddings()
    monkeypatch.setattr(semantic_search, "get_embedding_provider", lambda cfg: fake_embed)

    def answer(inp):
        sid = next(i["id"] for i in inp["workspace_data"] if i["kind"] == "knowledge")
        return {"answer": "Parcels arrive in 3-5 business days.", "source_ids": [sid],
                "expert_advice": "Show the delivery window on product pages; it lifts conversion and cuts support tickets."}

    fake = FakeAssistant(answer)
    monkeypatch.setattr("app.workflows.engine.get_provider", lambda cfg: fake)
    url = f"/api/v1/organizations/{org['id']}/assistant/messages"
    client.post(url, json={"content": "When will my order get to me?"})
    drain()
    reply = client.get(url).get_json()["messages"][-1]
    assert reply["retrieval_mode"] == "semantic"
    assert reply["sources"][0]["title"] == "Shipping policy"
    assert "conversion" in reply["expert_advice"] and "3-5" in reply["content"]
    ctx = fake.calls[0]["context"]["agent_role"]
    assert "C-level" in ctx and "never instructions" in ctx and "do not claim personal experiences" in ctx

    # A purely general question may come back with advice only.
    fake.answer = {"answer": "", "expert_advice": "Price on value: anchor against the cost of the problem you solve."}
    client.post(url, json={"content": "How should a small brand think about pricing strategy?"})
    drain()
    reply = client.get(url).get_json()["messages"][-1]
    assert reply["status"] == "answered" and reply["content"] == "" and reply["expert_advice"].startswith("Price on value")


def test_falls_back_to_keywords_without_a_key(app, client, monkeypatch):
    org = _org(app, client)
    app.config["GEMINI_API_KEY"] = ""
    fake = FakeAssistant({"answer": "We ship worldwide.", "source_ids": []})
    monkeypatch.setattr("app.workflows.engine.get_provider", lambda cfg: fake)
    url = f"/api/v1/organizations/{org['id']}/assistant/messages"
    client.post(url, json={"content": "What is the shipping policy?"})
    drain()
    reply = client.get(url).get_json()["messages"][-1]
    assert reply["status"] == "answered" and reply["retrieval_mode"] == "keyword"
    assert any(i["title"] == "Shipping policy" for i in fake.calls[0]["input"]["workspace_data"])
