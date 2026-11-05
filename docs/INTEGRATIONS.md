# Integrations

Source of truth: `app/integrations/catalog.py`, served at
`GET /api/v1/public/integrations` and shown on `/integrations` and
`/app/integrations`.

## Statuses

| Status | Meaning |
|---|---|
| `available_tested` | Implemented and covered by tests |
| `architecture_supported` | Connector contract exists; no live connector |
| `planned` | Nothing built |

## What exists

- **Manual export** to Meta/Instagram, Google Ads (RSA) and TikTok Ads
  formats (`app/integrations/export_formats.py`). Approved content only;
  never posts or spends. Admins can disable each destination per
  workspace; the export endpoint refuses a disabled destination.
- **Outbound webhooks** (`app/services/webhook_service.py`): events
  `run.completed`, `run.failed`, `approval.requested`, `approval.decided`,
  `deliverable.created`, `budget.threshold`.
  - Headers: `ARC-Event-Id`, `ARC-Event-Type`, `ARC-Event-Version`
    (`2026-11-01`), `ARC-Signature: t=<unix>,v1=<hex>` where `v1 =
    HMAC-SHA256(secret, "<t>.<raw body>")`.
  - Receivers: verify with constant-time compare; reject `|now - t| >
    300s` (replay); dedupe on `ARC-Event-Id`.
  - Delivery: from the worker, HTTPS only, hostname resolved and every
    address must be public, no redirects, 10s timeout, 6 attempts with
    exponential backoff (30s doubling).
- **Payment webhooks** (`POST /api/v1/billing/webhook`): Stripe-format
  signature, same 5-minute tolerance, idempotent on event id.

## Live connector: WordPress.com (blog publishing)

- **Setup (once, by the ARC operator):** create an app at
  https://developer.wordpress.com/apps with redirect URL
  `https://usearc.vercel.app/api/v1/integrations/wordpress/callback`, then set
  `WORDPRESS_CLIENT_ID`, `WORDPRESS_CLIENT_SECRET` and
  `INTEGRATION_ENCRYPTION_KEY` on Render (never Vercel).
- **Per workspace:** an owner/admin clicks *Connect WordPress.com* under
  Integrations and picks a site. The token is encrypted at rest.
- **Publishing:** on an approved SEO deliverable, *Publish now* or *Save as
  draft* queues the post. The worker re-checks kill switch, approval and
  exact version, posts once (deterministic slug), reads it back, and only
  then shows *Live on your site* with the URL. See docs/DECISIONS.md D17.
- **Endpoints:** `POST /organizations/<id>/integrations/wordpress/connect`,
  `GET /integrations/wordpress/callback`,
  `DELETE /organizations/<id>/integrations/wordpress`,
  `POST /organizations/<id>/approvals/<id>/publish/wordpress`,
  `GET /organizations/<id>/deliverables/<id>/publications`.

## Live connector: outreach email (Brevo or Resend, client-owned)

- **Per workspace:** Outreach → *Connect sender*: provider, API key, verified
  from-address, from-name, postal address, optional reply-to. Brevo free
  plan sends up to 300 emails/day; Resend free plan 100/day (check current
  limits with the provider).
- **Flow:** upload a list (lawful basis + source + attestation) → create a
  batch (optionally from a PR-agent outreach draft) → request approval →
  approve → start. Pause, resume and cancel at any time. See D18.
- **Endpoints:** `/organizations/<id>/outreach` (overview), `/outreach/sender`
  (POST/DELETE), `/outreach/lists`, `/outreach/lists/<id>/contacts`,
  `/outreach/suppressions`, `/outreach/batches`, `/outreach/batches/<id>`
  (PATCH), `/outreach/batches/<id>/preview`,
  `/outreach/batches/<id>/{request-approval,approve,reject,start,pause,cancel}`,
  public `POST /api/v1/outreach/unsubscribe/<token>`.

## Ad launching (test platform now; Meta/Google when approved)

- **Guardrail:** Ads → *Set a cap* (owner/admin). 0 = launching off.
- **Flow:** approve a paid media plan → Ads → *Launch an ad* (pick an ad,
  daily budget, end date) → approver types the budget → the worker launches
  it on the test platform. Pause, resume, stop or *Stop all ads* any time;
  the kill switch pauses everything. See D19.
- **Going live:** Meta needs a Business-verified app with Marketing API
  `ads_management` (app review); Google needs a Google Ads manager account
  and an approved developer token. Each becomes a class in
  `ads_platforms.py` with the same methods; nothing else changes.
- **Endpoints:** `/organizations/<id>/ads`, `/ads/guardrail`, `/ads/launches`,
  `/ads/launches/<id>/decision`, `/ads/launches/<id>/{pause,resume,stop}`,
  `/ads/stop-all`.

## Live connectors — prerequisites (not built)

| Connector | You need to provide |
|---|---|
| Meta Graph (publishing) | Meta app, business verification, app review for `pages_manage_posts` / `instagram_content_publish`, OAuth redirect URL |
| LinkedIn | Marketing Developer Platform access |
| Google Ads API | Developer token (basic access), OAuth client, customer consent |
| GA4 | OAuth client with Analytics Data API |
| CMS / e-commerce | Per-platform API credentials |
| CRM / helpdesk | Per-platform OAuth app |
| Email delivery (for invites/resets) | Provider key (e.g. Resend) + verified domain |
| Image/video generation | Provider key + licensing review |

Per `CLAUDE.md`, a live publishing connector will not be added until you
choose a pilot channel and confirm API access. Any live connector must keep:
approval before first publish, kill-switch enforcement, idempotency keys,
and no agent-initiated spend changes.
