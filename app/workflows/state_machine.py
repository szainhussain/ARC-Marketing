from app.services.errors import Conflict


def apply_transition(entity, new_status: str, transitions: dict[str, set]) -> None:
    """Mutates entity.status only if the transition is allowed; raises
    Conflict (409) otherwise. Keeps workflow/task state transitions in one
    place instead of duplicating the rules at every call site."""

    current_status = entity.status
    allowed = transitions.get(current_status, set())
    if new_status not in allowed:
        raise Conflict(
            f"Cannot move from '{current_status}' to '{new_status}'.",
            details=[{"field": "status", "issue": "invalid_transition"}],
        )
    entity.status = new_status
