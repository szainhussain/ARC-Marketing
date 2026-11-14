import { useEffect, useState } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { BarChart3, ClipboardList, FileText, Pause, PenLine, Play, Send, ShieldCheck } from 'lucide-react'

const STEPS = [
  { icon: FileText, label: 'You brief', line: 'One short brief: the goal, the offer and your channels.' },
  { icon: ClipboardList, label: 'ARC plans', line: 'Research, a strategy and a dated plan built on your numbers.' },
  { icon: PenLine, label: 'ARC writes', line: 'Posts, ads, emails and pages in your brand voice.' },
  { icon: ShieldCheck, label: 'You approve', line: 'Nothing goes out until you approve that exact version.', gate: true },
  { icon: Send, label: 'It goes out', line: 'Published or exported in each platform’s format.' },
  { icon: BarChart3, label: 'You see profit', line: 'Which channels made or lost money, feeding next month’s plan.' },
]
const STEP_MS = 2600

/**
 * The monthly loop as a moving picture instead of seven paragraphs: a marker
 * travels the track and one plain sentence shows at a time. Under reduced
 * motion nothing moves and every sentence is listed. Pausable (the rotation
 * also stops while the pointer or keyboard focus is on it).
 */
export default function FlowLoop() {
  const reduce = useReducedMotion()
  const [active, setActive] = useState(0)
  const [playing, setPlaying] = useState(true)
  const [held, setHeld] = useState(false)

  useEffect(() => {
    if (reduce || !playing || held) return
    const id = window.setInterval(() => setActive((i) => (i + 1) % STEPS.length), STEP_MS)
    return () => window.clearInterval(id)
  }, [reduce, playing, held])

  if (reduce) {
    return (
      <ol className="flowloop-static" aria-label="How a month with ARC works">
        {STEPS.map((s) => (
          <li key={s.label}>
            <s.icon size={18} aria-hidden="true" />
            <span>
              <strong>{s.label}.</strong> {s.line}
            </span>
          </li>
        ))}
      </ol>
    )
  }

  const pct = (active / (STEPS.length - 1)) * 100
  return (
    <div
      className="flowloop"
      onPointerEnter={() => setHeld(true)}
      onPointerLeave={() => setHeld(false)}
      onFocus={() => setHeld(true)}
      onBlur={() => setHeld(false)}
    >
      <div className="flowloop-track" aria-hidden="true">
        <motion.div className="flowloop-fill" animate={{ scaleX: pct / 100 }} transition={{ type: 'spring', stiffness: 90, damping: 20 }} />
      </div>
      <ol className="flowloop-steps" aria-label="How a month with ARC works">
        {STEPS.map((s, i) => {
          const state = i === active ? 'active' : i < active ? 'done' : 'todo'
          return (
            <li key={s.label} className={`flowloop-step ${state}${s.gate ? ' gate' : ''}`}>
              <button type="button" aria-pressed={i === active} onClick={() => setActive(i)}>
                <motion.span className="flowloop-node" animate={{ scale: i === active ? 1.12 : 1 }} transition={{ type: 'spring', stiffness: 260, damping: 18 }}>
                  <s.icon size={20} aria-hidden="true" />
                </motion.span>
                <span className="flowloop-label">{s.label}</span>
              </button>
            </li>
          )
        })}
      </ol>
      <div className="flowloop-caption">
        <motion.p key={active} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28, ease: 'easeOut' }} aria-live="off">
          <strong>
            {active + 1}. {STEPS[active].label}.
          </strong>{' '}
          {STEPS[active].line}
        </motion.p>
        <button type="button" className="icon-btn" aria-label={playing ? 'Pause the animation' : 'Play the animation'} onClick={() => setPlaying((p) => !p)}>
          {playing ? <Pause size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
        </button>
      </div>
    </div>
  )
}
