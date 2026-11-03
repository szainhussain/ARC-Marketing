---
name: review-ui
description: Browser-driven review of a Marketing Department Harness UI change — not just a visual check, but console errors, failed requests, accessibility (label association), and no-fabricated-data checks. Use for any frontend change before declaring it done.
---

A build succeeding is not proof a UI change works — this project caught
two real bugs (a label-association accessibility bug and a data-loss race
condition) that were invisible in code review and only surfaced by
actually running the app in a browser. Follow that standard.

## Setup

```bash
# Terminal 1
export FLASK_APP=wsgi.py && flask run

# Terminal 2
cd frontend && npm run dev
```

Confirm `frontend/.env.local`'s `VITE_API_BASE_URL` and the backend's
`.env` `FRONTEND_ORIGIN` use the **same hostname** (`localhost` in both,
not one `127.0.0.1`) — see `/CLAUDE.md`'s "Local dev gotcha." If Vite
printed "Port 5173 is in use, trying another one," update `FRONTEND_ORIGIN`
to match the actual port it bound to and restart the backend.

## Drive it

If no project browser-automation tool is already configured, use a
throwaway Playwright script outside the repo (the pattern that caught both
bugs in this build — see `docs/TEST_REPORT.md`):

```js
const { chromium } = require('playwright');
// nav -> fill/click through the flow your change touches -> screenshot ->
// check page.on('console') for errors and page.on('response') for 4xx/5xx
```

Install with `npm install playwright` in a scratch directory if it isn't
already available; the Chromium binary may need `npx playwright install
chromium` once.

## Check specifically

1. **Labels.** Every `<label>` has a matching `htmlFor`/`id`. If
   `getByLabel('Field name')` can't find your field, that's the same bug
   class as before — fix the markup, don't work around it in the test.
2. **Console.** Zero unexpected errors. (Two `401` entries from the
   initial unauthenticated `/me` probe before login are expected and
   benign — don't chase those.)
3. **Network.** No unexpected 4xx/5xx. A `400` on `/auth/register` with
   "CSRF session token is missing" usually means the hostname mismatch
   above, not a backend bug.
4. **No fabricated data.** Status labels, progress indicators, and
   deliverable content must reflect real persisted backend state — no
   hardcoded percentages, no fake "AI is thinking" animation not backed by
   an actual task status, no claiming something was published when it was
   only exported. This is an explicit product requirement, not a style
   preference.
5. **Loading/empty/error states.** Does the page handle zero campaigns,
   zero deliverables, a failed API call, and a slow response reasonably —
   not just the happy path with data already present?
6. **Re-run 2–3 times** if the change touches a `useEffect` that fetches
   on mount — React 19 StrictMode's double-invoke can produce a timing-
   dependent bug that doesn't reproduce on every single run (this is
   exactly how the onboarding data-loss bug was confirmed as a real race,
   not a one-off).

Report what you actually drove (which screens, which actions) and what you
saw — screenshots and console/network output, not "looks good."
