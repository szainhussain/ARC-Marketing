from app.agents.registry import AGENTS, AGENTS_BY_ID, agents_in_department_order
from app.ai.schemas import SCHEMAS_BY_TASK_TYPE
from app.models.deliverable import VALID_DELIVERABLE_TYPES


def test_twelve_distinct_agents():
    assert len(AGENTS) == 12
    assert len(AGENTS_BY_ID) == 12
    assert [a.number for a in agents_in_department_order()] == list(range(1, 13))
    assert len({a.task_type for a in AGENTS}) == 12
    assert len({a.instructions for a in AGENTS}) == 12


def test_every_agent_has_schema_and_deliverable_type():
    for agent in AGENTS:
        assert agent.task_type in SCHEMAS_BY_TASK_TYPE
        assert agent.task_type in VALID_DELIVERABLE_TYPES
        assert agent.version


def test_dependencies_are_readable():
    # An agent always may read what it depends on, except QA, which
    # deliberately reads a subset to stay within model token limits.
    for agent in AGENTS:
        if agent.agent_id != "marketing_ops":
            assert set(agent.depends_on) <= set(agent.reads), agent.agent_id


def test_no_agent_can_execute_external_actions():
    for agent in AGENTS:
        assert agent.external_action_policy != "auto_execute"
        assert agent.allowed_tools == ("ai.generate_structured",)
    assert AGENTS_BY_ID["paid_media"].external_action_policy == "never_executable_spend_is_human_only"
