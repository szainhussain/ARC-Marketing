# Billing and Plans

## Plans (provisional)

Seeded by `flask seed-plans` / first use (`app/services/platform_service.py`).
Prices and limits are **placeholders**, marked provisional everywhere they
appear, and editable as data (`plans.entitlements_json`) without a deploy.

| Plan | Price/mo | Runs/mo | Seats | Active campaigns | AI budget/mo (est.) | Agent executions/mo | Exports/mo |
|---|---|---|---|---|---|---|---|
| Launch | $149 | 10 | 2 | 3 | $10 | 300 | 50 |
| Growth | $399 | 40 | 5 | 10 | $40 | 1,500 | 300 |
| Scale | $999 | 150 | 15 | 50 | $150 | 6,000 | 2,000 |
| Enterprise | Custom | ∞ | ∞ | ∞ | Custom | ∞ | ∞ |

All plans include all 12 agents. New workspaces start on Launch,
`trialing`, for `TRIAL_DAYS` (14).

## Enforcement (backend)

| Limit | Where |
|---|---|
| Runs / month | `engine.enqueue_campaign_run` → 429 |
| Seats (members + open invites) | invitation create |
| Knowledge entries | knowledge create |
| Max run budget | caps workspace run budget at enqueue |
| AI budget / month, agent executions / month | `engine._budget_error` before each model call |
| Exports / month | `external_action_service.execute_manual_handoff` |

Budget alerts: notifications (and a `budget.threshold` webhook) at 80% and
100% of the monthly AI budget, once per month each.

## Subscription lifecycle

Plan state changes **only** in response to a verified payment event:

`checkout.session.completed` / `customer.subscription.updated` → plan set,
`active` · `invoice.paid` → recorded · `invoice.payment_failed` →
`past_due` + notification · `customer.subscription.deleted` → `cancelled`.

Events are stored in `billing_events` (unique provider+event id) so retries
and replays are ignored. Downgrades are refused while usage exceeds the
target plan's seats / campaigns / knowledge limits.

## Providers

| `BILLING_PROVIDER` | Behaviour |
|---|---|
| `test` (dev default) | In-app TEST MODE checkout; completing it sends a signed event through the real webhook path. No money moves. |
| `stripe` | Stripe Checkout Session via REST. **Implemented, not exercised** (no keys). |
| `none` (production default) | Checkout refused with a clear message |

## Enabling Stripe in production

1. Create Products/Prices in Stripe; set each plan's `stripe_price_ref`.
2. Set `BILLING_PROVIDER=stripe`, `STRIPE_SECRET_KEY`, and
   `BILLING_WEBHOOK_SECRET` (the endpoint's signing secret).
3. Add webhook endpoint `https://<api>/api/v1/billing/webhook` for the
   five event types above.
4. Test in Stripe test mode end to end before switching to live keys.
5. Not yet built: customer portal (payment method updates), proration,
   tax, invoices PDF, overage billing.
