---
name: verify-workflow
description: Exercise the campaign workflow (strategy -> research -> plan -> content -> QA) end-to-end and confirm real, honest status reporting. Use after any change to app/agents/, app/ai/, or app/workflows/campaign_workflow.py.
---

The workflow has two paths to verify — both must be checked, not just the
happy one:

## 1. No-provider path (the default in this environment)

```bash
curl -X POST http://localhost:5000/api/v1/organizations/<org_id>/campaigns/<campaign_id>/runs \
  -H "Idempotency-Key: $(uuidgen || python -c 'import uuid;print(uuid.uuid4())')" \
  -b cookies.txt -H "X-CSRFToken: $TOKEN"
```

Expect: `status: "failed"`, first task's `error_summary` starts with
`capability_unavailable:`, no deliverables created. If instead you see
fabricated-looking content with no real `ANTHROPIC_API_KEY` set, that's a
regression of the single most important governance rule in this codebase
— stop and fix it before anything else.

## 2. Success path (requires a fake or real provider)

Prefer the fake-provider pattern over burning real API calls:
`tests/integration/test_workflow_success_path.py` monkeypatches
`app.workflows.campaign_workflow.get_provider` with a `FakeProvider`
returning canned schema-valid data for each `task_type`. Run it directly:

```bash
python -m pytest tests/integration/test_workflow_success_path.py -q
```

Confirm: all 5 tasks reach `completed`, the run reaches `completed`, one
`Deliverable` + `DeliverableVersion` per stage exists, and a `UsageRecord`
was written per stage with `is_actual: false`.

If you added a new stage: add its `task_type` to `FAKE_OUTPUTS` in that
test file and confirm it slots into the pipeline in the right order (check
`PIPELINE` in `campaign_workflow.py`).

## 3. Partial-failure path

Stop a stage partway (e.g. monkeypatch a `FakeProvider` that raises
`InvalidOutput` on stage 3) and confirm: stages 1–2's deliverables are
*not* deleted, the run is `failed` with a clear `error_summary` naming
which stage stopped it, and a retry (new idempotency key, or revisit after
fixing the cause) doesn't duplicate the already-completed stages' work.

## 4. Business-profile gating

With an incomplete business profile, confirm the run returns
`status: "needs_input"` with a specific list of missing fields in
`error_summary` *before* any AI call is attempted (no wasted provider
spend on an input you already know is incomplete) — see
`BusinessProfile.completeness_warnings()`.

Report which of these 4 you actually ran and their real results — "the
workflow works" without running at least #1 and #2 is not a verified
claim.
