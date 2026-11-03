import { useState } from 'react'
import type { PlatformExport } from '../api/types'

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // clipboard API can be unavailable (e.g. insecure context); fail silently,
      // the text is still visible and selectable for manual copy.
    }
  }
  return (
    <button className="secondary" onClick={handleCopy} style={{ padding: '4px 10px', fontSize: '0.8rem' }}>
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

export default function PlatformExportView({ export: exp }: { export: PlatformExport }) {
  return (
    <div>
      {exp.variant_exports.map((v, i) => (
        <div key={i} className="variant-card">
          <div className="channel-tag">{v.platform_label}</div>

          {v.fields.map((f, fi) => (
            <div key={fi} style={{ marginTop: 10 }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: 4,
                }}
              >
                <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--color-muted-fg)' }}>
                  {f.label}
                  {f.limit_confirmed && f.limit !== null && (
                    <span
                      className={`status-pill ${f.fits ? 'completed' : 'failed'}`}
                      style={{ marginLeft: 8 }}
                    >
                      {f.length}/{f.limit}
                    </span>
                  )}
                  {!f.limit_confirmed && (
                    <span className="status-pill" style={{ marginLeft: 8 }}>
                      limit unconfirmed
                    </span>
                  )}
                </span>
                <CopyButton text={f.text} />
              </div>
              <p className="deliverable-prose" style={{ background: 'var(--color-bg)', padding: '8px 10px', borderRadius: 6 }}>
                {f.text}
              </p>
              {f.note && (
                <p className="muted" style={{ fontSize: '0.78rem', margin: '2px 0 0' }}>
                  {f.note}
                </p>
              )}
            </div>
          ))}

          {v.cta && (
            <div style={{ marginTop: 10 }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--color-muted-fg)' }}>
                Call to action
              </span>
              <p className="deliverable-prose">{v.cta}</p>
              {v.cta_note && (
                <p className="muted" style={{ fontSize: '0.78rem' }}>
                  {v.cta_note}
                </p>
              )}
            </div>
          )}

          {v.requirements && v.requirements.length > 0 && (
            <div style={{ marginTop: 10 }}>
              <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--color-muted-fg)' }}>
                Requirements
              </span>
              <ul className="deliverable-list">
                {v.requirements.map((r, ri) => (
                  <li key={ri}>{r}</li>
                ))}
              </ul>
            </div>
          )}

          <div style={{ marginTop: 10 }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--color-muted-fg)' }}>
              Asset checklist
            </span>
            <ul className="deliverable-list">
              {v.asset_checklist.map((a, ai) => (
                <li key={ai}>{a}</li>
              ))}
            </ul>
          </div>

          <p className="muted" style={{ fontSize: '0.76rem', marginTop: 10, marginBottom: 0 }}>
            {v.source_note}
          </p>
        </div>
      ))}
    </div>
  )
}
