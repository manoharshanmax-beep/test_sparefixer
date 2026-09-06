import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException
from marshmallow import ValidationError

logger = logging.getLogger("sparefixer")


class APIError(Exception):
    """Raised anywhere in the app for a controlled, client-facing error."""

    def __init__(self, message, status_code=400, payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload or {}

    def to_dict(self):
        body = {"error": self.message, "status": self.status_code}
        body.update(self.payload)
        return body


def register_error_handlers(app):

    @app.errorhandler(APIError)
    def handle_api_error(err: APIError):
        logger.warning("APIError: %s (%s)", err.message, err.status_code)
        return jsonify(err.to_dict()), err.status_code

    @app.errorhandler(ValidationError)
    def handle_validation_error(err: ValidationError):
        logger.warning("ValidationError: %s", err.messages)
        return jsonify({"error": "Invalid input", "details": err.messages, "status": 400}), 400

    @app.errorhandler(404)
    def handle_404(err):
        return jsonify({"error": "Resource not found", "status": 404}), 404

    @app.errorhandler(405)
    def handle_405(err):
        return jsonify({"error": "Method not allowed", "status": 405}), 405

    @app.errorhandler(400)
    def handle_400(err):
        message = getattr(err, "description", "Bad request")
        return jsonify({"error": message, "status": 400}), 400

    @app.errorhandler(HTTPException)
    def handle_http_exception(err: HTTPException):
        return jsonify({"error": err.description, "status": err.code}), err.code

    @app.errorhandler(500)
    def handle_500(err):
        logger.exception("Unhandled server error")
        return jsonify({"error": "Internal server error", "status": 500}), 500

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        # Catch-all so a stray exception never leaks a raw traceback to the client.
        logger.exception("Unexpected exception: %s", err)
        return jsonify({"error": "Internal server error", "status": 500}), 500
