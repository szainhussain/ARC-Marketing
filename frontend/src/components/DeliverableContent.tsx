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

const RENDERERS: Record<string, (props: { content: Json }) => JSX.Element> = {
  strategy: Strategy,
  research_notes: ResearchNotes,
  campaign_plan: CampaignPlan,
  content_pack: ContentPack,
  qa_report: QAReport,
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
