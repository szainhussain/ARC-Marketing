import logging
import uuid

from flask import g, jsonify
from werkzeug.exceptions import HTTPException

from app.services.errors import AppError

logger = logging.getLogger("app")


def register_error_handlers(app):
    @app.before_request
    def _assign_request_id():
        g.request_id = str(uuid.uuid4())

    @app.after_request
    def _attach_request_id_header(response):
        response.headers["X-Request-Id"] = getattr(g, "request_id", "")
        return response

    @app.errorhandler(AppError)
    def handle_app_error(error: AppError):
        request_id = getattr(g, "request_id", str(uuid.uuid4()))
        return (
            jsonify(
                {
                    "error": {
                        "code": error.code,
                        "message": error.message,
                        "details": error.details,
                        "request_id": request_id,
                    }
                }
            ),
            error.http_status,
        )

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        request_id = getattr(g, "request_id", str(uuid.uuid4()))
        return (
            jsonify(
                {
                    "error": {
                        "code": "HTTP_ERROR",
                        "message": error.description or "Request error.",
                        "details": [],
                        "request_id": request_id,
                    }
                }
            ),
            error.code or 500,
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        request_id = getattr(g, "request_id", str(uuid.uuid4()))
        logger.exception("Unhandled error [request_id=%s]", request_id)
        return (
            jsonify(
                {
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Something went wrong. Please try again.",
                        "details": [],
                        "request_id": request_id,
                    }
                }
            ),
            500,
        )
