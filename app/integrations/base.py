class Connector:
    """Explicit contract every integration/connector implements, per the
    governance spec. The MVP only ships ManualHandoffConnector; a live
    connector (M11) is added only after a pilot channel is selected and
    API access is verified (see docs/DECISIONS.md)."""

    name = "base"

    def get_capabilities(self) -> dict:
        raise NotImplementedError

    def health_check(self) -> dict:
        raise NotImplementedError

    def validate_action(self, action_payload: dict) -> None:
        raise NotImplementedError

    def execute_action(self, action_payload: dict, idempotency_key: str) -> dict:
        raise NotImplementedError

    def verify_action(self, action_reference: str) -> dict:
        raise NotImplementedError

    def disconnect(self) -> None:
        raise NotImplementedError
