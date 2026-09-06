import logging
import sys
import time
import uuid
from logging.handlers import RotatingFileHandler

from flask import g, request


def configure_logging(app):
    level = getattr(logging, app.config.get("LOG_LEVEL", "INFO").upper(), logging.INFO)

    logger = logging.getLogger("sparefixer")
    logger.setLevel(level)
    logger.propagate = False

    if not logger.handlers:
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(fmt)
        logger.addHandler(console_handler)

        # File logging is best-effort: on read-only filesystems (some PaaS
        # dynos) this can fail silently and we fall back to stdout only,
        # which Render/Heroku both capture anyway.
        try:
            file_handler = RotatingFileHandler("sparefixer.log", maxBytes=2_000_000, backupCount=3)
            file_handler.setFormatter(fmt)
            logger.addHandler(file_handler)
        except OSError:
            logger.warning("File logging unavailable; using stdout only")

    _register_request_hooks(app, logger)
    return logger


def _register_request_hooks(app, logger):

    @app.before_request
    def _start_timer():
        g._request_id = uuid.uuid4().hex[:8]
        g._start_time = time.time()
        logger.info(
            "--> [%s] %s %s from %s",
            g._request_id, request.method, request.path, request.remote_addr,
        )

    @app.after_request
    def _log_response(response):
        duration_ms = (time.time() - getattr(g, "_start_time", time.time())) * 1000
        request_id = getattr(g, "_request_id", "-")
        logger.info(
            "<-- [%s] %s %s %s (%.1fms)",
            request_id, request.method, request.path, response.status_code, duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response

    @app.teardown_request
    def _log_exception(exc):
        if exc is not None:
            logger.error("Exception during request %s: %s", request.path, exc)
