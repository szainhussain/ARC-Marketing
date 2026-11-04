"""Run the agent worker loop as a daemon thread inside the web process.

For hosts whose free tier has no background-worker service (e.g. Render
free). Correctness doesn't depend on it: tasks are claimed atomically and
leased, so if the process sleeps or restarts mid-task the lease expires and
the task is retried. Prefer a separate `flask worker` service when you can.
"""

import logging
import threading
import time

log = logging.getLogger(__name__)
_started = False


def start_embedded_worker(app, poll_interval: float = 2.0) -> threading.Thread | None:
    global _started
    if _started:
        return None
    _started = True

    def loop():
        from app.extensions import db
        from app.workflows.engine import work_once

        log.warning("Embedded agent worker started (poll=%ss)", poll_interval)
        while True:
            did_work = False
            with app.app_context():
                try:
                    did_work = work_once()
                except Exception:  # noqa: BLE001 - one bad task must not kill the loop
                    log.exception("Embedded worker iteration failed")
                    db.session.rollback()
                finally:
                    db.session.remove()
            if not did_work:
                time.sleep(poll_interval)

    thread = threading.Thread(target=loop, name="arc-embedded-worker", daemon=True)
    thread.start()
    return thread
