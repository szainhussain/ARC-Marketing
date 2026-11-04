import { useEffect, useRef, useState } from 'react'
import { Pause, Play, RotateCcw, Check } from 'lucide-react'

/** Local, deterministic demo of how a run moves through the department.
 * Runs entirely in the browser: it never calls the API and can't trigger
 * any real action. Clearly labelled as a demonstration. */

type NodeState = 'waiting' | 'running' | 'done' | 'approval'
type DemoNode = { id: string; n: string; title: string; deps: string[]; note: string }

const NODES: DemoNode[] = [
  { id: 'cmo', n: '01', title: 'CMO', deps: [], note: 'Objectives & KPIs' },
  { id: 'research', n: '07', title: 'Research', deps: ['cmo'], note: 'Audience evidence' },
  { id: 'manager', n: '02', title: 'Marketing Manager', deps: ['cmo', 'research'], note: 'Phased plan' },
  { id: 'insights', n: '08', title: 'Customer Insights', deps: ['research'], note: 'Themes & templates' },
  { id: 'creative', n: '06', title: 'Creative', deps: ['manager'], note: 'Copy variants' },
  { id: 'seo', n: '09', title: 'SEO & Growth', deps: ['manager'], note: 'Keyword themes' },
  { id: 'pr', n: '04', title: 'PR & Partnerships', deps: ['manager'], note: 'Outreach drafts' },
  { id: 'accounts', n: '10', title: 'Key Accounts', deps: ['manager'], note: 'Account plan' },
  { id: 'social', n: '03', title: 'Social', deps: ['creative'], note: 'Post calendar' },
  { id: 'paid', n: '05', title: 'Paid Media', deps: ['creative'], note: 'Budget split (you decide)' },
  { id: 'ops', n: '11', title: 'Ops & QA', deps: ['social', 'paid', 'seo', 'pr', 'insights', 'accounts'], note: 'Quality gate' },
  { id: 'approval', n: '—', title: 'Your approval', deps: ['ops'], note: 'Approve the content pack' },
  { id: 'record', n: '12', title: 'Record Keeper', deps: ['approval'], note: 'Decisions & learnings' },
]

const initial = () => Object.fromEntries(NODES.map((n) => [n.id, 'waiting'])) as Record<string, NodeState>

export default function WorkflowDemo() {
  const [state, setState] = useState<Record<string, NodeState>>(initial)
  const [playing, setPlaying] = useState(false)
  const tick = useRef<number | undefined>(undefined)

  useEffect(() => {
    if (!playing) return
    tick.current = window.setInterval(() => {
      setState((prev) => {
        const next = { ...prev }
        let changed = false
        for (const node of NODES) {
          if (prev[node.id] === 'running') {
            next[node.id] = 'done'
            changed = true
          }
        }
        for (const node of NODES) {
          if (prev[node.id] !== 'waiting') continue
          const ready = node.deps.every((d) => next[d] === 'done')
          if (ready) {
            next[node.id] = node.id === 'approval' ? 'approval' : 'running'
            changed = true
          }
        }
        if (!changed) setPlaying(false)
        return next
      })
    }, 900)
    return () => window.clearInterval(tick.current)
  }, [playing])

  const done = Object.values(state).filter((s) => s === 'done').length
  const awaiting = state.approval === 'approval'

  return (
    <div className="card" style={{ padding: 20 }}>
      <div className="card-head">
        <div>
          <strong>Campaign run — demonstration</strong>{' '}
          <span className="sample-tag">LOCAL DEMO · NO REAL ACTIONS</span>
        </div>
        <div className="head-actions">
          {!playing ? (
            <button className="small-btn" onClick={() => setPlaying(true)} disabled={awaiting || done === NODES.length}>
              <Play size={14} aria-hidden="true" /> {done === 0 ? 'Start' : 'Resume'}
            </button>
          ) : (
            <button className="secondary small-btn" onClick={() => setPlaying(false)}>
              <Pause size={14} aria-hidden="true" /> Pause
            </button>
          )}
          <button
            className="secondary small-btn"
            onClick={() => {
              setPlaying(false)
              setState(initial())
            }}
          >
            <RotateCcw size={14} aria-hidden="true" /> Reset
          </button>
        </div>
      </div>
      <div className="progress" style={{ margin: '6px 0 16px' }} aria-label={`${done} of ${NODES.length} steps done`}>
        <span style={{ width: `${(done / NODES.length) * 100}%` }} />
      </div>
      <div className="demo-board" aria-live="polite">
        {NODES.map((node) => {
          const s = state[node.id]
          return (
            <div key={node.id} className={`demo-node ${s}`}>
              <div className="dn">{node.n}</div>
              <div className="dt">{node.title}</div>
              <div className="ds">
                {s === 'waiting' && (node.deps.length ? 'Waiting on dependencies' : 'Ready')}
                {s === 'running' && 'Working…'}
                {s === 'done' && <>✓ {node.note}</>}
                {s === 'approval' && 'Needs your decision'}
              </div>
              {s === 'approval' && (
                <button
                  className="small-btn"
                  style={{ marginTop: 8 }}
                  onClick={() => {
                    setState((prev) => ({ ...prev, approval: 'done' }))
                    setPlaying(true)
                  }}
                >
                  <Check size={14} aria-hidden="true" /> Approve (demo)
                </button>
              )}
            </div>
          )
        })}
      </div>
      <p className="muted small" style={{ marginBottom: 0, marginTop: 14 }}>
        In the real workspace this graph is drawn from persisted tasks and their dependencies, and the run pauses at
        approvals until a person decides.
      </p>
    </div>
  )
}
