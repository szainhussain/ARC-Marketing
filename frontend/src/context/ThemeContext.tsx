import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  applyAppearance,
  loadAccentPref,
  loadThemePref,
  resolveTheme,
  resolveTone,
  saveAccentPref,
  saveThemePref,
  type AccentPref,
  type Theme,
  type ThemePref,
  type WorkspaceAccent,
} from '../lib/theme'

type WorkspaceAppearance = { accent: WorkspaceAccent | null; brandHex: string | null } | null

type ThemeState = {
  themePref: ThemePref
  theme: Theme
  setThemePref: (p: ThemePref) => void
  accentPref: AccentPref
  setAccentPref: (p: AccentPref) => void
  /** Set by the app shell while a workspace is open; null on public pages. */
  setWorkspaceAppearance: (w: WorkspaceAppearance) => void
}

const ThemeContext = createContext<ThemeState | null>(null)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [themePref, setThemePrefState] = useState<ThemePref>(loadThemePref)
  const [accentPref, setAccentPrefState] = useState<AccentPref>(loadAccentPref)
  const [workspace, setWorkspaceAppearance] = useState<WorkspaceAppearance>(null)
  const [system, setSystem] = useState<Theme>(() => resolveTheme('system'))

  // Follow the device live while on "System".
  useEffect(() => {
    const mq = window.matchMedia?.('(prefers-color-scheme: light)')
    if (!mq) return
    const onChange = () => setSystem(mq.matches ? 'light' : 'dark')
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const theme: Theme = themePref === 'system' ? system : themePref
  const brandHex = workspace?.brandHex ?? null
  const wsAccent = workspace?.accent ?? null

  useEffect(() => {
    const ws = wsAccent || brandHex ? { accent: wsAccent, brandHex } : null
    applyAppearance(theme, { dark: resolveTone('dark', accentPref, ws), light: resolveTone('light', accentPref, ws) })
  }, [theme, accentPref, wsAccent, brandHex])

  const value = useMemo<ThemeState>(
    () => ({
      themePref,
      theme,
      setThemePref: (p) => {
        saveThemePref(p)
        setThemePrefState(p)
      },
      accentPref,
      setAccentPref: (p) => {
        saveAccentPref(p)
        setAccentPrefState(p)
      },
      setWorkspaceAppearance,
    }),
    [themePref, theme, accentPref],
  )
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}
