from app.config import _database_url, _origins


def test_postgres_scheme_is_normalised(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host/db?sslmode=require")
    assert _database_url() == "postgresql+psycopg2://u:p@host/db?sslmode=require"


def test_pasted_psql_snippet_is_tolerated(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "  psql 'postgresql://u:p@host/db?sslmode=require'  ")
    assert _database_url() == "postgresql+psycopg2://u:p@host/db?sslmode=require"


def test_explicit_driver_is_kept(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://u:p@host/db")
    assert _database_url() == "postgresql+psycopg2://u:p@host/db"


def test_multiple_frontend_origins(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://a.vercel.app/, https://app.example.com")
    assert _origins() == ["https://a.vercel.app", "https://app.example.com"]


def test_embedded_worker_processes_tasks(tmp_path, monkeypatch):
    import threading
    import time

    from app import create_app
    from app.config import TestingConfig
    from app.embedded_worker import start_embedded_worker
    from app.extensions import db
    from app.models.workflow_run import WorkflowRun
    from tests.conftest import complete_profile, create_campaign, create_org, register_and_login
    from tests.fakes import FakeProvider, use_provider
    import app.embedded_worker as ew

    # Not the shared `app` fixture: its in-memory SQLite is one connection shared by every
    # thread (StaticPool), and SQLite connections aren't safe for concurrent use, so the
    # worker thread and this test's polling could clash (seen in CI as a lookup returning None).
    # A file database gives each thread its own connection.
    monkeypatch.setattr(TestingConfig, "SQLALCHEMY_DATABASE_URI", f"sqlite:///{tmp_path / 'worker.db'}")
    app = create_app("testing")
    client = app.test_client()
    stop = threading.Event()
    worker = None
    with app.app_context():
        db.create_all()
        try:
            use_provider(monkeypatch, FakeProvider())
            register_and_login(client)
            org = create_org(client)
            complete_profile(client, org["id"])
            campaign = create_campaign(client, org["id"])
            run = client.post(f"/api/v1/organizations/{org['id']}/campaigns/{campaign['id']}/runs",
                              headers={"Idempotency-Key": "emb"}).get_json()["workflow_run"]
            monkeypatch.setattr(ew, "_started", False)
            worker = start_embedded_worker(app, poll_interval=0.05, stop=stop)

            status = None
            for _ in range(200):
                db.session.expire_all()
                status = db.session.get(WorkflowRun, run["id"]).status
                if status == "completed":
                    break
                time.sleep(0.05)
            assert status == "completed"
        finally:
            stop.set()
            if worker:
                worker.join(timeout=5)
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
