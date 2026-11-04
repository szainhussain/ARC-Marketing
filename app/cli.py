import logging
import signal
import time

import click
from flask import current_app

log = logging.getLogger(__name__)


def register_cli(app) -> None:
    @app.cli.command("purge-deleted-workspaces")
    def purge_deleted_workspaces() -> None:
        """Permanently delete workspaces whose deletion grace period has passed."""

        from app.services.data_lifecycle import purge_due_workspaces

        click.echo(f"Purged {purge_due_workspaces()} workspace(s).")

    @app.cli.command("seed-plans")
    def seed_plans() -> None:
        """Insert the default (provisional) plans if none exist."""

        from app.extensions import db
        from app.services.platform_service import ensure_plans_seeded

        ensure_plans_seeded()
        db.session.commit()
        click.echo("Plans present.")

    @app.cli.command("worker")
    @click.option("--once", is_flag=True, help="Process everything claimable now, then exit.")
    @click.option("--poll-interval", default=2.0, show_default=True, help="Seconds to wait when idle.")
    def worker(once: bool, poll_interval: float) -> None:
        """Run the agent task worker (separate from the web server)."""

        from app.extensions import db
        from app.workflows.engine import drain, work_once

        if once:
            click.echo(f"Processed {drain()} task(s).")
            return

        stopping = {"flag": False}

        def _stop(*_):
            stopping["flag"] = True
            click.echo("Stopping after the current task...")

        signal.signal(signal.SIGINT, _stop)
        signal.signal(signal.SIGTERM, _stop)

        click.echo(
            f"ARC worker started (provider={current_app.config.get('AI_PROVIDER')}, "
            f"poll={poll_interval}s). Ctrl+C to stop."
        )
        while not stopping["flag"]:
            try:
                did_work = work_once()
            except Exception:  # noqa: BLE001 - one bad task must not kill the worker
                log.exception("Worker iteration failed")
                db.session.rollback()
                did_work = False
            finally:
                db.session.remove()
            if not did_work:
                time.sleep(poll_interval)
