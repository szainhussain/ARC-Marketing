# Tools and Dependencies

## Adopted

| Tool/package | Why | Notes |
|---|---|---|
| Flask 3.1 + Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF, Flask-CORS | Core web framework per spec | Pinned versions in `requirements.txt` |
| Marshmallow 3.23 | Request/response and AI-output schema validation | Chosen over Pydantic for simpler native Flask integration; spec allows either, says "choose one consistently" |
| SQLAlchemy 2.1 + Alembic | ORM + migrations | |
| `anthropic` 0.40 (Python SDK) | AI provider adapter | Only imported inside `app/ai/provider_adapter.py`, lazily, so the app still runs with the package absent/provider unconfigured |
| `psycopg2-binary` 2.9.10 | PostgreSQL driver | In `requirements.txt` (Docker/production) only — excluded from `requirements-dev.txt` because it has no prebuilt wheel for the host's Python 3.14 in this session; see `docs/DECISIONS.md` D2 |
| `gunicorn` 23.0 | Production WSGI server (Docker) | |
| `pytest`, `pytest-cov` | Test framework | 22 tests, see `docs/TEST_REPORT.md` |
| React 19 + TypeScript + Vite 6 | Frontend | Scaffolded via `npm create vite@6.3.1 -- --template react-ts` |
| `react-router-dom` 6.28 | Client-side routing | |
| `playwright` 1.49 (dev-only, not a project dependency) | Browser verification during this build session | Used from a throwaway script outside the repo (see `docs/TEST_REPORT.md`); not added to `package.json` since it's a one-off verification tool, not a runtime or CI dependency. Recommend adding `@playwright/test` properly if ongoing browser regression testing is wanted. |

## Evaluated, not adopted (per the spec's repository-adoption rule)

| Item | Decision | Reason |
|---|---|---|
| UI UX Pro Max Skill (`nextlevelbuilder/ui-ux-pro-max-skill`) | Deferred | Not inspected for current install instructions/compatibility in this session; the built UI is functional but plain — worth evaluating in a dedicated design pass rather than installing speculatively |
| Everything Claude Code (`affaan-m/everything-claude-code`) | Deferred | Project-specific Skills were authored directly instead (see `.claude/skills/`) rather than importing an unreviewed external repository wholesale |
| Paperclip (multi-agent orchestration) | Deferred | The spec requires first determining whether the Flask workflow engine meets requirements — it does, for the current 5-stage fixed pipeline. Revisit only if/when the 12-agent expansion needs real branching orchestration (see `docs/12_AGENT_EXPANSION_ROADMAP.md`) |
| OpenWhispr, Chatwoot, AppFlowy, n8n, Higgsfield | Deferred | None required for the MVP pilot workflow; no concrete need identified this session |
| Open-SEO / CAP video tooling | Rejected (for now) | Spec itself flags these as ambiguous names that may refer to multiple projects — not guessing a repository |

## Known dependency risks

- `npm install` reported 15 vulnerabilities (12 moderate, 3 high) in the
  Vite scaffold's dev-dependency tree (eslint toolchain, typical for a
  fresh `create-vite` scaffold). Not run `npm audit fix --force` since
  that can introduce breaking changes to the build toolchain without
  review — flagging here for a deliberate follow-up rather than silently
  fixing or silently ignoring.
- `psycopg2-binary` is nearing end-of-life in favor of `psycopg` (v3);
  kept v2 to match the spec's own stack recommendation and existing
  Flask-SQLAlchemy ecosystem conventions. Revisit before a long-lived
  production deployment.
