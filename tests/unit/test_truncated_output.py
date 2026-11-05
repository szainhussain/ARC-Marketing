"""A reply cut off by the output-token limit is retried with a request for a
shorter answer, and the limit is large enough for long agent outputs."""

from types import SimpleNamespace

from marshmallow import Schema, fields

from app.ai import provider_adapter
from app.ai.provider_adapter import GroqProvider


class Out(Schema):
    title = fields.String(required=True)


class FakeCompletions:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def create(self, **kw):
        self.calls.append(kw)
        text, reason = self.replies.pop(0)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text), finish_reason=reason)],
                               usage=SimpleNamespace(prompt_tokens=10, completion_tokens=10))


def test_cut_off_reply_is_retried_with_a_shorter_request(monkeypatch):
    comp = FakeCompletions([('{"title": "A very long unfinished', "length"), ('{"title": "Short"}', "stop")])
    p = GroqProvider(api_key="k", model="m")
    monkeypatch.setattr(p, "_client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=comp)))
    result = p.generate_structured("social_media", {"x": 1}, Out)
    assert result.data == {"title": "Short"}
    assert all(c["max_tokens"] == provider_adapter._MAX_OUTPUT_TOKENS >= 8000 for c in comp.calls)
    assert "cut off" in comp.calls[1]["messages"][0]["content"]
