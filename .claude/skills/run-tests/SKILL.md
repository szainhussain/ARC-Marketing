---
name: run-tests
description: Run the Marketing Department Harness test suite (backend pytest + frontend build/lint) and report real pass/fail results. Use when asked to run tests, verify the build, or before declaring any change done.
---

Run, in order, and report the actual output of each (never paraphrase a
command you didn't run):

1. **Backend tests**
   ```bash
   cd <repo root>
   source .venv/Scripts/activate   # create with `python -m venv .venv` + `pip install -r requirements-dev.txt` if missing
   python -m pytest -q
   ```
   22 tests currently exist (`tests/unit`, `tests/integration`,
   `tests/security`) — see `docs/TEST_REPORT.md` for what each group
   covers. A failing test is a real regression; investigate before
   reporting back, don't silently skip or delete it.

2. **Frontend build + lint**
   ```bash
   cd frontend
   npm run build   # tsc -b && vite build — must be 0 errors
   npm run lint     # eslint . — 2 pre-existing warnings in context files are expected; new errors are not
   ```

3. **If the change touches a backend route or model, also**: start the
   dev server (`export FLASK_APP=wsgi.py && flask run`) and hit the
   relevant endpoint with `curl`, or better, use `check-tenant-isolation`
   / `verify-workflow` if the change is in that territory.

Report exact pass/fail counts and any failure output — not "tests look
good" without having run them. If you had to fix something to get tests
passing, say what broke and what you changed.
