from app.agents.base import AgentSpec
from app.agents.definitions import AGENTS

AGENTS_BY_ID: dict[str, AgentSpec] = {a.agent_id: a for a in AGENTS}


def get_agent(agent_id: str) -> AgentSpec | None:
    return AGENTS_BY_ID.get(agent_id)


def agents_in_department_order() -> list[AgentSpec]:
    return sorted(AGENTS, key=lambda a: a.number)


def _validate_registry() -> None:
    """Fail fast at import if the registry is internally inconsistent,
    a typo in depends_on would otherwise only show up as a workflow that
    silently never progresses."""

    if len(AGENTS_BY_ID) != len(AGENTS):
        raise RuntimeError("Duplicate agent_id in registry")
    numbers = sorted(a.number for a in AGENTS)
    if numbers != list(range(1, len(AGENTS) + 1)):
        raise RuntimeError(f"Agent numbers must be 1..{len(AGENTS)} with no gaps: {numbers}")
    for agent in AGENTS:
        for dep in (*agent.depends_on, *agent.reads):
            if dep not in AGENTS_BY_ID:
                raise RuntimeError(f"{agent.agent_id} references unknown agent {dep!r}")
    # Cycle check via DFS.
    state: dict[str, int] = {}

    def visit(agent_id: str) -> None:
        if state.get(agent_id) == 1:
            raise RuntimeError(f"Dependency cycle through {agent_id}")
        if state.get(agent_id) == 2:
            return
        state[agent_id] = 1
        for dep in AGENTS_BY_ID[agent_id].depends_on:
            visit(dep)
        state[agent_id] = 2

    for agent in AGENTS:
        visit(agent.agent_id)


_validate_registry()
