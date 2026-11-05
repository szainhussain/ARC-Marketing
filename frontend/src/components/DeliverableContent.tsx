import type { JSX, ReactNode } from 'react'

type Json = Record<string, unknown>

function asStringList(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.filter((v): v is string => typeof v === 'string')
}

function Section({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="deliverable-section">
      <div className="section-label">{label}</div>
      {children}
    </div>
  )
}

function BulletList({ items }: { items: string[] }) {
  if (items.length === 0) return null
  return (
    <ul className="deliverable-list">
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  )
}

function ChipList({ items }: { items: string[] }) {
  if (items.length === 0) return null
  return (
    <div>
      {items.map((item, i) => (
        <span className="tag-chip" key={i}>
          {item}
        </span>
      ))}
    </div>
  )
}

function Strategy({ content }: { content: Json }) {
  return (
    <>
      {typeof content.strategic_direction === 'string' && (
        <Section label="Strategic direction">
          <p className="deliverable-prose">{content.strategic_direction}</p>
        </Section>
      )}
      <Section label="Key objectives">
        <BulletList items={asStringList(content.key_objectives)} />
      </Section>
      <Section label="Assumptions">
        <BulletList items={asStringList(content.assumptions)} />
      </Section>
      <Section label="Sources">
        <BulletList items={asStringList(content.sources)} />
      </Section>
    </>
  )
}

function ResearchNotes({ content }: { content: Json }) {
  return (
    <>
      {typeof content.scope_note === 'string' && content.scope_note && (
        <Section label="Scope">
          <p className="deliverable-prose muted">{content.scope_note}</p>
        </Section>
      )}
      <Section label="Audience hypotheses">
        <BulletList items={asStringList(content.audience_hypotheses)} />
      </Section>
      <Section label="Competitor notes">
        <BulletList items={asStringList(content.competitor_notes)} />
      </Section>
      <Section label="Assumptions">
        <BulletList items={asStringList(content.assumptions)} />
      </Section>
      <Section label="Sources">
        <BulletList items={asStringList(content.sources)} />
      </Section>
    </>
  )
}

function CampaignPlan({ content }: { content: Json }) {
  const timeline = Array.isArray(content.timeline) ? (content.timeline as Json[]) : []
  return (
    <>
      {typeof content.summary === 'string' && (
        <Section label="Summary">
          <p className="deliverable-prose">{content.summary}</p>
        </Section>
      )}
      <Section label="Channels">
        <ChipList items={asStringList(content.channels)} />
      </Section>
      {timeline.length > 0 && (
        <Section label="Timeline">
          {timeline.map((phase, i) => (
            <div className="timeline-phase" key={i}>
              <div className="phase-title">
                {typeof phase.phase === 'string' ? phase.phase : `Phase ${i + 1}`}
              </div>
              <BulletList items={asStringList(phase.activities)} />
            </div>
          ))}
        </Section>
      )}
      <Section label="Success metrics">
        <BulletList items={asStringList(content.success_metrics)} />
      </Section>
      <Section label="Assumptions">
        <BulletList items={asStringList(content.assumptions)} />
      </Section>
    </>
  )
}

function ContentPack({ content }: { content: Json }) {
  const variants = Array.isArray(content.variants) ? (content.variants as Json[]) : []
  return (
    <>
      {typeof content.creative_brief === 'string' && (
        <Section label="Creative brief">
          <p className="deliverable-prose">{content.creative_brief}</p>
        </Section>
      )}
      {variants.length > 0 && (
        <Section label="Channel variants">
          {variants.map((v, i) => (
            <div className="variant-card" key={i}>
              {typeof v.channel === 'string' && <div className="channel-tag">{v.channel}</div>}
              {typeof v.headline === 'string' && <div className="headline">{v.headline}</div>}
              {typeof v.body === 'string' && <p className="deliverable-prose">{v.body}</p>}
            </div>
          ))}
        </Section>
      )}
      {typeof content.calendar_notes === 'string' && content.calendar_notes && (
        <Section label="Calendar notes">
          <p className="deliverable-prose muted">{content.calendar_notes}</p>
        </Section>
      )}
    </>
  )
}

function QAReport({ content }: { content: Json }) {
  const passed = content.passed === true
  const checked = asStringList(content.checked)
  const issues = asStringList(content.issues)
  return (
    <>
      <Section label="Result">
        <span className={`status-pill ${passed ? 'completed' : 'failed'}`}>
          {passed ? 'Passed' : 'Needs attention'}
        </span>
      </Section>
      {checked.length > 0 && (
        <Section label="Checks performed">
          {checked.map((c, i) => (
            <div className="qa-check" key={i}>
              <span className="dot" />
              {c}
            </div>
          ))}
        </Section>
      )}
      {issues.length > 0 && (
        <Section label="Issues">
          <BulletList items={issues} />
        </Section>
      )}
    </>
  )
}

// ---- Specialist-agent deliverables -------------------------------------
// Each new type declares which fields to show, in what order, with what
// label. Lists of objects render as small cards (first field as the title).

type FieldSpec = { key: string; label: string }

function humanKey(key: string) {
  const text = key.replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

const TITLE_KEYS = ['name', 'title', 'theme', 'segment', 'situation', 'item', 'target_type', 'page', 'day', 'channel']

function ObjectCard({ item }: { item: Json }) {
  const entries = Object.entries(item).filter(([, v]) => v !== '' && v !== null && v !== undefined)
  if (entries.length === 0) return null
  // Stored content has alphabetically sorted keys, so pick a meaningful
  // title field rather than whichever key happens to come first.
  const titleKey = TITLE_KEYS.find((k) => typeof item[k] === 'string' && item[k]) ?? entries[0][0]
  const title = item[titleKey]
  const rest = entries.filter(([k]) => k !== titleKey)
  return (
    <div className="variant-card">
      <div className="headline">{String(title)}</div>
      {rest.map(([k, v]) => {
        if (typeof v === 'boolean') {
          return v ? (
            <span key={k} className="tag-chip warn-chip">
              {k === 'escalate_to_human' ? 'Needs a person' : humanKey(k)}
            </span>
          ) : null
        }
        if (Array.isArray(v)) {
          return v.length ? (
            <div key={k} className="small">
              <span className="muted">{humanKey(k)}:</span> {v.map(String).join(' · ')}
            </div>
          ) : null
        }
        return (
          <div key={k} className="small">
            <span className="muted">{humanKey(k)}:</span>{' '}
            {k === 'share_percent' ? `${v}%` : String(v)}
          </div>
        )
      })}
    </div>
  )
}

function FieldValue({ value }: { value: unknown }) {
  if (typeof value === 'string') return value ? <p className="deliverable-prose">{value}</p> : null
  if (typeof value === 'boolean') return <p className="deliverable-prose">{value ? 'Yes' : 'No'}</p>
  if (Array.isArray(value)) {
    if (value.length === 0) return null
    if (value.every((v) => typeof v === 'string')) return <BulletList items={value as string[]} />
    return (
      <>
        {value.map((v, i) =>
          v && typeof v === 'object' ? <ObjectCard key={i} item={v as Json} /> : <p key={i}>{String(v)}</p>,
        )}
      </>
    )
  }
  return null
}

function fieldRenderer(fields: FieldSpec[]) {
  return function Renderer({ content }: { content: Json }) {
    return (
      <>
        {fields.map(({ key, label }) => {
          const value = content[key]
          const empty = value === undefined || value === '' || (Array.isArray(value) && value.length === 0)
          if (empty) return null
          return (
            <Section key={key} label={label}>
              <FieldValue value={value} />
            </Section>
          )
        })}
      </>
    )
  }
}

const SocialCalendar = fieldRenderer([
  { key: 'channels', label: 'Channels' },
  { key: 'calendar_entries', label: 'Post calendar' },
  { key: 'community_guidelines', label: 'Community guidelines' },
  { key: 'escalation_triggers', label: 'Escalate to a person when' },
  { key: 'assumptions', label: 'Assumptions' },
])

const OutreachPlan = fieldRenderer([
  { key: 'target_profiles', label: 'Target profiles (no specific people or contacts)' },
  { key: 'outreach_drafts', label: 'Outreach drafts — for your review' },
  { key: 'event_ideas', label: 'Event ideas' },
  { key: 'assumptions', label: 'Assumptions' },
])

const PaidMediaPlan = fieldRenderer([
  { key: 'campaign_structure', label: 'Campaign structure' },
  { key: 'budget_allocation_recommendation', label: 'Recommended budget split (you decide spend)' },
  { key: 'bid_strategy', label: 'Bid strategy' },
  { key: 'experiments', label: 'Experiments' },
  { key: 'kpi_targets', label: 'KPI targets' },
  { key: 'assumptions', label: 'Assumptions' },
])

const SiteOptimizationFields = fieldRenderer([
  { key: 'keyword_themes', label: 'Keyword themes' },
  { key: 'landing_page_recommendations', label: 'Landing page recommendations' },
  { key: 'metadata_drafts', label: 'Page title & meta drafts' },
  { key: 'conversion_experiments', label: 'Conversion experiments' },
  { key: 'assumptions', label: 'Assumptions' },
])

/** The agent's markdown subset ('## ' headings, paragraphs, '- ' bullets, **bold**), rendered as React text only. */
export function ArticleBody({ markdown }: { markdown: string }) {
  const bold = (s: string) =>
    s.split(/(\*\*[^*]+\*\*)/g).map((p, i) => (p.startsWith('**') && p.endsWith('**') ? <strong key={i}>{p.slice(2, -2)}</strong> : p))
  const out: ReactNode[] = []
  let bullets: string[] = []
  let para: string[] = []
  const flush = () => {
    if (para.length) out.push(<p key={`p${out.length}`}>{bold(para.join(' '))}</p>)
    if (bullets.length) out.push(<ul key={`u${out.length}`}>{bullets.map((b, i) => <li key={i}>{bold(b)}</li>)}</ul>)
    para = []
    bullets = []
  }
  for (const raw of markdown.replace(/\r/g, '').split('\n')) {
    const line = raw.trim()
    const head = line.match(/^#{1,4}\s+(.*)$/)
    const item = line.match(/^(?:[-*•]|\d+[.)])\s+(.*)$/)
    if (!line) flush()
    else if (head) {
      flush()
      out.push(<h4 key={`h${out.length}`}>{bold(head[1])}</h4>)
    } else if (item) {
      if (para.length) flush()
      bullets.push(item[1])
    } else {
      if (bullets.length) flush()
      para.push(line)
    }
  }
  flush()
  return <div className="article-body">{out}</div>
}

function SiteOptimizationPlan({ content }: { content: Json }) {
  const articles = Array.isArray(content.blog_articles) ? (content.blog_articles as Json[]) : []
  return (
    <>
      <SiteOptimizationFields content={content} />
      {articles.map((a, i) => (
        <Section key={i} label={articles.length > 1 ? `Blog article ${i + 1}` : 'Blog article'}>
          <article className="blog-article">
            <h3>{String(a.title || '')}</h3>
            {a.excerpt ? <p className="muted">{String(a.excerpt)}</p> : null}
            <ArticleBody markdown={String(a.body_markdown || '')} />
            {Array.isArray(a.tags) && a.tags.length > 0 && (
              <p className="small muted">Tags: {(a.tags as unknown[]).map(String).join(', ')}{a.target_keyword ? ` · Keyword: ${String(a.target_keyword)}` : ''}</p>
            )}
          </article>
        </Section>
      ))}
    </>
  )
}

const CustomerInsights = fieldRenderer([
  { key: 'data_note', label: 'Data basis' },
  { key: 'themes', label: 'Customer themes (hypotheses)' },
  { key: 'likely_objections', label: 'Likely objections' },
  { key: 'response_templates', label: 'Response templates' },
  { key: 'assumptions', label: 'Assumptions' },
])

const AccountPlan = fieldRenderer([
  { key: 'account_segments', label: 'Account segments' },
  { key: 'enablement_materials', label: 'Sales enablement materials' },
  { key: 'co_marketing_ideas', label: 'Co-marketing ideas' },
  { key: 'assumptions', label: 'Assumptions' },
])

const CampaignRecord = fieldRenderer([
  { key: 'summary', label: 'Summary' },
  { key: 'key_decisions', label: 'Key decisions' },
  { key: 'action_items', label: 'Action items' },
  { key: 'knowledge_updates', label: 'Knowledge updates' },
  { key: 'open_questions', label: 'Open questions' },
])

const RENDERERS: Record<string, (props: { content: Json }) => JSX.Element> = {
  strategy: Strategy,
  research_notes: ResearchNotes,
  campaign_plan: CampaignPlan,
  content_pack: ContentPack,
  qa_report: QAReport,
  social_calendar: SocialCalendar,
  outreach_plan: OutreachPlan,
  paid_media_plan: PaidMediaPlan,
  site_optimization_plan: SiteOptimizationPlan,
  customer_insights: CustomerInsights,
  account_plan: AccountPlan,
  campaign_record: CampaignRecord,
}

export default function DeliverableContent({
  deliverableType,
  content,
}: {
  deliverableType: string
  content: Record<string, unknown> | undefined
}) {
  if (!content) return <p className="muted">No content yet.</p>

  const Renderer = RENDERERS[deliverableType]
  return (
    <div>
      {Renderer ? <Renderer content={content} /> : <p className="muted">Unrecognized deliverable type.</p>}
      <details className="raw-json">
        <summary>View raw JSON</summary>
        <pre className="content-json">{JSON.stringify(content, null, 2)}</pre>
      </details>
    </div>
  )
}
