import { useEffect, useState, type ReactNode } from 'react'
import { motion, useReducedMotion } from 'motion/react'
import { BarChart3, Check, FileText, Globe, Mail, Megaphone, Pause, Play, RefreshCw, RotateCcw, Share2, ShieldCheck } from 'lucide-react'

export type StoryStep = { title: string; body: string }
const STEP_MS = 5200
const ease = [0.16, 1, 0.3, 1] as const

/* Each scene is a tiny looping-free animation that plays once when its step becomes active. */

function Line({ w, delay }: { w: string; delay: number }) {
  return <motion.span className="hiw-line" style={{ width: w }} initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: 0.5, delay, ease }} />
}

function SceneSetup() {
  const rows = ['Business', 'Brand voice', 'Goals', 'Your numbers']
  return (
    <div className="hiw-card">
      {rows.map((r, i) => (
        <div key={r} className="hiw-row">
          <span className="hiw-key">{r}</span>
          <Line w={`${78 - i * 9}%`} delay={0.25 + i * 0.35} />
          <motion.span className="hiw-tick" initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ delay: 0.7 + i * 0.35, type: 'spring', stiffness: 320, damping: 16 }}>
            <Check size={13} aria-hidden="true" />
          </motion.span>
        </div>
      ))}
    </div>
  )
}

function SceneBrief() {
  return (
    <div className="hiw-card hiw-doc">
      <div className="hiw-doc-head">
        <FileText size={18} aria-hidden="true" /> Campaign brief
      </div>
      {['92%', '74%', '86%', '58%'].map((w, i) => (
        <Line key={w} w={w} delay={0.3 + i * 0.3} />
      ))}
      <motion.div className="hiw-chip-btn" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.7, duration: 0.35 }}>
        Run
      </motion.div>
    </div>
  )
}

function SceneAgents() {
  const chain = ['Research', 'Strategy', 'Plan', 'Content', 'Quality check', 'Record']
  return (
    <ol className="hiw-chain" aria-hidden="true">
      {chain.map((c, i) => (
        <motion.li key={c} initial={{ opacity: 0.25 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 + i * 0.55, duration: 0.3 }}>
          <motion.span className="hiw-dot" initial={{ scale: 0.6, backgroundColor: 'var(--color-border-strong)' }} animate={{ scale: 1, backgroundColor: 'var(--color-accent)' }} transition={{ delay: 0.3 + i * 0.55, duration: 0.3 }} />
          {c}
        </motion.li>
      ))}
    </ol>
  )
}

function SceneRetry() {
  return (
    <div className="hiw-center">
      <motion.div className="hiw-badge warn" initial={{ opacity: 1 }} animate={{ opacity: 0 }} transition={{ delay: 2.2, duration: 0.3 }}>
        <motion.span animate={{ rotate: 360 }} transition={{ duration: 1.1, repeat: 1, ease: 'linear' }} style={{ display: 'inline-flex' }}>
          <RefreshCw size={22} aria-hidden="true" />
        </motion.span>
        Busy. Trying again
      </motion.div>
      <motion.div className="hiw-badge ok" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 2.5, duration: 0.35 }}>
        <Check size={22} aria-hidden="true" /> Done
      </motion.div>
    </div>
  )
}

function SceneApprove() {
  return (
    <div className="hiw-card hiw-approve">
      <div className="hiw-doc-head">
        Content pack <span className="hiw-version">v2</span>
      </div>
      <Line w="88%" delay={0.2} />
      <Line w="64%" delay={0.4} />
      <motion.div className="hiw-stamp" initial={{ scale: 2.2, opacity: 0, rotate: -18 }} animate={{ scale: 1, opacity: 1, rotate: -8 }} transition={{ delay: 1.3, type: 'spring', stiffness: 260, damping: 14 }}>
        <ShieldCheck size={18} aria-hidden="true" /> Approved
      </motion.div>
    </div>
  )
}

function ScenePublish() {
  const targets: [string, ReactNode][] = [
    ['Social', <Share2 key="s" size={16} aria-hidden="true" />],
    ['Ads', <Megaphone key="a" size={16} aria-hidden="true" />],
    ['Blog', <Globe key="b" size={16} aria-hidden="true" />],
    ['Email', <Mail key="e" size={16} aria-hidden="true" />],
  ]
  return (
    <div className="hiw-publish">
      <div className="hiw-chip-btn solid">
        <ShieldCheck size={15} aria-hidden="true" /> Approved work
      </div>
      <div className="hiw-targets">
        {targets.map(([label, icon], i) => (
          <motion.div key={label} className="hiw-target" initial={{ opacity: 0, y: -26 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 + i * 0.3, duration: 0.45, ease }}>
            {icon} {label}
          </motion.div>
        ))}
      </div>
    </div>
  )
}

function SceneLearn() {
  const bars = [38, 52, 47, 68, 84]
  return (
    <div className="hiw-learn">
      <div className="hiw-bars" aria-hidden="true">
        {bars.map((h, i) => (
          <motion.span key={i} style={{ height: `${h}%` }} initial={{ scaleY: 0 }} animate={{ scaleY: 1 }} transition={{ delay: 0.25 + i * 0.22, duration: 0.5, ease }} />
        ))}
      </div>
      <motion.div className="hiw-loopback" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.6, duration: 0.4 }}>
        <RotateCcw size={16} aria-hidden="true" /> Feeds next month's plan
      </motion.div>
    </div>
  )
}

const SCENES = [SceneSetup, SceneBrief, SceneAgents, SceneRetry, SceneApprove, ScenePublish, SceneLearn]
const ICONS = [FileText, FileText, Share2, RefreshCw, ShieldCheck, Megaphone, BarChart3]

/**
 * The How it works page as a moving walkthrough: seven steps, one small
 * illustration playing at a time. Auto-advances, pauses on hover, focus or the
 * pause button, and every step is a button. Under reduced motion it renders the
 * plain numbered list with no illustration.
 */
export default function HowItWorksStory({ steps }: { steps: StoryStep[] }) {
  const reduce = useReducedMotion()
  const [active, setActive] = useState(0)
  const [playing, setPlaying] = useState(true)
  const [held, setHeld] = useState(false)

  useEffect(() => {
    if (reduce || !playing || held) return
    const id = window.setInterval(() => setActive((i) => (i + 1) % steps.length), STEP_MS)
    return () => window.clearInterval(id)
  }, [reduce, playing, held, steps.length])

  if (reduce) {
    return (
      <ol className="timeline" style={{ maxWidth: 760 }}>
        {steps.map((s, i) => (
          <li key={s.title} className="info">
            <span className="timeline-dot" aria-hidden="true" />
            <div>
              <div style={{ fontWeight: 700 }}>
                {i + 1}. {s.title}
              </div>
              <div className="muted">{s.body}</div>
            </div>
          </li>
        ))}
      </ol>
    )
  }

  const Scene = SCENES[active % SCENES.length]
  return (
    <div className="hiw" onPointerEnter={() => setHeld(true)} onPointerLeave={() => setHeld(false)} onFocus={() => setHeld(true)} onBlur={() => setHeld(false)}>
      <ol className="hiw-steps">
        {steps.map((s, i) => {
          const Icon = ICONS[i % ICONS.length]
          return (
            <li key={s.title} className={i === active ? 'active' : ''}>
              <button type="button" aria-pressed={i === active} onClick={() => setActive(i)}>
                <span className="hiw-num">
                  <Icon size={16} aria-hidden="true" />
                </span>
                <span>
                  <span className="hiw-title">
                    {i + 1}. {s.title}
                  </span>
                  {i === active && (
                    <motion.span className="hiw-body" initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} transition={{ duration: 0.3 }}>
                      {s.body}
                    </motion.span>
                  )}
                </span>
              </button>
              {i === active && playing && !held && (
                <motion.span className="hiw-progress" key={`p-${active}`} initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: STEP_MS / 1000, ease: 'linear' }} />
              )}
            </li>
          )
        })}
      </ol>
      <div className="hiw-stage" aria-hidden="true">
        <motion.div key={active} className="hiw-scene" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, ease: 'easeOut' }}>
          <Scene />
        </motion.div>
        <button type="button" className="icon-btn hiw-pause" aria-label={playing ? 'Pause the walkthrough' : 'Play the walkthrough'} onClick={() => setPlaying((p) => !p)}>
          {playing ? <Pause size={16} aria-hidden="true" /> : <Play size={16} aria-hidden="true" />}
        </button>
      </div>
    </div>
  )
}
