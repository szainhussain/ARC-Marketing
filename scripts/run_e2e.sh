#!/usr/bin/env bash
# End-to-end journey with the deterministic fixture AI provider.
# Uses its own throwaway SQLite database (instance/e2e.db), so dev data and
# real provider quota are untouched. Expects the Vite dev server running
# (cd frontend && npm run dev) and nothing else on port 5000.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .venv/Scripts/activate ]; then source .venv/Scripts/activate; else source .venv/bin/activate; fi
export FLASK_APP=wsgi.py
export DATABASE_URL="sqlite:///e2e.db"
export AI_PROVIDER=fixture
export ALLOW_FIXTURE_PROVIDER=true
export BILLING_PROVIDER=test
export WORKER_RETRY_BASE_SECONDS=0

rm -f instance/e2e.db
flask db upgrade >/dev/null
flask seed-plans >/dev/null

flask run --port 5000 >/tmp/arc-e2e-web.log 2>&1 &
WEB=$!
flask worker --poll-interval 0.5 >/tmp/arc-e2e-worker.log 2>&1 &
WORKER=$!
trap 'kill $WEB $WORKER 2>/dev/null || true' EXIT

for _ in $(seq 1 40); do
  curl -sf http://localhost:5000/api/v1/health/live >/dev/null && break
  sleep 0.5
done

cd frontend
node e2e/journey.mjs
