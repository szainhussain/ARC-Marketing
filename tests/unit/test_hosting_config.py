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


def test_embedded_worker_processes_tasks(app, client, monkeypatch):
    import time

    from app.embedded_worker import start_embedded_worker
    from app.models.workflow_run import WorkflowRun
    from tests.conftest import complete_profile, create_campaign, create_org, register_and_login
    from tests.fakes import FakeProvider, use_provider
    import app.embedded_worker as ew

    use_provider(monkeypatch, FakeProvider())
    register_and_login(client)
    org = create_org(client)
    complete_profile(client, org["id"])
    campaign = create_campaign(client, org["id"])
    run = client.post(f"/api/v1/organizations/{org['id']}/campaigns/{campaign['id']}/runs",
                      headers={"Idempotency-Key": "emb"}).get_json()["workflow_run"]
    monkeypatch.setattr(ew, "_started", False)
    start_embedded_worker(app, poll_interval=0.05)
    from app.extensions import db

    for _ in range(200):
        db.session.expire_all()
        if db.session.get(WorkflowRun, run["id"]).status == "completed":
            break
        time.sleep(0.05)
    assert db.session.get(WorkflowRun, run["id"]).status == "completed"
