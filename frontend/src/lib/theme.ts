/** Light/dark theme and accent colour.
 *
 * Theme: each person picks Light, Dark or System (default), saved in their browser.
 * Accent: each person picks a preset, or "workspace" (default) to follow the workspace
 * accent an admin set, which can be a preset or the Brand Kit colour. Brand colours are
 * adjusted until they meet WCAG AA against the theme background, so a client's brand can
 * never make text unreadable. Preset values are checked by theme.test.tsx.
 *
 * index.html applies the saved theme and accent before React loads (no flash), using the
 * same storage keys as below.
 */

export type ThemePref = 'system' | 'light' | 'dark'
export type Theme = 'light' | 'dark'
export type AccentId = 'arc' | 'indigo' | 'emerald' | 'amber' | 'rose' | 'violet'
export type AccentPref = 'workspace' | AccentId
export type WorkspaceAccent = AccentId | 'brand'
export type Tone = { accent: string; accent2: string; hover: string; onAccent: string }

export const THEME_KEY = 'arc-theme'
export const ACCENT_KEY = 'arc-accent'
export const ACCENT_CACHE_KEY = 'arc-accent-vars'

/** Background and card colours per theme (mirror index.css), used for contrast checks. */
export const SURFACES: Record<Theme, { bg: string; surface: string; surface2: string }> = {
  dark: { bg: '#08090b', surface: '#111317', surface2: '#16181d' },
  light: { bg: '#f8fafc', surface: '#ffffff', surface2: '#f1f5f9' },
}

export const ACCENTS: Record<AccentId, { label: string; dark: Tone; light: Tone }> = {
  arc: {
    label: 'ARC Blue',
    dark: { accent: '#9fd8ff', accent2: '#c7b8ff', hover: '#c3e7ff', onAccent: '#08090b' },
    light: { accent: '#0369a1', accent2: '#6d28d9', hover: '#075985', onAccent: '#ffffff' },
  },
  indigo: {
    label: 'Indigo',
    dark: { accent: '#a5b4fc', accent2: '#c4b5fd', hover: '#c7d2fe', onAccent: '#08090b' },
    light: { accent: '#4338ca', accent2: '#7c3aed', hover: '#3730a3', onAccent: '#ffffff' },
  },
  emerald: {
    label: 'Emerald',
    dark: { accent: '#6ee7b7', accent2: '#9fd8ff', hover: '#a7f3d0', onAccent: '#08090b' },
    light: { accent: '#047857', accent2: '#0369a1', hover: '#065f46', onAccent: '#ffffff' },
  },
  amber: {
    label: 'Amber',
    dark: { accent: '#fcd34d', accent2: '#fdba74', hover: '#fde68a', onAccent: '#08090b' },
    light: { accent: '#a34a06', accent2: '#c2410c', hover: '#92400e', onAccent: '#ffffff' },
  },
  rose: {
    label: 'Rose',
    dark: { accent: '#fda4af', accent2: '#f0abfc', hover: '#fecdd3', onAccent: '#08090b' },
    light: { accent: '#be123c', accent2: '#a21caf', hover: '#9f1239', onAccent: '#ffffff' },
  },
  violet: {
    label: 'Violet',
    dark: { accent: '#c4b5fd', accent2: '#f0abfc', hover: '#ddd6fe', onAccent: '#08090b' },
    light: { accent: '#6d28d9', accent2: '#be185d', hover: '#5b21b6', onAccent: '#ffffff' },
  },
}
export const ACCENT_IDS = Object.keys(ACCENTS) as AccentId[]

/* ---------- colour maths (WCAG 2.x) ---------- */

const HEX = /^#?([0-9a-f]{6})$/i

export function isHex(value: unknown): value is string {
  return typeof value === 'string' && HEX.test(value.trim())
}

function rgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '')
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)) as [number, number, number]
}

function toHex([r, g, b]: number[]): string {
  return '#' + [r, g, b].map((v) => Math.round(Math.min(255, Math.max(0, v))).toString(16).padStart(2, '0')).join('')
}

export function luminance(hex: string): number {
  const [r, g, b] = rgb(hex).map((v) => {
    const c = v / 255
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  })
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (hi + 0.05) / (lo + 0.05)
}

/** Mix towards white (t>0) or black (t<0). */
function shade(hex: string, t: number): string {
  const target = t > 0 ? 255 : 0
  return toHex(rgb(hex).map((v) => v + (target - v) * Math.abs(t)))
}

/** Lighten (dark theme) or darken (light theme) `hex` until it reaches `min` contrast on every background given. */
function readable(hex: string, theme: Theme, against: string[], min = 4.5): string {
  const dir = theme === 'dark' ? 1 : -1
  for (let step = 0; step <= 20; step++) {
    const c = shade(hex, (dir * step) / 20)
    if (against.every((bg) => contrast(c, bg) >= min)) return c
  }
  return theme === 'dark' ? '#ffffff' : '#000000'
}

/** A full accent tone from a Brand Kit colour, adjusted so it stays readable in `theme`. */
export function brandTone(hex: string, theme: Theme, secondary?: string | null): Tone {
  const s = SURFACES[theme]
  const bgs = [s.bg, s.surface, s.surface2]
  const accent = readable(hex, theme, bgs)
  const accent2 = secondary && isHex(secondary) ? readable(secondary, theme, bgs) : accent
  const hover = readable(shade(accent, theme === 'dark' ? 0.25 : -0.2), theme, bgs)
  const onAccent = contrast(accent, '#ffffff') >= contrast(accent, '#08090b') ? '#ffffff' : '#08090b'
  return { accent, accent2, hover, onAccent }
}

/* ---------- preferences ---------- */

function read(key: string): string | null {
  try {
    return localStorage.getItem(key)
  } catch {
    return null
  }
}

function write(key: string, value: string | null) {
  try {
    if (value == null) localStorage.removeItem(key)
    else localStorage.setItem(key, value)
  } catch {
    /* storage blocked (private mode): the choice lasts for this page only */
  }
}

export function loadThemePref(): ThemePref {
  const v = read(THEME_KEY)
  return v === 'light' || v === 'dark' ? v : 'system'
}

export function saveThemePref(pref: ThemePref) {
  write(THEME_KEY, pref === 'system' ? null : pref)
}

export function loadAccentPref(): AccentPref {
  const v = read(ACCENT_KEY)
  return v && v in ACCENTS ? (v as AccentId) : 'workspace'
}

export function saveAccentPref(pref: AccentPref) {
  write(ACCENT_KEY, pref === 'workspace' ? null : pref)
}

export function systemTheme(): Theme {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
}

export function resolveTheme(pref: ThemePref): Theme {
  return pref === 'system' ? systemTheme() : pref
}

/** Which tone to use: the person's own preset wins; otherwise the workspace's choice; otherwise ARC Blue. */
export function resolveTone(
  theme: Theme,
  pref: AccentPref,
  workspace: { accent: WorkspaceAccent | null; brandHex: string | null } | null,
): Tone {
  if (pref !== 'workspace') return ACCENTS[pref][theme]
  if (workspace?.accent === 'brand' && workspace.brandHex && isHex(workspace.brandHex)) return brandTone(workspace.brandHex, theme)
  if (workspace?.accent && workspace.accent !== 'brand') return ACCENTS[workspace.accent][theme]
  return ACCENTS.arc[theme]
}

export function toneVars(t: Tone): Record<string, string> {
  return { '--color-accent': t.accent, '--color-accent-2': t.accent2, '--color-accent-hover': t.hover, '--color-on-accent': t.onAccent }
}

/** Apply theme + accent to <html>, and cache the accent so index.html can apply it before the next paint. */
export function applyAppearance(theme: Theme, tones: Record<Theme, Tone>) {
  const root = document.documentElement
  root.dataset.theme = theme
  for (const [k, v] of Object.entries(toneVars(tones[theme]))) root.style.setProperty(k, v)
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', SURFACES[theme].bg)
  write(ACCENT_CACHE_KEY, JSON.stringify({ dark: toneVars(tones.dark), light: toneVars(tones.light) }))
}
