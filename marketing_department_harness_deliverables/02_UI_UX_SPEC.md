# Marketing Department Harness — UI/UX Specification
**Version:** 1.0  
**Design objective:** clear, calm, trustworthy, workflow-led SaaS for SMBs.

## 1. UX principles
- Lead with the work and business outcomes, not a novelty “AI office” animation.
- Make the next action obvious: provide context, review a deliverable, resolve a blocker, or approve an action.
- Show what AI is doing, why it needs input, and what will happen next.
- Keep internal reasoning hidden; expose concise rationale, sources, assumptions, and decisions.
- Never make an external action look complete until confirmed.
- Keep review and approval states visually distinct.
- Design for desktop first, then make all core workflows usable on mobile.
- Prefer progressive disclosure over long forms or dense configuration.

## 2. Information architecture / sitemap
- Public
  - Home
  - How it works
  - Use cases
  - Plans / pilot
  - Trust, security & privacy
  - Sign in / Create account
- App
  - Workspace switcher
  - Overview
  - Campaigns
    - Campaign list
    - New campaign brief
    - Campaign workspace
    - Deliverables
  - Tasks
  - Approvals
  - Reports
  - Brand & business profile
  - Integrations
  - Team & permissions
  - Usage & billing
  - Settings / data export / deletion request
- Platform administration (separate access boundary)
  - Service health
  - Workflow/run diagnostics
  - Usage and abuse controls
  - Support / incident tooling

## 3. Core navigation
Desktop left navigation:
1. Overview
2. Campaigns
3. Tasks
4. Approvals (show count of pending items)
5. Reports
6. Brand profile
7. Integrations
8. Team & settings

Top bar:
- Current organization/workspace
- Search (later if needed)
- Help
- Notifications
- User menu

Mobile:
- Bottom navigation for Overview, Campaigns, Tasks, Approvals
- Secondary destinations under “More”
- Keep the primary action available without horizontal scrolling.

## 4. Key screens
### 4.1 Public landing page
Sections:
1. Clear headline: “Your coordinated AI marketing team.”
2. Subheading explaining plan, create, review, and controlled execution.
3. Primary CTA: “Start a pilot” / “Create workspace”.
4. Workflow strip: Brief → Plan → Create → Review → Execute.
5. Example deliverables and sample workflow timeline.
6. Approval and privacy explanation.
7. Pilot scope and limitations.
8. Pricing or pilot offer, only once validated.
9. FAQ and contact.

Do not imply all 12 department roles are fully autonomous in the first release.

### 4.2 Sign-up and workspace creation
- Email/password or chosen identity provider.
- Verify email before sensitive setup where required.
- Create organization name and workspace slug.
- Display concise privacy and terms links.
- Show loading, failure, retry, and success states.
- Prevent account enumeration in recovery flows.

### 4.3 Progressive onboarding
Use a short wizard with autosave and a progress indicator. Ask only questions needed to produce a useful first campaign.

**Step 1 — Business basics**
- Business name
- Website (optional)
- Industry/category
- Countries/regions served
- Business type: B2B, B2C, both, nonprofit/other

**Step 2 — Offer and audience**
- Main products/services
- Best-fit audience/customer
- Customer problem solved
- Differentiators / proof points
- Primary campaign goal

**Step 3 — Brand**
- Tone of voice
- Preferred and prohibited phrases
- Logo, brand guide, product/service files
- Claims that must not be made
- Competitors (optional)

**Step 4 — Channels and constraints**
- Channels used
- Available budget range (optional)
- Campaign dates
- Approval owner(s)
- Industry/legal restrictions or disclaimers

**Step 5 — Review**
- Summary with edit links
- Clear distinction between required and optional data
- CTA: “Save profile and create first campaign”
- Secondary CTA: “Finish later”

Avoid asking the same question in every agent setup. Shared profile data should be reused; task-specific questions should appear only when material.

### 4.4 Overview dashboard
Primary purpose: show current work, blockers, approvals, and outcomes.

Recommended layout:
- Header: “Good morning” optional; workspace name; primary CTA “Create campaign”.
- Four compact summary cards: Active campaigns, Tasks needing attention, Pending approvals, Usage this period.
- “Needs your attention” list sorted by urgency.
- Active campaigns table/list with stage, owner, next action, last update.
- Recent activity feed with actor, event, timestamp.
- Performance snapshot only when real connected data exists.
- Empty state with one clear next step.

Do not display made-up ROI or generic vanity metrics.

### 4.5 Campaign creation / brief
Use a structured form, not a blank chat-only interface.
Fields:
- Campaign name
- Objective (awareness, engagement, leads, sales, retention, launch, other)
- Offer/product/service
- Target audience
- Geography/language
- Channel(s)
- Key message / CTA
- Start/end dates
- Budget guidance (optional; never treated as authorization to spend)
- Success metrics
- Required facts and proof
- Constraints / prohibited claims
- Attachments
- “What else should the team know?” free text

Behavior:
- Autosave draft.
- Inline examples and plain-language help.
- “Review brief” step before running.
- Clarification questions limited to material gaps.
- Explicit “Generate plan and draft content” action with estimated usage if available.

### 4.6 Campaign workspace
Three-column desktop layout when width allows:
- Left: campaign stages and task list.
- Center: selected deliverable / brief / plan.
- Right: status, evidence/assumptions, comments, version history, and next action.
On smaller screens, collapse to tabs or stacked panels.

Stage rail:
1. Brief
2. Research
3. Strategy
4. Plan
5. Content
6. Quality review
7. Approval
8. Execution
9. Results

Status vocabulary:
- Draft
- Queued
- In progress
- Needs your input
- Awaiting approval
- Approved
- Executing
- Completed
- Failed
- Cancelled
- Verification required

Each status must have a clear textual label; do not rely on color alone.

### 4.7 Deliverable review
Header:
- Deliverable title
- Type (strategy, calendar, copy, creative brief, report)
- Version number
- Status
- Produced by workflow stage
- Last updated

Body:
- Editable content or readable preview
- Evidence/source notes when applicable
- “Known facts”, “Assumptions”, and “Needs confirmation” sections as relevant
- Comments and revision history

Actions:
- Edit
- Request changes
- Approve this version
- Reject
- Export/copy
- “Prepare external action” only if the deliverable is eligible

When requesting changes, collect a concise reason and preserve the previous version.

### 4.8 Approval center
List columns/cards:
- Action/deliverable
- Destination/account
- Exact version
- Requested by / requested at
- Risk/impact level
- Planned schedule
- Estimated spend, if any
- Status

Approval detail must show:
- Exact content or action payload
- Account/destination and audience
- Timing
- Cost/spend limit if applicable
- Relevant policy warnings
- What approval authorizes—and what it does not authorize
- Approve, reject, or request changes

Require an explicit confirmation for high-impact actions. Do not treat opening a screen, silence, or prior approval of another version as consent.

### 4.9 Tasks
Filters: status, campaign, stage, assigned capability, due date, needs input.
Task details:
- Purpose and expected output
- Dependencies
- Inputs and linked files
- Current state and attempts
- Output and error message
- Retry/cancel controls only when safe
- Audit/activity history

### 4.10 Reports
- Workflow summary: completed stages, deliverables, approvals, execution outcomes.
- Usage/cost summary with period and data source.
- Business outcomes only from connected, attributable data.
- Label estimates and recommendations.
- Provide CSV export later if it materially helps pilot customers.
- Never conflate content production with business performance.

### 4.11 Business profile and brand library
- Structured profile with edit history.
- Brand assets and documents with filename, type, date, and access scope.
- Mark outdated or superseded documents.
- Show how profile data is reused.
- Allow delete/export requests subject to documented retention and legal requirements.
- Do not expose a document to another organization.

### 4.12 Integrations
For each connector:
- Purpose and permissions requested
- Connected account identity
- Granted scopes
- Last health check
- Connect / reconnect / disconnect
- Data accessed and actions enabled
- Clear warnings for write permissions
- Never display tokens or secrets.

### 4.13 Optional “AI office” visualization
May be used as a secondary view or onboarding illustration, not the primary control surface. Each agent/role should map to real tasks and states. Avoid fake animation that suggests work is happening when no workflow run exists. Every status should be traceable to persisted backend records.

## 5. Design system
### Visual direction
Professional, warm, focused, modern B2B SaaS. Use a restrained neutral base and one primary accent. Reserve strong semantic colors for meaningful statuses. Avoid overly playful robot imagery or “sci-fi command center” visuals.

### Typography
- Use a readable sans-serif family with a clear hierarchy.
- Body text 14–16 px equivalent; dense data tables can be smaller but must remain readable.
- Clear heading hierarchy and generous line spacing.

### Layout and spacing
- 8-point spacing scale.
- Content max width around 1200–1360 px for desktop views.
- Use consistent cards, dividers, and alignment.
- Prefer one dominant CTA per screen.
- Avoid excessive cards within cards.

### Components
- Button: primary, secondary, tertiary, destructive, disabled/loading.
- Input: text, textarea, select, date, file upload.
- Status badge with icon + text.
- Progress/stage rail.
- Task row and campaign row.
- Deliverable viewer/editor.
- Approval summary panel.
- Activity timeline.
- Empty state.
- Toast and inline error.
- Confirmation modal for consequential actions.
- Usage meter.
- Source/assumption panel.
- Version history.

### Interaction standards
- Every async action has loading, success, failure, and retry states.
- Disable duplicate submission while request is in flight.
- Use optimistic UI only for reversible low-risk changes.
- Require server confirmation for approval and external action status.
- Keep unsaved changes visible and recoverable.
- Keyboard-accessible controls and focus states.
- Never use color as the only status signal.

## 6. Responsive behavior
- Desktop: full navigation and three-column campaign workspace.
- Tablet: collapsible sidebar and two-column or tabbed workspace.
- Mobile: stacked layout, simplified stage navigation, single-column review, approval actions easy to reach.
- Wide tables convert to cards or horizontal scrolling with a clear cue.
- File uploads and editing must remain usable on mobile.

## 7. Content and microcopy rules
- Use plain, direct language.
- Prefer “AI is preparing a draft” over “agent is thinking”.
- Prefer “Needs your approval before publishing” over vague “action required”.
- Explain why a blocker exists and how to resolve it.
- Never say “published”, “sent”, or “completed” before verified confirmation.
- Mark AI-generated assumptions and unverified recommendations.
- Be explicit about cost, destination, and permission scope before external actions.

## 8. Prototype acceptance checklist
- A first-time user can understand the product promise in under one minute.
- A user can complete onboarding without answering optional questions.
- A user can create a campaign and understand what happens next.
- Workflow status is visible and not dependent on animation.
- A reviewer can inspect exact content/version and approve or request changes.
- An unapproved action cannot be initiated from the UI or API.
- Errors provide a useful next step without exposing secrets.
- Main flows work at mobile widths and with keyboard navigation.
