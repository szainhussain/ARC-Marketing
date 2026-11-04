class AIProviderError(Exception):
    """Base class for provider-neutral AI errors. Workflow stages catch
    these and persist a safe error summary instead of leaking provider
    internals or raw stack traces to the user."""


class ProviderUnavailable(AIProviderError):
    """No provider is configured (missing API key/package) or the
    configured provider cannot be reached. The workflow must degrade to a
    documented capability_unavailable state, never fabricate output."""


class RateLimited(AIProviderError):
    def __init__(self, message: str, retry_after_seconds: float | None = None):
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


class InvalidOutput(AIProviderError):
    """Model output could not be parsed or failed schema validation after
    the bounded repair/retry budget was exhausted."""


class BudgetExceeded(AIProviderError):
    pass


class AIRequestTimeout(AIProviderError):
    pass
