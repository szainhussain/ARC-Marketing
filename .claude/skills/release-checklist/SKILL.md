---
name: release-checklist
description: Pre-release checklist for Marketing Department Harness, grounded in the spec's Definition of Done. Use before telling the user a milestone or the app is "ready" for anything beyond local dev.
---

Before claiming any milestone, feature, or the app overall is "done" or
"ready," verify each of these against the current code — don't check a box
because it was true in an earlier session, and don't check a box for
something `docs/IMPLEMENTATION_PLAN.md` already lists as deferred without
re-confirming it's still deferred.

## Functional

- [ ] `python -m pytest -q` passes, 0 failures (run it now, don't trust a
      stale memory of the result)
- [ ] `cd frontend && npm run build && npm run lint` — 0 errors
- [ ] The relevant user journey was driven in a real browser this session
      (see `review-ui` skill), not just API-tested
- [ ] Business-profile-incomplete path still returns `needs_input`, not a
      crash or fabricated output
- [ ] No-AI-provider path still returns a clean `capability_unavailable`
      failure, not fabricated output (see `verify-workflow` skill)

## Governance

- [ ] Any new tenant-scoped resource has a passing isolation test (see
      `check-tenant-isolation` skill)
- [ ] Any new approval/external-action path re-validates immediately
      before execution (see `review-security` skill)
- [ ] No real secret committed — check `git diff` / `git status` for
      `.env`, credentials, or API keys before any commit

## Docs in sync

- [ ] `docs/IMPLEMENTATION_PLAN.md`'s milestone table reflects what's
      actually built, not aspirational scope
- [ ] `docs/TEST_REPORT.md` reflects the actual last test run, including
      what was *not* tested
- [ ] `docs/API.md` documents only routes that actually exist
- [ ] New architecture decisions are recorded in `docs/DECISIONS.md`
      (append a new entry; don't edit old ones away)
- [ ] `README.md`'s "Known limitations" section still accurately lists
      what's missing

## Readiness assessment (say this explicitly, don't let it be implied)

State one of: **local prototype**, **pilot candidate**, or **production
deployment candidate** — with reasons, per
`docs/DEPLOYMENT.md`'s own assessment at the end. Do not say
"production-ready" because the app runs locally; the spec is explicit that
this is not sufficient. If CI, backup/restore, monitoring/alerting, a live
AI key, or a live publishing channel are still missing, the honest answer
is not "production deployment candidate" — say so.

## Report format

List: features completed this session, files/modules changed, exact
setup/startup commands, env vars/credentials still needed (names only,
never values), tests run and their real results, browser verification
performed, integrations actually connected vs. merely prepared, security
controls implemented and remaining risks, known bugs, recommended next
milestone, and the readiness assessment above.
