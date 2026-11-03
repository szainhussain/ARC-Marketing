import pytest

from app.services.errors import Conflict
from app.workflows.state_machine import apply_transition


class _FakeEntity:
    def __init__(self, status):
        self.status = status


def test_allowed_transition_succeeds():
    entity = _FakeEntity("pending")
    apply_transition(entity, "ready", {"pending": {"ready"}, "ready": set()})
    assert entity.status == "ready"


def test_disallowed_transition_raises_conflict():
    entity = _FakeEntity("completed")
    with pytest.raises(Conflict):
        apply_transition(entity, "running", {"completed": set()})
    # entity must be left unchanged on a rejected transition
    assert entity.status == "completed"
