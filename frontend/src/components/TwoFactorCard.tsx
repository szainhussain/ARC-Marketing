import { useState } from 'react'
import { ShieldCheck } from 'lucide-react'
import { apiRequest, ApiError } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useResource } from '../hooks/useResource'
import { Field, useToast } from './ui'

/** Turn two-factor sign-in on or off. Works with any authenticator app
 *  (Google Authenticator, Microsoft Authenticator, 1Password, Authy). */
export default function TwoFactorCard() {
  const { refresh } = useAuth()
  const toast = useToast()
  const status = useResource<{ enabled: boolean; recovery_codes_left: number }>('/auth/mfa')
  const [setup, setSetup] = useState<{ secret: string; otpauth_uri: string } | null>(null)
  const [code, setCode] = useState('')
  const [codes, setCodes] = useState<string[] | null>(null)
  const [disableForm, setDisableForm] = useState<{ open: boolean; password: string; code: string }>({ open: false, password: '', code: '' })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function call<T>(fn: () => Promise<T>): Promise<T | undefined> {
    setBusy(true)
    setError(null)
    try {
      return await fn()
    } catch (err) {
      setError(err instanceof ApiError ? err.details[0]?.issue || err.message : 'Something went wrong. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  async function begin() {
    const r = await call(() => apiRequest<{ secret: string; otpauth_uri: string }>('/auth/mfa/setup', { method: 'POST' }))
    if (r) setSetup(r)
  }
  async function enable() {
    const r = await call(() => apiRequest<{ recovery_codes: string[] }>('/auth/mfa/enable', { method: 'POST', body: { code } }))
    if (r) {
      setCodes(r.recovery_codes)
      setSetup(null)
      setCode('')
      status.reload()
      refresh()
    }
  }
  async function disable() {
    const looksLikeRecovery = disableForm.code.includes('-')
    const r = await call(() =>
      apiRequest('/auth/mfa/disable', {
        method: 'POST',
        body: { password: disableForm.password, ...(looksLikeRecovery ? { recovery_code: disableForm.code } : { code: disableForm.code }) },
      }),
    )
    if (r) {
      setDisableForm({ open: false, password: '', code: '' })
      toast({ tone: 'info', title: 'Two-factor sign-in turned off' })
      status.reload()
      refresh()
    }
  }
  function download() {
    if (!codes) return
    const blob = new Blob([`ARC recovery codes\nEach code works once.\n\n${codes.join('\n')}\n`], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = 'arc-recovery-codes.txt'
    a.click()
    URL.revokeObjectURL(a.href)
  }

  const enabled = status.data?.enabled
  return (
    <div className="card">
      <h2>
        <ShieldCheck size={17} aria-hidden="true" style={{ verticalAlign: '-3px' }} /> Two-factor sign-in
      </h2>
      {error && <div className="banner error" role="alert">{error}</div>}

      {codes && (
        <div className="banner success">
          <strong>Two-factor sign-in is on.</strong> Save these recovery codes somewhere safe — each one signs you in once if you
          lose your phone. They won't be shown again.
          <ul className="recovery-codes">
            {codes.map((c) => (
              <li key={c} className="mono">{c}</li>
            ))}
          </ul>
          <div className="head-actions" style={{ marginTop: 8 }}>
            <button type="button" className="secondary" onClick={download}>Download codes</button>
            <button type="button" onClick={() => setCodes(null)}>I've saved them</button>
          </div>
        </div>
      )}

      {!codes && !enabled && !setup && (
        <>
          <p className="muted small" style={{ marginTop: -6 }}>
            Protect your account with a code from an authenticator app each time you sign in.
          </p>
          <button disabled={busy || !status.data} onClick={begin}>Set up two-factor sign-in</button>
        </>
      )}

      {setup && (
        <div className="mfa-setup">
          <ol className="automation-steps">
            <li>Open your authenticator app and add an account. Choose <strong>“Enter a setup key”</strong> (or tap the link below on your phone).</li>
            <li>
              Account: your email · Key:{' '}
              <code className="mfa-secret" aria-label="Setup key">{setup.secret.match(/.{1,4}/g)?.join(' ')}</code> · Type: time-based
            </li>
            <li>Enter the 6-digit code it shows.</li>
          </ol>
          <p className="small" style={{ marginTop: -4 }}>
            <a href={setup.otpauth_uri}>Open in authenticator app</a>
          </p>
          <div className="share-form">
            <Field id="mfa-code" label="6-digit code">
              <input id="mfa-code" inputMode="numeric" autoComplete="one-time-code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="123456" />
            </Field>
            <button disabled={busy || code.replace(/\D/g, '').length !== 6} onClick={enable}>Turn on</button>
            <button type="button" className="link-btn" onClick={() => setSetup(null)}>Cancel</button>
          </div>
        </div>
      )}

      {enabled && !codes && (
        <>
          <p className="small" style={{ marginTop: -6 }}>
            <span className="status-pill succeeded">On</span>{' '}
            <span className="muted">
              {status.data?.recovery_codes_left} recovery code{status.data?.recovery_codes_left === 1 ? '' : 's'} left.
            </span>
          </p>
          {!disableForm.open ? (
            <button className="secondary" onClick={() => setDisableForm({ ...disableForm, open: true })}>Turn off</button>
          ) : (
            <div className="share-form">
              <Field id="mfa-off-password" label="Password">
                <input id="mfa-off-password" type="password" autoComplete="current-password" value={disableForm.password} onChange={(e) => setDisableForm({ ...disableForm, password: e.target.value })} />
              </Field>
              <Field id="mfa-off-code" label="Code or recovery code">
                <input id="mfa-off-code" autoComplete="one-time-code" value={disableForm.code} onChange={(e) => setDisableForm({ ...disableForm, code: e.target.value })} />
              </Field>
              <button className="danger" disabled={busy || !disableForm.password || !disableForm.code} onClick={disable}>Turn off two-factor</button>
              <button type="button" className="link-btn" onClick={() => setDisableForm({ open: false, password: '', code: '' })}>Cancel</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
