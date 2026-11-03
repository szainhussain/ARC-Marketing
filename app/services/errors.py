class AppError(Exception):
    """Base class for errors that the API layer converts into the standard
    {"error": {"code", "message", "details"}} envelope."""

    http_status = 400
    code = "APP_ERROR"

    def __init__(self, message: str, details: list | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class ValidationError(AppError):
    http_status = 400
    code = "VALIDATION_ERROR"


class AuthenticationError(AppError):
    http_status = 401
    code = "AUTHENTICATION_ERROR"


class PermissionDenied(AppError):
    http_status = 403
    code = "PERMISSION_DENIED"


class NotFound(AppError):
    http_status = 404
    code = "NOT_FOUND"


class Conflict(AppError):
    http_status = 409
    code = "CONFLICT"


class RateLimited(AppError):
    http_status = 429
    code = "RATE_LIMITED"
