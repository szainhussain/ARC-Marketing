"""Gunicorn settings. Starts the in-process agent worker when
RUN_EMBEDDED_WORKER=true (free hosting without a background-worker service)."""

import os

workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
timeout = 240
graceful_timeout = 30
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"


def post_worker_init(worker):
    app = worker.wsgi
    if app.config.get("RUN_EMBEDDED_WORKER"):
        from app.embedded_worker import start_embedded_worker

        start_embedded_worker(app)
