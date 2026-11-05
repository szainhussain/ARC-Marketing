import { useState } from 'react'
import { Link } from 'react-router-dom'
import { CheckCircle2, Circle, X } from 'lucide-react'
import { useResource } from '../hooks/useResource'

type Checklist = { items: { key: string; title: string; to: string; done: boolean }[]; done: number; total: number; complete: boolean }

const hiddenKey = (orgId: string) => `arc-checklist-hidden-${orgId}`

function readHidden(orgId: string) {
  try {
    return localStorage.getItem(hiddenKey(orgId)) === '1'
  } catch {
    return false
  }
}

/** Getting-started checklist computed by the server from real workspace activity. */
export default function GettingStarted({ orgId }: { orgId: string }) {
  const { data } = useResource<Checklist>(`/organizations/${orgId}/onboarding-checklist`)
  const [hidden, setHidden] = useState(() => readHidden(orgId))
  if (!data || hidden) return null
  const next = data.items.find((i) => !i.done)
  const pct = Math.round((data.done / data.total) * 100)

  function hide() {
    setHidden(true)
    try {
      localStorage.setItem(hiddenKey(orgId), '1')
    } catch {
      /* storage blocked: hidden for this visit only */
    }
  }

  return (
    <section className="card getting-started" aria-labelledby="gs-title">
      <div className="gs-head">
        <div>
          <h2 id="gs-title" style={{ margin: 0 }}>
            {data.complete ? 'Your marketing department is fully set up' : 'Get your marketing department running'}
          </h2>
          <p className="muted small" style={{ margin: '4px 0 0' }}>
            {data.done} of {data.total} done{next ? ` · Next: ${next.title.toLowerCase()}` : ''}
          </p>
        </div>
        <button type="button" className="icon-btn" aria-label="Hide checklist" onClick={hide}>
          <X size={16} />
        </button>
      </div>
      <div className="progress" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Setup progress">
        <span style={{ width: `${pct}%` }} />
      </div>
      <ol className="gs-list">
        {data.items.map((i) => (
          <li key={i.key} className={i.done ? 'done' : ''}>
            {i.done ? <CheckCircle2 size={16} aria-hidden="true" /> : <Circle size={16} aria-hidden="true" />}
            {i.done ? (
              <span>{i.title}</span>
            ) : (
              <Link to={i.to}>{i.title}</Link>
            )}
            <span className="sr-only">{i.done ? '(done)' : '(to do)'}</span>
          </li>
        ))}
      </ol>
    </section>
  )
}
