import type { Task } from '../api/types'
import { statusLabel } from '../lib/labels'

const NODE_W = 168
const NODE_H = 56
const COL_GAP = 44
const ROW_GAP = 16
const PAD = 12

/**
 * The run's real dependency graph, laid out by depth (an agent sits one
 * column to the right of its deepest dependency). Rendered from the
 * tasks' stored `depends_on` ids, not a hard-coded picture.
 */
export default function WorkflowGraph({
  tasks,
  selectedId,
  onSelect,
}: {
  tasks: Task[]
  selectedId?: string | null
  onSelect?: (task: Task) => void
}) {
  const byId = new Map(tasks.map((t) => [t.id, t]))
  const depth = new Map<string, number>()
  const depthOf = (task: Task, seen = new Set<string>()): number => {
    if (depth.has(task.id)) return depth.get(task.id) as number
    if (seen.has(task.id)) return 0
    seen.add(task.id)
    const deps = task.depends_on.map((id) => byId.get(id)).filter((t): t is Task => !!t)
    const d = deps.length === 0 ? 0 : 1 + Math.max(...deps.map((dep) => depthOf(dep, seen)))
    depth.set(task.id, d)
    return d
  }
  tasks.forEach((t) => depthOf(t))

  const columns: Task[][] = []
  tasks
    .slice()
    .sort((a, b) => a.sequence_index - b.sequence_index)
    .forEach((t) => {
      const d = depth.get(t.id) || 0
      columns[d] = columns[d] || []
      columns[d].push(t)
    })

  const maxRows = Math.max(1, ...columns.map((c) => c?.length || 0))
  const height = PAD * 2 + maxRows * NODE_H + (maxRows - 1) * ROW_GAP
  const width = PAD * 2 + columns.length * NODE_W + Math.max(0, columns.length - 1) * COL_GAP

  const pos = new Map<string, { x: number; y: number }>()
  columns.forEach((col, ci) => {
    const colHeight = col.length * NODE_H + (col.length - 1) * ROW_GAP
    const offset = (height - colHeight) / 2
    col.forEach((t, ri) => {
      pos.set(t.id, { x: PAD + ci * (NODE_W + COL_GAP), y: offset + ri * (NODE_H + ROW_GAP) })
    })
  })

  return (
    <div className="wf-graph" role="group" aria-label="Agent workflow dependency graph">
      <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`}>
        {tasks.flatMap((t) =>
          t.depends_on.map((depId) => {
            const from = pos.get(depId)
            const to = pos.get(t.id)
            if (!from || !to) return null
            const x1 = from.x + NODE_W
            const y1 = from.y + NODE_H / 2
            const x2 = to.x
            const y2 = to.y + NODE_H / 2
            const mid = (x1 + x2) / 2
            const done = byId.get(depId)?.status === 'succeeded'
            return (
              <path
                key={`${depId}-${t.id}`}
                d={`M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}`}
                className={`wf-edge${done ? ' done' : ''}`}
              />
            )
          }),
        )}
        {tasks.map((t) => {
          const p = pos.get(t.id)
          if (!p) return null
          return (
            <g
              key={t.id}
              transform={`translate(${p.x},${p.y})`}
              className={`wf-node ${t.status}${selectedId === t.id ? ' selected' : ''}`}
              onClick={onSelect ? () => onSelect(t) : undefined}
              role={onSelect ? 'button' : undefined}
              tabIndex={onSelect ? 0 : undefined}
              onKeyDown={
                onSelect
                  ? (e) => {
                      if (e.key === 'Enter' || e.key === ' ') onSelect(t)
                    }
                  : undefined
              }
              aria-label={`${t.agent_name}: ${statusLabel(t.status)}`}
            >
              <rect width={NODE_W} height={NODE_H} rx={10} />
              <circle cx={14} cy={18} r={4} className="wf-dot" />
              <text x={26} y={22} className="wf-title">
                {t.agent_number ? `${String(t.agent_number).padStart(2, '0')} ` : ''}
                {shorten(t.agent_name)}
              </text>
              <text x={14} y={42} className="wf-sub">
                {statusLabel(t.status)}
                {t.attempt_count > 1 ? ` · try ${t.attempt_count}/${t.max_attempts}` : ''}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}

function shorten(name: string): string {
  const first = name.split(/[,&]/)[0].trim()
  return first.length > 18 ? `${first.slice(0, 17)}…` : first
}
