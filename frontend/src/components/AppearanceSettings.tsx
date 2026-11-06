import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiRequest } from '../api/client'
import { useTheme } from '../context/ThemeContext'
import { ACCENT_IDS, ACCENTS, brandTone, isHex, type AccentPref, type ThemePref, type WorkspaceAccent } from '../lib/theme'

type Props = {
  workspaceId: string
  accentColor: WorkspaceAccent | null
  brandAccent: string | null
  canEdit: boolean
  onSaved: () => void
  onError: (message: string) => void
}

const THEMES: { value: ThemePref; label: string; hint: string }[] = [
  { value: 'system', label: 'Match my device', hint: 'Light or dark, following your computer or phone' },
  { value: 'light', label: 'Light', hint: 'White, high contrast' },
  { value: 'dark', label: 'Dark', hint: "ARC's original look" },
]

/** Theme and accent colour. Theme and personal accent are saved in this browser;
 * the workspace accent is a workspace setting only owners and admins can change. */
export default function AppearanceSettings({ workspaceId, accentColor, brandAccent, canEdit, onSaved, onError }: Props) {
  const { themePref, setThemePref, theme, accentPref, setAccentPref, setWorkspaceAppearance } = useTheme()
  const [wsChoice, setWsChoice] = useState<WorkspaceAccent>(accentColor || 'arc')
  const [busy, setBusy] = useState(false)
  useEffect(() => setWsChoice(accentColor || 'arc'), [accentColor])

  const hasBrand = isHex(brandAccent)
  const swatch = (id: WorkspaceAccent) =>
    id === 'brand' ? (hasBrand ? brandTone(brandAccent!, theme).accent : 'transparent') : ACCENTS[id][theme].accent
  const wsLabel = accentColor === 'brand' ? 'Brand colour' : ACCENTS[(accentColor || 'arc') as keyof typeof ACCENTS]?.label

  async function saveWorkspace() {
    setBusy(true)
    try {
      const accent = wsChoice === 'arc' ? null : wsChoice
      await apiRequest(`/organizations/${workspaceId}`, { method: 'PATCH', body: { accent_color: accent } })
      setWorkspaceAppearance({ accent, brandHex: brandAccent }) // show it now; the shell's next poll agrees
      onSaved()
    } catch (e) {
      onError(e instanceof Error ? e.message : 'Could not save the workspace colour')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card appearance">
      <h2 style={{ marginTop: 0 }}>Appearance</h2>

      <fieldset className="appearance-group">
        <legend>Theme</legend>
        <p className="muted small">Just for you, on this browser.</p>
        <div className="choice-row">
          {THEMES.map((t) => (
            <label key={t.value} htmlFor={`theme-${t.value}`} className={`choice${themePref === t.value ? ' selected' : ''}`}>
              <input id={`theme-${t.value}`} type="radio" name="theme" checked={themePref === t.value} onChange={() => setThemePref(t.value)} />
              <span className={`theme-preview ${t.value}`} aria-hidden="true" />
              <span>
                <strong>{t.label}</strong>
                <span className="muted small">{t.hint}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="appearance-group">
        <legend>Your accent colour</legend>
        <p className="muted small">Used for links, highlights and charts. Just for you, on this browser.</p>
        <div className="swatch-row">
          {(['workspace', ...ACCENT_IDS] as AccentPref[]).map((id) => (
            <label key={id} htmlFor={`accent-${id}`} className={`swatch-choice${accentPref === id ? ' selected' : ''}`}>
              <input id={`accent-${id}`} type="radio" name="accent" checked={accentPref === id} onChange={() => setAccentPref(id)} />
              {id === 'workspace' ? (
                <span className="swatch-dot workspace" aria-hidden="true" />
              ) : (
                <span className="swatch-dot" style={{ background: ACCENTS[id][theme].accent }} aria-hidden="true" />
              )}
              <span className="small">{id === 'workspace' ? `Workspace (${wsLabel})` : ACCENTS[id].label}</span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className="appearance-group" disabled={!canEdit}>
        <legend>Workspace accent colour</legend>
        <p className="muted small">
          The default for everyone in this workspace who hasn't picked their own.
          {!canEdit && ' Only owners and admins can change it.'}
        </p>
        <div className="swatch-row">
          {([...ACCENT_IDS, 'brand'] as WorkspaceAccent[]).map((id) => {
            const unavailable = id === 'brand' && !hasBrand
            return (
              <label key={id} htmlFor={`ws-accent-${id}`} className={`swatch-choice${wsChoice === id ? ' selected' : ''}${unavailable ? ' unavailable' : ''}`}>
                <input id={`ws-accent-${id}`} type="radio" name="ws-accent" disabled={unavailable} checked={wsChoice === id} onChange={() => setWsChoice(id)} />
                <span className={`swatch-dot${unavailable ? ' empty' : ''}`} style={{ background: swatch(id) }} aria-hidden="true" />
                <span className="small">{id === 'brand' ? 'Brand colour' : ACCENTS[id].label}</span>
              </label>
            )
          })}
        </div>
        {hasBrand ? (
          <p className="muted small">
            Brand colour uses {brandAccent} from your <Link to="/app/brand">Brand Kit</Link>, adjusted where needed so text stays readable in light and dark.
          </p>
        ) : (
          <p className="muted small">
            Add a brand colour in your <Link to="/app/brand">Brand Kit</Link> to use it here.
          </p>
        )}
        {canEdit && (
          <button type="button" disabled={busy || wsChoice === (accentColor || 'arc')} onClick={saveWorkspace}>
            {busy ? 'Saving…' : 'Save workspace colour'}
          </button>
        )}
      </fieldset>
    </div>
  )
}
