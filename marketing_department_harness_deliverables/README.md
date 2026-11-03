# Marketing Department Harness — Deliverables Pack

This pack contains five baseline specifications for the paid-pilot version of Marketing Department Harness.

1. `01_PRD.md` — product vision, personas, scope, requirements, stories, acceptance criteria, assumptions, release gates.
2. `02_UI_UX_SPEC.md` — sitemap, journeys, screen layouts, design system, responsive behavior, content rules, prototype checks.
3. `03_TECHNICAL_ARCHITECTURE.md` — Flask architecture, project layout, data model, state machines, API draft, AI workflow, security, deployment, testing.
4. `04_GOVERNANCE_AND_INTEGRATIONS.md` — approval policy, roles, connector lifecycle, privacy, prompt injection, budgets, audit and tests.
5. `05_IMPLEMENTATION_BACKLOG.md` — milestone-based implementation tasks, dependencies, acceptance criteria, definition of done, first coding instruction.

## Recommended use
Treat these as version 1.0 working specifications. Resolve the open decisions in the PRD before production integrations. Build a working vertical slice first; do not attempt to implement all 12 conceptual roles at once.

Recommended build order: M0 runnable skeleton → auth/tenant isolation → business profile → campaign brief → workflow persistence → AI provider adapter → campaign pack → review/versioning → approvals/audit → manual handoff → reporting → one live connector after a channel is selected.
