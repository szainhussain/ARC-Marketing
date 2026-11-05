import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest, ApiError } from '../api/client'
import { useResource } from '../hooks/useResource'

type Msg = {
  id: string
  role: 'user' | 'assistant'
  content: string
  status: 'pending' | 'running' | 'answered' | 'failed'
  sources: { kind: string; title: string; link: string }[]
  action: { type: string; label: string; link: string } | null
}

const STARTERS = ['What did my marketing team deliver this month?', 'What is waiting for my approval?', 'How are my results trending?']

/** Ask ARC: answers from this workspace's approved knowledge, deliverables and results. */
export default function AssistantChat({ orgId, onNavigate }: { orgId: string; onNavigate: () => void }) {
  const [pollMs, setPollMs] = useState<number | undefined>(undefined)
  const { data, reload } = useResource<{ messages: Msg[] }>(`/organizations/${orgId}/assistant/messages`, { pollMs })
  const [text, setText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const end = useRef<HTMLDivElement>(null)
  const messages = data?.messages || []
  const waiting = messages.some((m) => m.role === 'assistant' && (m.status === 'pending' || m.status === 'running'))

  useEffect(() => {
    setPollMs(waiting ? 2500 : undefined)
  }, [waiting])
  useEffect(() => {
    end.current?.scrollIntoView({ block: 'end' })
  }, [messages.length, waiting])

  async function send(q: string) {
    const content = q.trim()
    if (!content) return
    setSending(true)
    setError(null)
    try {
      await apiRequest(`/organizations/${orgId}/assistant/messages`, { method: 'POST', body: { content } })
      setText('')
      reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not send your question.')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="assistant">
      <div className="assistant-log" aria-live="polite">
        {messages.length === 0 && (
          <div className="assistant-empty">
            <p className="muted small" style={{ marginTop: 0 }}>
              Ask about your campaigns, deliverables, results or brand. Answers come only from this workspace, with sources.
            </p>
            {STARTERS.map((s) => (
              <button key={s} type="button" className="chip" onClick={() => send(s)} disabled={sending}>
                {s}
              </button>
            ))}
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`assistant-msg ${m.role}${m.status === 'failed' ? ' failed' : ''}`}>
            {m.role === 'assistant' && (m.status === 'pending' || m.status === 'running') ? (
              <span className="muted small">Thinking…</span>
            ) : (
              <p>{m.content}</p>
            )}
            {m.sources.length > 0 && (
              <div className="assistant-sources small">
                Sources:{' '}
                {m.sources.map((s, i) => (
                  <span key={`${s.link}-${i}`}>
                    {i > 0 && ' · '}
                    <Link to={s.link} onClick={onNavigate}>
                      {s.title}
                    </Link>
                  </span>
                ))}
              </div>
            )}
            {m.action && (
              <Link to={m.action.link} className="btn secondary small-btn" style={{ marginTop: 8 }} onClick={onNavigate}>
                {m.action.label || 'Open'}
              </Link>
            )}
          </div>
        ))}
        <div ref={end} />
      </div>
      <form
        className="assistant-form"
        onSubmit={(e) => {
          e.preventDefault()
          send(text)
        }}
      >
        {error && <div className="banner error">{error}</div>}
        <label htmlFor="assistant-input" className="sr-only">
          Your question
        </label>
        <textarea
          id="assistant-input"
          rows={2}
          value={text}
          placeholder="Ask about your marketing…"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              send(text)
            }
          }}
        />
        <button type="submit" disabled={sending || !text.trim()}>
          {sending ? 'Sending…' : 'Ask'}
        </button>
      </form>
    </div>
  )
}
