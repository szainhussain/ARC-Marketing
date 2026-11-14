// End-to-end journey (brief §21) against a running stack that uses the
// deterministic fixture AI provider. Run via scripts/run_e2e.sh.
//
//   FRONTEND_URL  default http://localhost:5174
//   API_URL       default http://localhost:5000/api/v1
//   SHOTS_DIR     default ./e2e/screenshots
import { chromium } from 'playwright'
import fs from 'node:fs'
import path from 'node:path'

const FRONTEND = process.env.FRONTEND_URL || 'http://localhost:5174'
const API = process.env.API_URL || 'http://localhost:5000/api/v1'
const SHOTS = process.env.SHOTS_DIR || path.resolve('e2e/screenshots')
fs.mkdirSync(SHOTS, { recursive: true })

const results = []
const consoleErrors = []
const serverErrors = []
let n = 0

async function step(name, fn) {
  const started = Date.now()
  try {
    await fn()
    results.push({ step: name, ok: true, ms: Date.now() - started })
    console.log(`PASS  ${name}`)
  } catch (err) {
    results.push({ step: name, ok: false, error: String(err).split('\n')[0], url: page.url() })
    console.log(`FAIL  ${name}: ${String(err).split('\n')[0]} (at ${page.url()})`)
    // what the page looked like when the step gave up; uploaded with the CI artifact
    await page.screenshot({ path: path.join(SHOTS, 'FAILED.png'), fullPage: true }).catch(() => {})
    throw err
  }
}

async function shot(page, name, fullPage = false) {
  n += 1
  await page.screenshot({ path: path.join(SHOTS, `${String(n).padStart(2, '0')}-${name}.png`), fullPage })
}

function watch(page) {
  page.on('console', (m) => {
    // A 401 on /me before sign-in is expected (not logged in yet).
    if (m.type() === 'error' && !/401 \(UNAUTHORIZED\)/.test(m.text())) consoleErrors.push(m.text())
  })
  page.on('response', (r) => {
    if (r.status() >= 500) serverErrors.push(`${r.status()} ${r.request().method()} ${r.url()}`)
  })
}

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } })
const page = await ctx.newPage()
watch(page)
const stamp = Date.now()
const email = `e2e-${stamp}@example.com`
let campaignUrl = ''
let orgId = ''

try {
  await step('public pages render', async () => {
    for (const p of ['/', '/product', '/agents', '/how-it-works', '/integrations', '/security', '/pricing', '/about', '/contact', '/docs', '/privacy', '/terms']) {
      await page.goto(FRONTEND + p, { waitUntil: 'networkidle' })
      await page.locator('main h1, main h2').first().waitFor()
    }
    await page.goto(FRONTEND + '/', { waitUntil: 'networkidle' })
    await page.getByRole('heading', { name: /A month of marketing, done/ }).waitFor()
    await shot(page, 'home')
    await page.getByRole('button', { name: 'Agent Operations Center' }).click()
    await page.getByRole('button', { name: 'Start' }).click()
    await page.waitForTimeout(2500)
    await shot(page, 'home-demo-running')
  })

  await step('1. register', async () => {
    await page.goto(FRONTEND + '/signup')
    await page.getByLabel('Full name').fill('E2E Owner')
    await page.getByLabel('Email').fill(email)
    await page.getByLabel('Password').fill('correct-horse-1')
    await page.getByLabel(/I agree to the/).check()
    await page.getByRole('button', { name: 'Create account' }).click()
    await page.waitForURL('**/create-workspace')
  })

  await step('2. create workspace', async () => {
    await page.getByLabel('Business or workspace name').fill('E2E Outfitters')
    await page.getByRole('button', { name: 'Create workspace' }).click()
    await page.waitForURL('**/app/onboarding')
    orgId = await page.evaluate(() => localStorage.getItem('activeOrganizationId'))
  })

  await step('3. onboarding wizard', async () => {
    await page.getByLabel('Business name').fill('E2E Outfitters')
    await page.getByLabel('Industry').fill('Outdoor gear')
    await page.getByRole('button', { name: 'Save and continue' }).click()
    await page.getByLabel('Main products/services').fill('Ultralight backpacks')
    await page.getByLabel('Best-fit audience / customer').fill('Weekend hikers, 25-45')
    await page.getByRole('button', { name: 'Save and continue' }).click()
    await page.getByLabel('Prohibited phrases').fill('guaranteed results')
    await page.getByRole('button', { name: 'Save and continue' }).click()
    await page.getByLabel('Primary campaign goal').fill('Increase first purchases')
    await page.getByRole('button', { name: 'Save and continue' }).click()
    await page.getByRole('button', { name: 'Save and continue' }).click()
    await shot(page, 'onboarding-review')
    await page.getByRole('button', { name: 'Finish and create a campaign' }).click()
    await page.waitForURL('**/app/campaigns/new')
  })

  await step('4. brand profile edit', async () => {
    await page.goto(FRONTEND + '/app/brand')
    await page.getByLabel('Tone of voice').fill('Warm, practical, outdoorsy')
    await page.getByRole('button', { name: 'Save brand profile' }).click()
    await page.getByText('Brand profile saved').waitFor()
  })

  await step('policy: require approval before agents start', async () => {
    await page.goto(FRONTEND + '/app/settings/automation', { waitUntil: 'networkidle' })
    const select = page.getByLabel('Mode for Agents research, plan and draft deliverables')
    await select.waitFor()
    const [resp] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/policies/agent_drafting') && r.request().method() === 'PATCH'),
      select.selectOption('require_approval'),
    ])
    if (!resp.ok()) throw new Error(`policy PATCH returned ${resp.status()}: ${await resp.text()}`)
  })

  await step('5-6. create campaign and run the department', async () => {
    await page.goto(FRONTEND + '/app/campaigns/new')
    await page.getByLabel('Campaign name').fill('E2E Spring Launch')
    await page.getByLabel('Objective').fill('Launch the ultralight line to weekend hikers')
    await page.getByRole('button', { name: 'Save and run the department' }).click()
    await page.waitForURL('**/workflow')
    campaignUrl = page.url().replace(/\/workflow$/, '')
    await page.getByRole('button', { name: 'Approve start' }).waitFor()
    await shot(page, 'run-awaiting-start')
  })

  await step('10. approval resumes the held workflow', async () => {
    await page.getByRole('button', { name: 'Approve start' }).click()
    await page.locator('.card-head h2 .status-pill').filter({ hasText: /Queued|Running|Completed/ }).waitFor()
  })

  await step('7. observe agents executing to completion', async () => {
    await page.locator('.card-head h2 .status-pill').filter({ hasText: 'Completed' }).waitFor({ timeout: 90000 })
    await page.getByRole('button', { name: 'List' }).click()
    await shot(page, 'run-completed', true)
  })

  await step('8. review deliverables', async () => {
    await page.goto(campaignUrl + '/deliverables')
    await page.getByRole('heading', { name: 'Strategy', exact: true }).waitFor()
    const count = await page.getByRole('button', { name: 'Request approval', exact: true }).count()
    if (count !== 12) throw new Error(`expected 12 deliverables awaiting approval, saw ${count}`)
    await page.getByRole('button', { name: 'Request approval', exact: true }).first().click()
    await page.getByText(/Approval:/).first().waitFor()
  })

  await step('9. approve in the approval inbox', async () => {
    await page.goto(FRONTEND + '/app/approvals')
    await page.getByText('If approved:').first().waitFor()
    await shot(page, 'approval-inbox')
    await page.getByRole('button', { name: 'Approve', exact: true }).first().click()
    await page.getByText('Nothing waiting').waitFor()
  })

  await step('11. Business Command Center shows real data', async () => {
    await page.goto(FRONTEND + '/app/dashboard')
    await page.getByRole('heading', { name: 'Business Command Center' }).waitFor()
    await page.locator('.kpi-tile', { hasText: 'Agent tasks completed' }).getByText('12').waitFor()
    // unconnected sources are named, never estimated
    await page.getByText(/Needs a connected source/).first().waitFor()
    await shot(page, 'command-center', true)
  })

  await step('12. Operations Center', async () => {
    await page.goto(FRONTEND + '/app/operations')
    await page.getByRole('heading', { name: 'Marketing Operations Center' }).waitFor()
    await page.locator('.wf-node').first().click()
    await page.getByText('Execution history').waitFor()
    await shot(page, 'operations-task-drawer')
    await page.keyboard.press('Escape')
  })

  await step('13. usage and audit records', async () => {
    await page.goto(FRONTEND + '/app/settings/usage')
    await page.getByText('Monthly workflow runs', { exact: false }).first().waitFor()
    await page.goto(FRONTEND + '/app/audit-log')
    await page.getByText('workflow.start_approved').waitFor()
    await page.getByText('approval.decided').first().waitFor()
  })

  await step('every app page renders', async () => {
    for (const p of ['/app/campaigns', '/app/agents', '/app/agents/cmo', '/app/tasks', '/app/calendar', '/app/content', '/app/assets',
      '/app/analytics', '/app/research', '/app/integrations', '/app/knowledge', '/app/team', '/app/billing', '/app/notifications',
      '/app/settings', '/app/settings/security', '/app/onboarding']) {
      await page.goto(FRONTEND + p, { waitUntil: 'networkidle' })
      await page.locator('main h1').first().waitFor()
    }
    await page.goto(FRONTEND + '/app/knowledge?status=proposed', { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: 'Approve' }).first().click()
  })

  await step('billing test-mode checkout', async () => {
    await page.goto(FRONTEND + '/app/billing')
    await page.getByRole('button', { name: 'Switch to Growth' }).click()
    await page.waitForURL('**/test-checkout**')
    await page.getByRole('button', { name: 'Complete test payment' }).click()
    await page.waitForURL('**/app/billing?checkout=success')
    await page.locator('.card', { hasText: 'Current plan' }).getByText('Growth').waitFor()
  })

  await step('mobile layout', async () => {
    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto(FRONTEND + '/app/dashboard', { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: 'Open navigation' }).click()
    await shot(page, 'mobile-nav')
    await page.goto(FRONTEND + '/', { waitUntil: 'networkidle' })
    await page.getByRole('button', { name: 'Open menu' }).click()
    await shot(page, 'mobile-home-menu')
    await page.setViewportSize({ width: 1440, height: 900 })
  })

  await step('14. unauthorized actions are blocked', async () => {
    const other = await browser.newContext()
    const p2 = await other.newPage()
    await p2.goto(FRONTEND + '/signup')
    await p2.getByLabel('Full name').fill('Intruder')
    await p2.getByLabel('Email').fill(`intruder-${stamp}@example.com`)
    await p2.getByLabel('Password').fill('correct-horse-1')
    await p2.getByLabel(/I agree to the/).check()
    await p2.getByRole('button', { name: 'Create account' }).click()
    await p2.waitForURL('**/create-workspace')
    const statuses = await p2.evaluate(async ({ api, org }) => {
      const csrf = (await (await fetch(`${api}/auth/csrf-token`, { credentials: 'include' })).json()).csrf_token
      const get = await fetch(`${api}/organizations/${org}/campaigns`, { credentials: 'include' })
      const post = await fetch(`${api}/organizations/${org}/operations/controls`, {
        method: 'PATCH', credentials: 'include', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ automation_paused: true }),
      })
      return [get.status, post.status]
    }, { api: API, org: orgId })
    if (statuses.some((s) => s !== 403)) throw new Error(`expected 403s, got ${statuses}`)
    await other.close()
  })
} catch {
  // recorded in results
} finally {
  await browser.close()
  const failed = results.filter((r) => !r.ok)
  const report = { passed: results.length - failed.length, failed: failed.length, results, consoleErrors, serverErrors }
  fs.writeFileSync(path.join(SHOTS, 'report.json'), JSON.stringify(report, null, 2))
  console.log(`\n${report.passed} passed, ${report.failed} failed; console errors: ${consoleErrors.length}; 5xx: ${serverErrors.length}`)
  if (consoleErrors.length) console.log(consoleErrors.slice(0, 10).join('\n'))
  if (serverErrors.length) console.log(serverErrors.slice(0, 10).join('\n'))
  process.exit(failed.length || serverErrors.length ? 1 : 0)
}
