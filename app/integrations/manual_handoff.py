from app.integrations.base import Connector


class ManualHandoffConnector(Connector):
    """The default execution adapter for the MVP. It never contacts a
    third-party API: it only packages approved content for the user to
    copy/download and post themselves. It is always "connected" and
    always succeeds at producing the export package, but it must never
    report the content as published — only the user's own confirmation
    (a separate, explicit step) can set publication_status to
    'manually_confirmed_published'."""

    name = "manual_handoff"

    def get_capabilities(self) -> dict:
        return {"supports_verification": False, "requires_manual_publication_confirmation": True}

    def health_check(self) -> dict:
        return {"state": "connected"}

    def validate_action(self, action_payload: dict) -> None:
        if not action_payload.get("content"):
            raise ValueError("No approved content to hand off.")

    def execute_action(self, action_payload: dict, idempotency_key: str) -> dict:
        return {
            "export_package": {
                "content": action_payload.get("content"),
                "destination_hint": action_payload.get("destination_hint", "manual"),
            }
        }

    def verify_action(self, action_reference: str) -> dict:
        return {"verification_supported": False}

    def disconnect(self) -> None:
        return None
