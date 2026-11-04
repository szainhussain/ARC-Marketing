import { useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis } from 'recharts'
import { AGENT_META } from '../../lib/agentMeta'

/** Interactive sample workspace for the homepage. All numbers are
 * SAMPLE DATA, labelled as such; nothing here comes from a customer. */

const SERIES = [4, 9, 7, 14, 18, 16, 24, 22, 30, 27, 35, 41].map((v, i) => ({ d: `W${i + 1}`, tasks: v }))
const AGENT_IDS = Object.keys(AGENT_META)
const STATUS = ['done', 'done', 'working', 'done', 'idle', 'working', 'done', 'idle', 'done', 'idle', 'waiting', 'idle']

export default function ProductPreview() {
  const [view, setView] = useState<'business' | 'ops'>('business')
  const [approved, setApproved] = useState(false)
  const reduce = useReducedMotion()

  return (
    <div className="preview-frame">
      <div className="preview-bar">
        <div className="preview-dots" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
        <span className="small muted">Spring Trail Launch</span>
        <span className="sample-tag">SAMPLE DATA</span>
        <span style={{ flex: 1 }} />
        <div className="seg" role="group" aria-label="Preview view">
          <button aria-pressed={view === 'business'} onClick={() => setView('business')}>
            Business Command Center
          </button>
          <button aria-pressed={view === 'ops'} onClick={() => setView('ops')}>
            Agent Operations Center
          </button>
        </div>
      </div>
      <AnimatePresence mode="wait">
        <motion.div
          key={view}
          className="preview-body"
          initial={reduce ? false : { opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.25 }}
        >
          {view === 'business' ? (
            <>
              <div className="preview-grid">
                <Mini k="Active campaigns" v="3" />
                <Mini k="Deliverables ready" v="12" />
                <Mini k="Awaiting approval" v={approved ? '0' : '1'} />
                <Mini k="Workflow success" v="96%" />
              </div>
              <div className="grid-3" style={{ gridTemplateColumns: '2fr 1fr' }}>
                <div className="mini" style={{ height: 190 }}>
                  <div className="k">Agent tasks completed (sample)</div>
                  <ResponsiveContainer width="100%" height={150}>
                    <AreaChart data={SERIES} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="pv" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="0" stopColor="#9fd8ff" stopOpacity={0.35} />
                          <stop offset="1" stopColor="#9fd8ff" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="d" hide />
                      <Tooltip contentStyle={{ background: '#16181d', border: '1px solid #33373e', borderRadius: 8 }} />
                      <Area type="monotone" dataKey="tasks" stroke="#9fd8ff" fill="url(#pv)" strokeWidth={2} isAnimationActive={!reduce} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <div className="mini">
                  <div className="k">Pending decision</div>
                  <div style={{ fontWeight: 600, marginTop: 8 }}>Content pack · v2</div>
                  <div className="muted small" style={{ margin: '4px 0 10px' }}>
                    From Creative Studio · risk: medium · version-locked
                  </div>
                  {approved ? (
                    <span className="status-pill approved">Approved</span>
                  ) : (
                    <button className="small-btn" onClick={() => setApproved(true)}>
                      Approve (sample)
                    </button>
                  )}
                </div>
              </div>
            </>
          ) : (
            <>
              <div className="preview-grid">
                <Mini k="Agents working" v="2" />
                <Mini k="Queued tasks" v="5" />
                <Mini k="Retries today" v="3" />
                <Mini k="AI cost (est.)" v="$0.27" />
              </div>
              <div className="preview-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))' }}>
                {AGENT_IDS.map((id, i) => {
                  const meta = AGENT_META[id]
                  const s = STATUS[i]
                  return (
                    <div key={id} className="mini" style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                      <meta.icon size={16} color="#9fd8ff" aria-hidden="true" />
                      <div style={{ minWidth: 0 }}>
                        <div className="small" style={{ fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {meta.short}
                        </div>
                        <span className={`status-pill ${s === 'done' ? 'succeeded' : s === 'working' ? 'running' : s === 'waiting' ? 'waiting_for_dependency' : 'idle'}`}>
                          {s}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </>
          )}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}

function Mini({ k, v }: { k: string; v: string }) {
  return (
    <div className="mini">
      <div className="k">{k}</div>
      <div className="v">{v}</div>
    </div>
  )
}
