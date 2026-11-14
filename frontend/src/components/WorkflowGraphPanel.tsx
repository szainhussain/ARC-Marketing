import { useRef, useState, type PointerEvent } from 'react'
import { Link } from 'react-router-dom'
import { List, Maximize2, Network, ZoomIn, ZoomOut } from 'lucide-react'
import type { AgentExecution, Task } from '../api/types'
import { useResource } from '../hooks/useResource'
import { humanize, money, relativeTime, statusLabel } from '../lib/labels'
import { Drawer, EmptyState, Skeleton, StatusPill } from './ui'
import WorkflowGraph from './WorkflowGraph'

export default function WorkflowGraphPanel({ tasks, orgId }: { tasks: Task[]; orgId: string }) {
  const [mode, setMode] = useState<'graph' | 'list'>('graph')
  const [scale, setScale] = useState(1)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [selected, setSelected] = useState<Task | null>(null)
  const drag = useRef<{ x: number; y: number; ox: number; oy: number } | null>(null)

  function onDown(e: PointerEvent<HTMLDivElement>) {
    if ((e.target as Element).closest('.wf-node')) return
    drag.current = { x: e.clientX, y: e.clientY, ox: offset.x, oy: offset.y }
    e.currentTarget.setPointerCapture(e.pointerId)
  }
  function onMove(e: PointerEvent<HTMLDivElement>) {
    if (!drag.current) return
    setOffset({ x: drag.current.ox + e.clientX - drag.current.x, y: drag.current.oy + e.clientY - drag.current.y })
  }
  const fit = () => {
    setScale(1)
    setOffset({ x: 0, y: 0 })
  }
  const byId = new Map(tasks.map((t) => [t.id, t]))

  return (
    <div>
      <div className="wf-controls" role="toolbar" aria-label="Workflow view controls">
        <div className="seg" role="group" aria-label="View">
          <button aria-pressed={mode === 'graph'} onClick={() => setMode('graph')}>
            <Network size={14} aria-hidden="true" /> Graph
          </button>
          <button aria-pressed={mode === 'list'} onClick={() => setMode('list')}>
            <List size={14} aria-hidden="true" /> List
          </button>
        </div>
        {mode === 'graph' && (
          <>
            <button className="icon-btn" aria-label="Zoom in" onClick={() => setScale((s) => Math.min(2, s + 0.15))}>
              <ZoomIn size={16} />
            </button>
            <button className="icon-btn" aria-label="Zoom out" onClick={() => setScale((s) => Math.max(0.4, s - 0.15))}>
              <ZoomOut size={16} />
            </button>
            <button className="icon-btn" aria-label="Fit to screen" onClick={fit}>
              <Maximize2 size={16} />
            </button>
            <span className="muted small">Drag to pan · click a node for details</span>
          </>
        )}
      </div>
      {mode === 'graph' ? (
        <div
          className="wf-viewport"
          onPointerDown={onDown}
          onPointerMove={onMove}
          onPointerUp={() => (drag.current = null)}
          onWheel={(e) => {
            if (e.ctrlKey) setScale((s) => Math.min(2, Math.max(0.4, s - e.deltaY * 0.002)))
          }}
        >
          <div style={{ transform: `translate(${offset.x}px, ${offset.y}px) scale(${scale})`, transformOrigin: '0 0', padding: 12 }}>
            <WorkflowGraph tasks={tasks} selectedId={selected?.id} onSelect={setSelected} />
          </div>
        </div>
      ) : (
        <ol className="timeline" aria-label="Workflow steps in execution order">
          {tasks
            .slice()
            .sort((a, b) => a.sequence_index - b.sequence_index)
            .map((t) => (
              <li key={t.id} className={t.status === 'succeeded' ? 'success' : t.status === 'failed' ? 'error' : t.status === 'running' ? 'info' : ''}>
                <span className="timeline-dot" aria-hidden="true" />
                <div style={{ flex: 1 }}>
                  <button className="link-btn" onClick={() => setSelected(t)}>
                    {String(t.agent_number || '').padStart(2, '0')} {t.agent_name}
                  </button>{' '}
                  <StatusPill status={t.status} />
                  <div className="muted small">
                    Waits for: {t.depends_on.length ? t.depends_on.map((id) => byId.get(id)?.agent_name || id).join(', ') : 'nothing'}
                  </div>
                </div>
              </li>
            ))}
        </ol>
      )}
      <TaskDrawer task={selected} orgId={orgId} byId={byId} onClose={() => setSelected(null)} />
    </div>
  )
}

export function TaskDrawer({
  task,
  orgId,
  byId,
  onClose,
}: {
  task: Task | null
  orgId: string
  byId?: Map<string, Task>
  onClose: () => void
}) {
  const { data, loading } = useResource<{ executions: AgentExecution[] }>(
    task ? `/organizations/${orgId}/tasks/${task.id}/executions` : null,
  )
  return (
    <Drawer open={!!task} onClose={onClose} title={task ? task.agent_name : ''}>
      {task && (
        <>
          <p>
            <StatusPill status={task.status} />{' '}
            <span className="muted small">
              Attempt {task.attempt_count}/{task.max_attempts} · <Link to={`/app/agents/${task.agent_id}`}>Agent profile</Link>
            </span>
          </p>
          {task.error_summary && <div className="banner warning">{task.error_summary}</div>}
          <div className="deliverable-section">
            <div className="section-label">Dependencies</div>
            <p className="small">
              {task.depends_on.length
                ? task.depends_on.map((id) => byId?.get(id)?.agent_name || id).join(', ')
                : 'None, starts first.'}
            </p>
          </div>
          <div className="deliverable-section">
            <div className="section-label">Output</div>
            <p className="small">{task.deliverable_id ? `${humanize(task.task_type || '')} delivered.` : 'No output yet.'}</p>
          </div>
          <div className="section-label">Execution history</div>
          {loading ? (
            <Skeleton count={3} />
          ) : !data || data.executions.length === 0 ? (
            <EmptyState title="Not attempted yet" />
          ) : (
            <ol className="timeline">
              {data.executions.map((e) => (
                <li key={e.id} className={e.status === 'succeeded' ? 'success' : 'error'}>
                  <span className="timeline-dot" aria-hidden="true" />
                  <div>
                    <div>
                      #{e.attempt_number} {statusLabel(e.status)}
                      {e.error_code ? `: ${humanize(e.error_code)}` : ''}
                    </div>
                    <div className="muted small">{e.error_summary || e.summary}</div>
                    {e.evaluation.filter((c) => !c.passed).map((c) => (
                      <div key={c.check} className="text-warning small">
                        ⚠ {c.detail}
                      </div>
                    ))}
                    <div className="muted small mono">
                      v{e.agent_version} · {e.model || 'no model call'} · {e.input_tokens + e.output_tokens} tokens ·{' '}
                      {money(e.estimated_cost_usd)} est. · {relativeTime(e.started_at)}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </>
      )}
    </Drawer>
  )
}
